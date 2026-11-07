"""The Automation IR: vendor-neutral models for capabilities and workflows.

A `Capability` describes one operation an automation can perform: its contract, its side
effects and whether it is safe to retry. A `Workflow` is a graph of nodes that reference
capabilities. Adapters produce these models; everything else in FlowGlyph consumes them.
"""

import json
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

IR_VERSION = "0.4.0"

type JsonSchema = dict[str, Any]
type CapabilityKind = Literal["workflow", "activity", "operation"]
type IdempotencyMode = Literal["none", "natural", "key", "conditional"]
type Provenance = Literal["declared", "inferred"]
type NodeKind = Literal["invoke", "activity", "decision", "container", "opaque"]
type Join = Literal["all", "any"]
type TriggerKind = Literal["call", "schedule", "event"]

OTHERWISE = "otherwise"
"""The condition of an edge taken when no other condition of its source holds."""


class Tri(StrEnum):
    """A three-valued answer for properties static analysis cannot always settle."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"

    @property
    def possible(self) -> bool:
        """Whether the property may hold, treating `UNKNOWN` as a yes."""
        return self is not Tri.NO

    @classmethod
    def combine(cls, values: "list[Tri]") -> "Tri":
        """Aggregate the values of several steps into the value for the whole."""
        if Tri.YES in values:
            return Tri.YES
        if Tri.UNKNOWN in values:
            return Tri.UNKNOWN
        return Tri.NO


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)


class Effects(_Model):
    """What running a capability does to the world outside the caller."""

    reads: Tri = Tri.UNKNOWN
    mutates_state: Tri = Tri.UNKNOWN
    destructive: Tri = Tri.UNKNOWN
    external: Tri = Tri.UNKNOWN

    @property
    def has_side_effects(self) -> bool:
        """Whether the capability may change state, counting unknowns as changes."""
        return self.mutates_state.possible or self.destructive.possible

    @classmethod
    def combine(cls, effects: "list[Effects]") -> "Effects":
        """Effects of running every given capability."""
        if not effects:
            return cls(reads=Tri.NO, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.NO)
        return cls(
            reads=Tri.combine([effect.reads for effect in effects]),
            mutates_state=Tri.combine([effect.mutates_state for effect in effects]),
            destructive=Tri.combine([effect.destructive for effect in effects]),
            external=Tri.combine([effect.external for effect in effects]),
        )


class Idempotency(_Model):
    """Whether, and how, a capability can be called more than once safely.

    `natural` means repeating the call has no further effect. `key` means it is safe only
    when deduplicated on `key_fields`. `none` means every call has an effect, so a gateway
    must deduplicate on a caller-supplied key before retrying.
    """

    mode: IdempotencyMode = "none"
    key_fields: tuple[str, ...] = ()
    scope: str | None = None
    ttl_seconds: int | None = Field(default=None, ge=1)
    compensation: str | None = None
    provenance: Provenance = "inferred"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    inferred_by: Literal["heuristic", "llm"] | None = "heuristic"


class Semantics(_Model):
    """Business meaning of a capability, independent of how it is implemented."""

    verb: str | None = None
    entity: str | None = None
    domain: str | None = None


class Security(_Model):
    """Authorization a caller needs before the capability may run."""

    scopes: tuple[str, ...] = ()
    approval_required: bool = False


class Source(_Model):
    """Where a capability came from, so it can be traced back and re-extracted."""

    provider: str
    artifact: str
    location: str
    source_hash: str
    artifact_version: str | None = None


class Trigger(_Model):
    """How a capability is started: called on demand, on a schedule, or by an event.

    `channel` is the protocol or adapter a call arrives through, such as `HTTPS`, `OData` or
    `ProcessDirect`, and `address` the path or address it listens on.
    """

    kind: TriggerKind = "call"
    channel: str | None = None
    address: str | None = None


class Parameter(_Model):
    """One named input or output, a convenience view over the JSON Schema."""

    name: str
    type: str
    required: bool
    description: str | None = None
    nullable: bool = False


class Capability(_Model):
    """One operation an agent can discover, reason about and, if invocable, run."""

    id: str
    version: str = "1.0.0"
    kind: CapabilityKind
    title: str
    description: str = ""
    category: str = "uncategorized"
    semantics: Semantics = Semantics()
    input_schema: JsonSchema = Field(default_factory=lambda: {"type": "object", "properties": {}})
    output_schema: JsonSchema = Field(default_factory=lambda: {"type": "object", "properties": {}})
    effects: Effects = Effects()
    idempotency: Idempotency = Idempotency()
    security: Security = Security()
    errors: tuple[str, ...] = ()
    trigger: Trigger | None = None
    entry_point: bool = False
    configuration: tuple[str, ...] = ()
    used_in: tuple[str, ...] = ()
    deprecated: bool = False
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    generated: tuple[Literal["description", "semantics"], ...] = ()
    """Fields a language model wrote, because the source did not say. Empty for extracted facts."""
    source: Source
    invocable: bool = True

    @property
    def inputs(self) -> list[Parameter]:
        """Input parameters in schema order."""
        return _parameters(self.input_schema)

    @property
    def outputs(self) -> list[Parameter]:
        """Output parameters in schema order."""
        return _parameters(self.output_schema)


class Node(_Model):
    """A step in a workflow graph.

    An incoming edge is *taken* when its source ran and its condition holds. With `join`
    set to `all` the node runs only when every incoming edge is taken; with `any` one is
    enough, which is what a step needs where an optional branch rejoins the main path. A
    node that does not run is skipped, and the edges leaving it are not taken.
    """

    id: str
    kind: NodeKind
    label: str
    capability: str | None = None
    note: str | None = None
    join: Join = "all"


class Edge(_Model):
    """Control flow between two nodes, optionally guarded by a condition."""

    source: str
    target: str
    condition: str | None = None


class Workflow(_Model):
    """The implementation graph behind a workflow capability."""

    id: str
    capability: str
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    calls: tuple[str, ...] = ()
    unresolved_calls: tuple[str, ...] = ()

    @property
    def entry(self) -> Node | None:
        """The first node, the one no edge points to."""
        targets = {edge.target for edge in self.edges}
        return next((node for node in self.nodes if node.id not in targets), None)

    def simulate(self, holds: Callable[[str], bool]) -> list[str]:
        """Ids of the nodes that run, in order, when `holds(condition)` decides each condition.

        Nodes without incoming edges always run. An `otherwise` edge is taken when no other
        condition leaving its source holds. Failures are not modelled: a failing step aborts
        the whole workflow.
        """
        incoming: dict[str, list[Edge]] = {node.id: [] for node in self.nodes}
        alternatives: dict[str, list[str]] = {}
        for edge in self.edges:
            incoming.setdefault(edge.target, []).append(edge)
            if edge.condition is not None and edge.condition != OTHERWISE:
                alternatives.setdefault(edge.source, []).append(edge.condition)
        ran: list[str] = []

        def taken(edge: Edge) -> bool:
            if edge.source not in ran:
                return False
            if edge.condition is None:
                return True
            if edge.condition == OTHERWISE:
                return not any(holds(other) for other in alternatives.get(edge.source, []))
            return holds(edge.condition)

        for node in self.nodes:
            edges = incoming.get(node.id, [])
            chosen = [edge for edge in edges if taken(edge)]
            runs = not edges or (len(chosen) == len(edges) if node.join == "all" else bool(chosen))
            if runs:
                ran.append(node.id)
        return ran


def _parameters(schema: JsonSchema) -> list[Parameter]:
    properties: dict[str, JsonSchema] = schema.get("properties", {})
    required = set(schema.get("required", []))
    parameters: list[Parameter] = []
    for name, spec in properties.items():
        declared: object = spec.get("type", "any")
        types = (
            [str(each) for each in cast("list[object]", declared)]
            if isinstance(declared, list)
            else [str(declared)]
        )
        concrete = [each for each in types if each != "null"] or ["null"]
        parameters.append(
            Parameter(
                name=name,
                type=concrete[0],
                required=name in required,
                description=spec.get("description"),
                nullable="null" in types,
            )
        )
    return parameters


def export_json_schemas(directory: str | Path) -> list[Path]:
    """Write the JSON Schemas of the IR documents into `directory`.

    Returns:
        The paths written, one per top-level IR document.
    """
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in (("capability", Capability), ("workflow", Workflow)):
        schema = model.model_json_schema()
        schema["$id"] = f"urn:flowglyph:ir:{IR_VERSION}:{name}"
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        path = target / f"{name}.schema.json"
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        written.append(path)
    return written
