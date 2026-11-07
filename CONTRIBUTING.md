# Contributing to FlowGlyph

Thanks for taking the time to contribute. This document covers how to set up the project,
the conventions the codebase follows, and how changes get merged.

## Development setup

You need [uv](https://docs.astral.sh/uv/) 0.13 or newer. Node 26 is only needed to
regenerate the README diagrams.

```bash
git clone https://github.com/afernandeztem/FlowGlyph
cd FlowGlyph
make install   # uv sync --all-extras + pre-commit hooks
make check     # ruff, pyright, pytest
```

Tests that call a real LLM are marked `llm` and skipped by default. `make test-llm` runs them
with the backend named in `FLOWGLYPH_PLANNER` (`anthropic` by default, which needs an
`ANTHROPIC_API_KEY`; `claude-code`, `codex`, `gemini` or `cursor` use that tool's own sign-in).
Every run uses real model capacity.

Before changing code, read [docs/guide.md](docs/guide.md) to see what FlowGlyph does from a
user's side, [docs/architecture.md](docs/architecture.md) for how the code is divided and
[docs/glossary.md](docs/glossary.md) for what its words mean.

## Project layout

| Path | What lives there |
|---|---|
| `src/flowglyph/ir.py` | The Automation IR models. Changing them is a spec change, see below. |
| `src/flowglyph/views.py` | How the IR is shown: effects codes, retry advice, L0 cards. |
| `src/flowglyph/sources.py` | Folders, files and git URLs resolved to local files. |
| `src/flowglyph/adapters/` | One subpackage per source format. Adapters only produce IR. |
| `src/flowglyph/catalog/` | Extraction, lock file and versioning, overrides, search, persistence. |
| `src/flowglyph/report.py` | The idempotency report. |
| `src/flowglyph/wiki.py` | The LLM wiki: build and lint. |
| `src/flowglyph/gateway/` | MCP server, policy engine, idempotency ledger, audit log, executors. |
| `src/flowglyph/planner/` | Requirements to workflow IR, and the backends that propose plans. |
| `src/flowglyph/compilers/` | Workflow IR back to BPMN and UiPath XAML. |
| `src/flowglyph/cli/` | The `flowglyph` command: one module per context in `commands/`. |
| `src/flowglyph/_internal/` | Private helpers. Not part of the public API. |
| `tests/unit/` | Fast tests per module. `test_architecture.py` enforces the dependency rules. |
| `tests/e2e/` | The command line and the MCP server, driven as a user or agent would. |
| `tests/golden/` | Expected outputs. Regenerate with `pytest --update-golden` and review the diff. |
| `tests/eval/` | Planner quality against a real model (`-m llm`). |
| `tests/fixtures/` | Sample sources. Third-party ones keep their license next to them and in `NOTICE`. |
| `docs/adr/` | Decision records: why things are the way they are. |

## Code style

The bar is code that reads as if one careful person wrote all of it.

- English everywhere: code, docstrings, error messages, commit messages.
- Google-style docstrings on public modules, classes and functions, only when they say
  something the signature does not. Private helpers usually need none.
- No inline comments that describe *what* a line does. A comment is allowed only to explain a
  non-obvious *why*: a workaround, a spec reference, a deliberate trade-off.
- No section banners. If a module needs sections, it needs to be split into modules.
- No commented-out code, no emoji, no `TODO` without a linked issue.
- Full names over abbreviations. `workflow`, not `wf`; `activity`, not `a`.
- Data that crosses a module boundary is a typed model, never an anonymous `dict`.
- Project exceptions derive from `FlowGlyphError`. Never catch bare `Exception`.
- Keep functions small and single-purpose; ruff enforces the limits.

`ruff check`, `ruff format --check` and `pyright` (strict) must pass. Pre-commit runs all
three.

## Changing the IR

The IR is the project's contract with every adapter, catalog and agent that consumes it.
Changes to `ir.py` need:

1. An ADR in `docs/adr/` explaining the change and its migration path.
2. An update to `docs/ir-spec.md` and the generated JSON Schemas (`make schemas`).
3. A bump of `IR_VERSION` following semver: removing or renaming a field is a major change.

## Writing an adapter

An adapter translates one source format into IR. It is a class with a `name`, a `version`, and
two methods; nothing to inherit. This one reads scheduled jobs from a `jobs.yaml` file:

<!-- adapter-example -->
```python
import hashlib
from pathlib import Path
from typing import ClassVar

import yaml

from flowglyph import Capability, Effects, Trigger
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.ir import Source


class JobsAdapter:
    """Scheduled jobs listed in a `jobs.yaml` file."""

    name: ClassVar[str] = "jobs"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is, or contains, a `jobs.yaml`."""
        return path.name == "jobs.yaml" or (path / "jobs.yaml").is_file()

    def extract(self, path: Path) -> Extraction:
        """One capability per job."""
        file = path if path.is_file() else path / "jobs.yaml"
        data = file.read_bytes()
        source_hash = "sha256:" + hashlib.sha256(data).hexdigest()
        capabilities: list[Capability] = []
        diagnostics: list[Diagnostic] = []
        for job in yaml.safe_load(data).get("jobs", []):
            if "schedule" not in job:
                message = f"{job['name']} has no schedule"
                diagnostics.append(Diagnostic("warning", file.name, message))
                continue
            capabilities.append(
                Capability(
                    id=f"jobs/{job['name']}",
                    kind="workflow",
                    title=job["name"],
                    description=job.get("description", ""),
                    trigger=Trigger(kind="schedule", channel="cron", address=job["schedule"]),
                    effects=Effects(),
                    source=Source(
                        provider=self.name,
                        artifact=job["name"],
                        location=file.name,
                        source_hash=source_hash,
                    ),
                    invocable=False,
                )
            )
        return Extraction(
            capabilities=capabilities,
            artifacts={file.name: source_hash},
            diagnostics=diagnostics,
        )
```

Register it from your own package, and `flowglyph extract --adapter jobs` finds it:

```toml
[project.entry-points."flowglyph.adapters"]
jobs = "flowglyph_jobs:JobsAdapter"
```

In tests or scripts, `flowglyph.register_adapter("jobs", JobsAdapter)` does the same.

When a tree can hold many sources (every UiPath project in a repository, say), also define
`discover(root) -> list[Path]`; each path it returns is extracted on its own. Without it, the
adapter receives `root` whole when `detect` accepts it.

The rules every adapter follows:

- **Deterministic and offline.** The same bytes always give the same `Extraction`: no network,
  no LLM, no clock, no randomness. Sort what you emit.
- **Sources are untrusted data.** Parse them; never execute, import or evaluate anything they
  contain. Refuse XML that declares a DTD (built-in adapters use `_internal.xml.parse_xml`).
  Read the names of externalized configuration, never its values.
- **Say unknown when you do not know.** `Effects()` is unknown everywhere, and that is a better
  answer than a guess. Use `yes` and `no` only for what the format guarantees.
- **Declare only what the source declares.** Idempotency is `declared` only when the source
  itself promises it; otherwise it is `inferred`, with an honest `confidence`.
- **Facts go in fields, not tags.** Use `trigger`, `entry_point`, `configuration`, `used_in` and
  `deprecated`; keep `tags` for the source's own free labels.
- **Ids are stable.** An id never moves to a different operation, and does not change when a
  file is reformatted. Prefix it with the adapter name.
- **Report, do not fail.** Problems with one artifact become a `Diagnostic`; raise
  `AdapterError` only when nothing can be read.
- **Test with real samples.** Add fixtures under `tests/fixtures/` (with their license if they
  are not yours), unit tests for each rule, and a golden test once the output is stable.

## Adding a planner backend

A planner backend proposes a plan; the resolver then checks it against the catalog, so a backend
never has to be trusted. There are two ways to add one.

**A coding assistant with a headless mode** needs only a `CommandSpec`: the command line to run,
where the JSON Schema goes (`{schema}` or `{schema_file}`), and where the plan comes back (stdout,
a key in a JSON envelope, or `{output_file}`). Built-in presets are in
`src/flowglyph/planner/command.py`; add yours there and to `BUILT_IN` in `planner/backends.py`,
or use `CommandPlanModel(CommandSpec(...))` directly.

**Any other SDK or model** needs a class with a `propose` method, and a factory registered under
the `flowglyph.planners` entry point group:

<!-- planner-example -->
```python
from collections.abc import Sequence
from typing import Any

import my_sdk

from flowglyph.planner import PlanModel
from flowglyph.planner.model import Plan, plan_json_schema
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text


class MySdkPlanModel:
    """Proposes plans through my_sdk."""

    def __init__(self, model: str) -> None:
        self.model = model

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Send the shared prompt and schema; parse the answer as a plan."""
        answer = my_sdk.complete(
            model=self.model,
            system=SYSTEM_PROMPT,
            prompt=request_text(requirements, candidates),
            json_schema=plan_json_schema(),
        )
        return Plan.model_validate_json(answer)


def my_sdk_planner(model: str | None, effort: str | None) -> PlanModel:
    """Factory FlowGlyph calls with `--model` and `--effort`."""
    return MySdkPlanModel(model or "my-default-model")
```

```toml
[project.entry-points."flowglyph.planners"]
my-sdk = "flowglyph_my_sdk:my_sdk_planner"
```

`flowglyph plan requirements.md catalog --via my-sdk` then uses it, and
`FLOWGLYPH_PLANNER=my-sdk pytest -m llm` runs the planner evaluation against it. Use the shared
`SYSTEM_PROMPT`, `request_text` and `plan_json_schema` so every backend is asked the same thing.
Send nothing but the requirements and the candidate cards.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`.
- Sign off every commit (`git commit -s`). This certifies the
  [Developer Certificate of Origin](https://developercertificate.org/): that you wrote the
  change or have the right to submit it under the project's license.
- Add an entry under `Unreleased` in `CHANGELOG.md` for user-facing changes.
- Keep pull requests focused. A refactor and a feature are two pull requests.

## Reporting bugs and proposing features

Use the issue templates. For security issues, follow [SECURITY.md](SECURITY.md) instead.

By participating you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
