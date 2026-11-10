"""An LLM wiki of a catalog, in the shape Andrej Karpathy describes in "LLM Wiki".

The automation sources are the raw layer and are never modified. FlowGlyph writes the
structural part of every page (contracts, effects, call graph, backlinks) deterministically;
an LLM, or a person, adds knowledge in each page's Notes section, which survives every rebuild.
`AGENTS.md` is the schema that tells an LLM how to maintain the wiki, `index.md` lists every
page by category and `log.md` is an append-only record of ingests and lint passes.
"""

import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from flowglyph import report
from flowglyph._internal import markdown
from flowglyph._internal.text import first_line
from flowglyph.catalog import Catalog, Change, load_catalog
from flowglyph.ir import Capability
from flowglyph.views import effects_code

NOTES_MARKER = "<!-- flowglyph:notes -->"
DATA_DIRECTORY = "_data"
_NOTES_TEMPLATE = f"""{NOTES_MARKER}
## Notes

_Everything below this line is kept when the wiki is rebuilt. Add what the sources cannot say:
business meaning, owners, incidents, how this is used in practice._
"""
_REVIEW_MESSAGE = "has side effects and no retry guarantee: declare its idempotency"
_ORPHAN_MESSAGE = "nothing invokes it and it is not an entry point"
_LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
_UNSAFE = re.compile(r"[^\w.-]+")
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)

SCHEMA = """# Wiki schema

This wiki describes the automations in the sources it was built from. It follows the "LLM wiki"
pattern: the sources are read-only, the wiki is maintained by an LLM, and this file tells that
LLM how.

## Layers

- **Sources** (UiPath projects, OpenAPI documents, SAP OData metadata) are the source of truth.
  Never edit them from here.
- **Generated sections** of every page are rewritten by `flowglyph wiki build`. Never edit text
  above the `<!-- flowglyph:notes -->` line: it will be lost.
- **Notes** sections, below that line, belong to you. They survive every rebuild.
- `_data/` holds the machine-readable catalog. Read it, do not edit it.

## Pages

- `index.md`: every page by category, one line each. Read it first.
- `overview.md`: sources, counts, entry points and open gaps.
- `capabilities/`: one page per capability. Its contract, effects, idempotency, steps, the
  workflows that use it and related capabilities.
- `categories/` and `sources/`: one page per category and per project or service.
- `log.md`: append-only history. Entries start with `## [YYYY-MM-DD] <kind> | <subject>`.

## Workflows

**Ingest.** When the sources change, run `flowglyph wiki build <sources> -o <wiki>`. Then read
the new `log.md` entry and update the Notes of the pages it lists as changed.

**Query.** Read `index.md`, open the relevant pages, answer with links to them. If the answer
is worth keeping, add it to the Notes of the pages it is about.

**Lint.** Run `flowglyph wiki lint <wiki>` and work through the issues. Idempotency marked for
review is decided by people: propose the override, do not invent one. Overrides go in
`flowglyph.overrides.yaml` next to the sources, for example:

```yaml
capabilities:
  <capability id>:
    idempotency: {mode: key, key_fields: [<input that identifies the request>]}
```

## Conventions

- Link pages with relative Markdown links, such as `[Main](../capabilities/uipath_x_Main.md)`.
- Write facts the sources cannot show: what a step means for the business, who owns it, known
  failure modes. Do not restate the contract.
- When a source contradicts a note, the source wins: update the note and say why in `log.md`.
"""


@dataclass(frozen=True)
class LintIssue:
    """Something in the wiki or its catalog that needs attention."""

    level: Literal["error", "warning", "info"]
    page: str
    message: str


@dataclass(frozen=True)
class BuildResult:
    """What a wiki build wrote."""

    directory: Path
    pages: int
    removed: tuple[str, ...]
    log_entry: str


def page_name(capability_id: str) -> str:
    """File name of the page of a capability, category or source."""
    return _UNSAFE.sub("_", capability_id).strip("_") + ".md"


