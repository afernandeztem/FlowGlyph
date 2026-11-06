# ADR-0005: Typed capability facts, and presentation outside the IR

- Status: accepted
- Date: 2026-11-06

## Context

Adapters had started to encode facts as prefixed strings in `tags`: `entry-point`,
`used-in:<file>`, `trigger:<adapter>`, `parameter:<name>`, `odata-v2`, `deprecated`. Consumers
parsed them back with `startswith`. Nothing checked them, every adapter invented its own prefixes,
and the JSON Schema of a capability said nothing about them.

The IR models also carried presentation: `Effects.code()` (the `RwX` letters),
`Idempotency.advice()` (an English sentence) and `Capability.card()` (the L0 view for agents).
Those change whenever a screen or a prompt does; the IR must not.

## Decision

IR 0.3.0 gives those facts typed fields on `Capability`:

| Field | Replaces | Meaning |
|---|---|---|
| `trigger: Trigger` (`kind`, `channel`, `address`) | `trigger:*` tags | how the capability is started: called, scheduled or by an event, through which channel, at which address |
| `entry_point: bool` | `entry-point` | the main workflow of its project |
| `configuration: tuple[str, ...]` | `parameter:*` | names of externalized parameters it depends on; never their values |
| `used_in: tuple[str, ...]` | `used-in:*` | where a documentation-only capability, such as an activity type, appears |
| `deprecated: bool` | `deprecated` | the source marks it as deprecated |

`tags` remains for free labels that carry no meaning FlowGlyph relies on, such as the tags of an
OpenAPI operation.

Presentation moves to `flowglyph.views`: `effects_code`, `retry_advice` and `l0_card`. The IR keeps
only domain behaviour: `Tri.possible`, `Effects.has_side_effects`, the `combine` rules and
`Workflow.simulate`.

## Consequences

- The capability JSON Schema now documents every fact consumers use.
- Python callers replace `capability.effects.code()` with `views.effects_code(capability.effects)`,
  and likewise for advice and cards. FlowGlyph is pre-1.0, so this ships as a minor version with a
  changelog entry rather than a deprecation cycle.
- Catalog versions do not move: these fields are not part of a capability's contract.
