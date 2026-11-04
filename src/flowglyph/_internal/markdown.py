import json
import re
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from flowglyph._internal.text import first_line
from flowglyph.ir import Capability, Parameter, Tri, Workflow

if TYPE_CHECKING:
    from flowglyph.catalog import Catalog

_UNSAFE_FILENAME = re.compile(r"[^\w.-]+")
_EFFECTS_LEGEND = (
    "Effects codes: R reads, W mutates state, D destructive, X external. "
    "Upper case means yes, lower case means unknown."
)


def card_filename(capability: Capability) -> str:
    """File name of the Markdown card of `capability`."""
    return _UNSAFE_FILENAME.sub("_", capability.id).strip("_") + ".md"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _effects_line(capability: Capability) -> str:
    effects = capability.effects
    parts = [
        f"{name}: {value.value}"
        for name, value in (
            ("reads", effects.reads),
            ("mutates state", effects.mutates_state),
            ("destructive", effects.destructive),
            ("external", effects.external),
        )
    ]
    return ", ".join(parts)


def _retry_advice(capability: Capability) -> str:
    idempotency = capability.idempotency
    if idempotency.mode == "natural":
        return "safe to retry"
    if idempotency.mode == "key":
        fields = ", ".join(idempotency.key_fields) or "a caller-supplied key"
        return f"safe to retry when deduplicated on {fields}"
    if idempotency.mode == "conditional":
        return "safe to retry only under documented conditions"
    return "not idempotent: run through the gateway with an idempotency key"


def _idempotency_line(capability: Capability) -> str:
    idempotency = capability.idempotency
    return (
        f"{idempotency.mode}, {_retry_advice(capability)} "
        f"({idempotency.provenance}, confidence {idempotency.confidence:.1f})"
    )


def _parameter_table(parameters: list[Parameter], *, inputs: bool) -> list[str]:
    if not parameters:
        return ["None."]
    header = (
        "| Name | Type | Required | Description |" if inputs else "| Name | Type | Description |"
    )
    rows = [header, "|---|---|---|---|" if inputs else "|---|---|---|"]
    for parameter in parameters:
        description = _cell(parameter.description or "")
        if inputs:
            required = "yes" if parameter.required else "no"
            rows.append(f"| `{parameter.name}` | {parameter.type} | {required} | {description} |")
        else:
            rows.append(f"| `{parameter.name}` | {parameter.type} | {description} |")
    return rows


def _graph_section(workflow: Workflow, capabilities: Mapping[str, Capability]) -> list[str]:
    lines = ["## Steps", ""]
    for position, node in enumerate(workflow.nodes, start=1):
        target = capabilities.get(node.capability) if node.capability else None
        reference = f" -> [{target.title}]({card_filename(target)})" if target else ""
        join = ", runs if any predecessor ran" if node.join == "any" else ""
        lines.append(f"{position}. **{_cell(node.label)}** ({node.kind}{join}){reference}")
        if node.note:
            lines.append(f"   {_cell(first_line(node.note, 240))}")
    conditional = [edge for edge in workflow.edges if edge.condition]
    if conditional:
        lines += ["", "Branches:", ""]
        lines += [f"- `{e.source}` -> `{e.target}` when `{e.condition}`" for e in conditional]
    if workflow.unresolved_calls:
        lines += ["", "Unresolved invocations:", ""]
        lines += [f"- `{call}`" for call in workflow.unresolved_calls]
    return [*lines, ""]


def render_capability(
    capability: Capability,
    workflows: Mapping[str, Workflow],
    capabilities: Mapping[str, Capability],
) -> str:
    """The L1 card of a capability: what an agent reads before filling its arguments."""
    front_matter = {
        "id": capability.id,
        "kind": capability.kind,
        "category": capability.category,
        "version": capability.version,
        "effects": capability.effects.code() or "none",
        "idempotency": capability.idempotency.mode,
        "invocable": capability.invocable,
    }
    lines = ["---", *(f"{key}: {json.dumps(value)}" for key, value in front_matter.items()), "---"]
    lines += ["", f"# {capability.title}", ""]
    if capability.description:
        lines += [capability.description, ""]
    lines += [
        f"- **Source:** `{capability.source.location}` ({capability.source.provider})",
        f"- **Effects:** {_effects_line(capability)}",
        f"- **Idempotency:** {_idempotency_line(capability)}",
    ]
    if capability.security.approval_required:
        lines.append("- **Approval:** required before every run")
    lines.append("")
    if capability.notes:
        lines += ["> **Notes**", *(f"> - {note}" for note in capability.notes), ""]
    lines += ["## Inputs", "", *_parameter_table(capability.inputs, inputs=True), ""]
    if capability.kind != "activity":
        lines += ["## Outputs", "", *_parameter_table(capability.outputs, inputs=False), ""]
    workflow = workflows.get(capability.id)
    if workflow is not None:
        lines += _graph_section(workflow, capabilities)
    used_in = [
        tag.removeprefix("used-in:") for tag in capability.tags if tag.startswith("used-in:")
    ]
    if used_in:
        lines += ["## Used in", "", *(f"- `{location}`" for location in used_in), ""]
    lines += [
        "## Contract",
        "",
        "```json",
        json.dumps(
            {"input": capability.input_schema, "output": capability.output_schema},
            indent=2,
            ensure_ascii=False,
        ),
        "```",
        "",
    ]
    return "\n".join(lines)


def render_index(catalog: "Catalog") -> str:
    """The catalog's front page: every workflow and activity at a glance."""
    workflows = sorted(
        (c for c in catalog if c.kind != "activity"), key=lambda capability: capability.id
    )
    activities = sorted((c for c in catalog if c.kind == "activity"), key=lambda c: c.title)
    lines = [
        "# Catalog",
        "",
        f"{len(workflows)} invocable capabilities, {len(activities)} activity types.",
        "",
        "## Invocable",
        "",
        "| Capability | Description | Inputs | Effects | Idempotency | Version |",
        "|---|---|---|---|---|---|",
    ]
    for capability in workflows:
        inputs = ", ".join(f"`{parameter.name}`" for parameter in capability.inputs) or "none"
        lines.append(
            f"| [{capability.title}](capabilities/{card_filename(capability)}) "
            f"| {_cell(first_line(capability.description, 100))} | {inputs} "
            f"| {capability.effects.code() or 'none'} | {capability.idempotency.mode} "
            f"| {capability.version} |"
        )
    by_category: defaultdict[str, list[Capability]] = defaultdict(list)
    for capability in activities:
        by_category[capability.category].append(capability)
    if by_category:
        lines += ["", "## Activity types", ""]
    for category in sorted(by_category):
        lines += [f"### {category}", ""]
        for capability in by_category[category]:
            flag = " (side effects)" if capability.effects.has_side_effects else ""
            mutates = capability.effects.mutates_state
            certainty = " (unknown)" if mutates is Tri.UNKNOWN else ""
            lines.append(
                f"- [{capability.title}](capabilities/{card_filename(capability)}){flag}{certainty}"
            )
        lines.append("")
    lines += [
        _EFFECTS_LEGEND,
        "",
    ]
    return "\n".join(lines)
