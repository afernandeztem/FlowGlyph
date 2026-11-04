# Automation IR specification

Version 0.1.0. Machine-readable schemas: [`schemas/capability.schema.json`](../schemas/capability.schema.json)
and [`schemas/workflow.schema.json`](../schemas/workflow.schema.json).

The IR describes *what an automation does* independently of *how it is implemented* and *how
an agent calls it*. It has two documents: **Capability** and **Workflow**.

## Capability

One operation. Example, extracted from the UiPath ReFrameWork:

```yaml
id: uipath/reframework/Framework/InitAllSettings
version: 1.0.0
kind: workflow
title: InitiAllSettings
description: Initialize, populate and output a configuration Dictionary ...
category: workflow
input_schema:
  type: object
  properties:
    in_ConfigFile: {type: string, x-clr-type: "InArgument(x:String)", x-default-expression: Data\Config.xlsx}
    in_ConfigSheets: {type: array, x-clr-type: "InArgument(s:String[])"}
  required: []
  additionalProperties: false
output_schema:
  type: object
  properties:
    out_Config: {type: object, x-clr-type: "OutArgument(scg:Dictionary(x:String, x:Object))"}
effects: {reads: yes, mutates_state: no, destructive: no, external: yes}
idempotency: {mode: natural, provenance: inferred, confidence: 0.8, inferred_by: heuristic}
security: {scopes: [], approval_required: false}
source:
  provider: uipath
  artifact: InitiAllSettings
  location: Framework/InitAllSettings.xaml
  source_hash: sha256:…
invocable: true
```

| Field | Meaning |
|---|---|
| `id` | Stable identifier, `<provider>/<project>/<path>` for workflows. Never reused for a different operation. |
| `version` | Semver computed by `extract` against the previous lock. See [Versioning](#versioning). |
| `kind` | `workflow` (a callable automation), `operation` (an API call) or `activity` (a building block, documented but not invocable on its own). |
| `input_schema`, `output_schema` | JSON Schema. `x-` keys keep source-specific detail such as the original .NET type. |
| `effects` | See [Effects](#effects). |
| `idempotency` | See [Idempotency](#idempotency). |
| `security` | Scopes the caller needs and whether a human must approve each run. |
| `notes` | Problems found while extracting, such as an `out_` argument declared as input. |
| `invocable` | Whether a gateway may run the capability directly. |

### Effects

Four properties, each `yes`, `no` or `unknown`:

| Property | Question |
|---|---|
| `reads` | Does it read data from somewhere? |
| `mutates_state` | Can it change state that outlives the call? |
| `destructive` | Can that change lose data or be impossible to undo? |
| `external` | Does it talk to a system outside the robot or process? |

`unknown` is a first-class answer. Static analysis cannot prove that a click or a script is
harmless, and the IR does not pretend it can: consumers must treat `unknown` as a possible
`yes`. A workflow's effects are the combination of its activities' effects and, transitively,
those of the workflows it invokes.

The compact form used in L0 cards writes `R`, `W`, `D`, `X` for yes and lower case for
unknown: `RwX` reads, may write, and is external.

### Idempotency

| Mode | Meaning |
|---|---|
| `natural` | Repeating the call has no further effect. Safe to retry. |
| `key` | Safe to retry when deduplicated on `key_fields`, within `scope`, for `ttl_seconds`. |
| `conditional` | Safe only under conditions documented in `description`. |
| `none` | Every call has an effect. A gateway must deduplicate on a caller-supplied key. |

`provenance` records where the answer comes from: `inferred` by a heuristic or an LLM (with
`confidence`), or `declared` by a person in `flowglyph.overrides.yaml`. Whether a run was
actually deduplicated is a runtime fact reported by the gateway, never stored in the IR.

`compensation` names the capability that undoes this one, when there is one.

## Workflow

The implementation graph of a workflow capability.

| Field | Meaning |
|---|---|
| `nodes` | Steps: `invoke` (calls another capability), `activity` (a step with effects), `decision` (a branch), `container` (a scope with effects of its own) and `opaque` (a state machine, flowchart or parallel block whose internal control flow is not modelled yet). |
| `edges` | Control flow. `condition` is set on edges leaving a decision. |
| `calls` | Capability ids this workflow invokes. |
| `unresolved_calls` | Invocations that could not be matched to a capability, including targets computed at runtime. |

Pure steps (assignments, logging, control flow without branching) are folded away: the graph
shows what an agent needs to reason about, not every activity. Opaque nodes are followed by
their children flattened in document order; their edges do not represent real control flow.

## Representations

| Level | What | Size | Use |
|---|---|---|---|
| L0 | `Capability.card()`: id, one-line description, parameter names, effects code, idempotency mode | tens of bytes | Discovery across thousands of capabilities. |
| L1 | The Markdown card | a few hundred tokens | Choosing between candidates and filling arguments. |
| L2 | The full Capability document | full contract | Validation and execution. |

## Versioning

`extract(path, previous=lock)` compares each capability with its entry in the previous lock:

| Change | Bump |
|---|---|
| Input or output removed, retyped, or an input becomes required | major |
| Optional input or new output added, or effects, idempotency or security changed | minor |
| Only titles, descriptions or parameter descriptions changed | patch |
| Only layout, designer metadata or comments changed | none |

The lock file records, per artifact, its content hash, and per capability, its version and the
hashes of its contract, metadata and documentation. It contains no timestamps, so extracting
unchanged sources produces an identical lock.

## Overrides

`flowglyph.overrides.yaml`, next to the sources, lets a person correct or complete what the
parser inferred. Fields are deep-merged into the capability; idempotency set this way becomes
`declared` with confidence 1.0.

```yaml
capabilities:
  uipath/invoices/Main:
    description: Books a supplier invoice in the ERP.
    idempotency: {mode: key, key_fields: [in_InvoicePath], ttl_seconds: 86400}
    security: {approval_required: true}
```