def build_wiki(
    catalog: Catalog, directory: str | Path, *, subject: str | None = None
) -> BuildResult:
    """Write or refresh the wiki of `catalog` in `directory`, keeping every page's notes."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    catalog.save(root / DATA_DIRECTORY)
    schema = root / "AGENTS.md"
    if not schema.exists():
        schema.write_text(SCHEMA, encoding="utf-8", newline="\n")
    callers = _callers(catalog)
    by_category = _group(catalog, lambda c: c.category)
    by_source = _group(catalog, _source_key)
    written: set[Path] = set()
    for capability in catalog:
        page = root / "capabilities" / page_name(capability.id)
        _write(page, _capability_page(capability, catalog, callers, by_category))
        written.add(page)
    for category, members in by_category.items():
        page = root / "categories" / page_name(category)
        _write(page, _group_page(f"Category: {category}", members))
        written.add(page)
    for source, members in by_source.items():
        page = root / "sources" / page_name(source)
        _write(page, _source_page(source, members, catalog))
        written.add(page)
    removed = _retire(root, written)
    (root / "index.md").write_text(
        _index(catalog, by_category, by_source), encoding="utf-8", newline="\n"
    )
    _write(root / "overview.md", _overview(catalog, by_source))
    entry = _log_entry(catalog, subject or catalog.lock.origin or "sources", removed)
    _append_log(root, entry)
    return BuildResult(root, len(written) + 2, tuple(sorted(removed)), entry)


def lint_wiki(directory: str | Path) -> list[LintIssue]:
    """Check a wiki and its catalog, and record the pass in `log.md`."""
    root = Path(directory)
    catalog = load_catalog(root / DATA_DIRECTORY)
    issues: list[LintIssue] = []
    called = {callee for workflow in catalog.workflows.values() for callee in workflow.calls}
    for capability in sorted(catalog, key=lambda c: c.id):
        page = f"capabilities/{page_name(capability.id)}"
        if report.status(capability) == "review":
            issues.append(LintIssue("warning", page, _REVIEW_MESSAGE))
        if capability.invocable and not capability.description:
            issues.append(LintIssue("info", page, "has no description in its source"))
        for note in capability.notes:
            level = "warning" if note.startswith("warning: ") else "info"
            issues.append(LintIssue(level, page, note.removeprefix(f"{level}: ")))
        is_root = capability.entry_point or capability.source.provider != "uipath"
        if capability.kind == "workflow" and capability.id not in called and not is_root:
            issues.append(LintIssue("info", page, _ORPHAN_MESSAGE))
    for workflow in catalog.workflows.values():
        page = f"capabilities/{page_name(workflow.capability)}"
        issues.extend(
            LintIssue("warning", page, f"invokes something that is not in the sources: {call}")
            for call in workflow.unresolved_calls
        )
    issues.extend(_broken_links(root))
    issues.extend(
        LintIssue("info", path.relative_to(root).as_posix(), "its capability left the sources")
        for path in sorted(root.glob("capabilities/*.md"))
        if "> **Removed from the sources.**" in path.read_text(encoding="utf-8")
    )
    _append_log(root, _lint_entry(issues))
    return issues


def _capability_page(
    capability: Capability,
    catalog: Catalog,
    callers: dict[str, list[str]],
    by_category: dict[str, list[Capability]],
) -> str:
    card = markdown.render_capability(capability, catalog.workflows, catalog.capabilities)
    category = capability.category
    source = _source_key(capability)
    lines = [
        card.rstrip(),
        "",
        f"- **Status:** {report.status(capability)}",
        f"- **Category:** [{category}](../categories/{page_name(category)})",
        f"- **Source:** [{source}](../sources/{page_name(source)})",
    ]
    users = callers.get(capability.id, [])
    if users:
        lines += ["", "## Used by", ""]
        lines += [f"- [{catalog.capabilities[u].title}]({page_name(u)})" for u in users]
    related = [c for c in by_category.get(capability.category, []) if c.id != capability.id][:10]
    if related:
        lines += ["", "## Related", ""]
        lines += [
            f"- [{c.title}]({page_name(c.id)}): {first_line(c.description, 90) or c.id}"
            for c in related
        ]
    return "\n".join(lines) + "\n"


def _group_page(title: str, members: list[Capability]) -> str:
    lines = [
        f"# {title}",
        "",
        f"{len(members)} capabilities.",
        "",
        "| Capability | Effects | Idempotency | Status |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| [{c.title}](../capabilities/{page_name(c.id)}) | {effects_code(c.effects) or 'none'} "
        f"| {c.idempotency.mode} | {report.status(c)} |"
        for c in members
    ]
    return "\n".join(lines) + "\n"


def _source_page(source: str, members: list[Capability], catalog: Catalog) -> str:
    page = _group_page(f"Source: {source}", members).rstrip("\n")
    entry_points = [c for c in members if c.entry_point]
    lines = [page]
    for entry in entry_points:
        lines += [
            "",
            f"## Call tree of {entry.title}",
            "",
            "```text",
            *_tree(entry, catalog),
            "```",
        ]
    return "\n".join(lines) + "\n"


def _tree(root: Capability, catalog: Catalog) -> list[str]:
    lines = [f"{root.title} [{effects_code(root.effects) or 'pure'}]"]

    def visit(capability_id: str, depth: int, seen: frozenset[str]) -> None:
        workflow = catalog.workflows.get(capability_id)
        if workflow is None:
            return
        for callee in workflow.calls:
            target = catalog.capabilities.get(callee)
            if target is None:
                continue
            lines.append(
                f"{'  ' * depth}- {target.title} [{effects_code(target.effects) or 'pure'}]"
            )
            if callee not in seen:
                visit(callee, depth + 1, seen | {callee})

    visit(root.id, 1, frozenset({root.id}))
    return lines


def _index(
    catalog: Catalog,
    by_category: dict[str, list[Capability]],
    by_source: dict[str, list[Capability]],
) -> str:
    lines = [
        "# Index",
        "",
        (
            f"{len(catalog)} capabilities from {len(by_source)} sources. Start with the "
            "[overview](overview.md); the [schema](AGENTS.md) explains how this wiki is kept."
        ),
        "",
        "## Sources",
        "",
        *(
            f"- [{source}](sources/{page_name(source)}): {len(members)} capabilities"
            for source, members in sorted(by_source.items())
        ),
    ]
    for category in sorted(by_category):
        lines += ["", f"## {category}", ""]
        for capability in by_category[category]:
            summary = first_line(capability.description, 100) or capability.kind
            lines.append(
                f"- [{capability.title}](capabilities/{page_name(capability.id)}): {summary} "
                f"({effects_code(capability.effects) or 'pure'}, {report.status(capability)})"
            )
    return "\n".join(lines) + "\n"


def _overview(catalog: Catalog, by_source: dict[str, list[Capability]]) -> str:
    rows = report.rows(catalog)
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.status] += 1
    lock = catalog.lock
    origin = f"{lock.origin} at `{lock.revision}`" if lock.origin else "local files"
    lines = [
        "# Overview",
        "",
        f"- **Read from:** {origin}",
        f"- **Adapters:** {', '.join(f'{n} {v}' for n, v in sorted(lock.adapters.items()))}",
        f"- **Capabilities:** {len(catalog)} in {len(by_source)} sources",
        (
            f"- **Idempotency:** {counts['safe']} safe, {counts['keyed']} keyed, "
            f"{counts['declared']} declared, {counts['review']} to review"
        ),
        "",
        "## To review",
        "",
    ]
    pending = [row for row in rows if row.status == "review"]
    lines += [
        f"- [{row.id}](capabilities/{page_name(row.id)}): {row.effects}" for row in pending
    ] or ["Nothing."]
    unresolved = [
        (workflow.capability, call)
        for workflow in catalog.workflows.values()
        for call in workflow.unresolved_calls
    ]
    if unresolved:
        lines += ["", "## Invocations that point outside the sources", ""]
        lines += [
            f"- [{c}](capabilities/{page_name(c)}) invokes `{call}`" for c, call in unresolved
        ]
    return "\n".join(lines) + "\n"


def _write(page: Path, generated: str) -> None:
    page.parent.mkdir(parents=True, exist_ok=True)
    notes = _NOTES_TEMPLATE
    if page.exists():
        current = page.read_text(encoding="utf-8")
        if NOTES_MARKER in current:
            notes = current[current.index(NOTES_MARKER) :]
    page.write_text(
        generated.rstrip("\n") + "\n\n" + notes.rstrip("\n") + "\n", encoding="utf-8", newline="\n"
    )


_RETIRED = "> **Removed from the sources.**"


def _retire(root: Path, written: set[Path]) -> list[str]:
    """Delete generated pages that left the sources, unless someone wrote notes on them."""
    removed: list[str] = []
    for folder in ("capabilities", "categories", "sources"):
        for page in (root / folder).glob("*.md"):
            if page in written:
                continue
            text = page.read_text(encoding="utf-8")
            # Every page a build writes carries the marker: a file without it is someone's own.
            if NOTES_MARKER not in text or _RETIRED in text:
                continue
            notes = text[text.index(NOTES_MARKER) :]
            relative = page.relative_to(root).as_posix()
            if notes.strip() != _NOTES_TEMPLATE.strip():
                title = text.split("\n", 1)[0] if text.startswith("# ") else f"# {page.stem}"
                banner = f"{title}\n\n{_RETIRED} Kept because it has notes.\n"
                page.write_text(banner + "\n" + notes, encoding="utf-8", newline="\n")
            else:
                page.unlink()
            removed.append(relative)
    return removed


def _log_entry(catalog: Catalog, subject: str, removed: list[str]) -> str:
    today = datetime.now(UTC).date().isoformat()
    review = sum(1 for row in report.rows(catalog) if row.status == "review")
    lines = [
        f"## [{today}] ingest | {subject}",
        "",
        f"- {len(catalog)} capabilities, {review} to review",
    ]
    lines += [_change_line(change) for change in catalog.changes]
    lines += [f"- retired `{page}`" for page in sorted(removed)]
    return "\n".join(lines) + "\n"


def _change_line(change: Change) -> str:
    link = f"[{change.capability}](capabilities/{page_name(change.capability)})"
    if change.kind == "changed":
        versions = f"{change.old_version} -> {change.new_version}"
        return f"- {change.bump.name.lower()} change: {link} {versions}"
    return f"- {change.kind}: {link}"


def _lint_entry(issues: Iterable[LintIssue]) -> str:
    today = datetime.now(UTC).date().isoformat()
    found = list(issues)
    warnings = sum(1 for issue in found if issue.level != "info")
    return f"## [{today}] lint | {len(found)} issues, {warnings} warnings\n"


def _append_log(root: Path, entry: str) -> None:
    log = root / "log.md"
    if not log.exists():
        log.write_text(
            "# Log\n\nAppend-only. Newest entries at the bottom.\n", encoding="utf-8", newline="\n"
        )
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n" + entry)


def _broken_links(root: Path) -> list[LintIssue]:
    issues: list[LintIssue] = []
    for page in sorted(root.rglob("*.md")):
        if DATA_DIRECTORY in page.relative_to(root).parts:
            continue
        prose = _CODE.sub("", page.read_text(encoding="utf-8"))
        for target in _LINK.findall(prose):
            if target.startswith(("http://", "https://")):
                continue
            if not (page.parent / target).exists():
                issues.append(
                    LintIssue(
                        "error", page.relative_to(root).as_posix(), f"broken link to {target}"
                    )
                )
    return issues


def _callers(catalog: Catalog) -> dict[str, list[str]]:
    callers: defaultdict[str, list[str]] = defaultdict(list)
    for workflow in sorted(catalog.workflows.values(), key=lambda w: w.id):
        for node in workflow.nodes:
            if node.capability and workflow.capability not in callers[node.capability]:
                callers[node.capability].append(workflow.capability)
    return callers


def _group(catalog: Catalog, key: Callable[[Capability], str]) -> dict[str, list[Capability]]:
    groups: defaultdict[str, list[Capability]] = defaultdict(list)
    for capability in sorted(catalog, key=lambda c: c.id):
        groups[key(capability)].append(capability)
    return dict(groups)


def _source_key(capability: Capability) -> str:
    """`provider/project`: the first two segments of a capability id."""
    return "/".join(capability.id.split("/")[:2])
