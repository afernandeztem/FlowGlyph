---
name: flowglyph
description: "Know what an automation does before touching or running it. Use for UiPath (.xaml, project.json), SAP OData, SAP Cloud Integration iFlows, SAP Build Process Automation, BPMN, n8n and OpenAPI: which workflows change data, which are safe to retry, what calls what, and how a project uses each activity. Triggers: 'is it safe to run twice', 'what does this workflow change', 'idempotency', 'side effects', 'retry', 'call tree', 'document this UiPath project', 'AGENTS.md for this project', 'add an activity like the others', 'compile to BPMN', 'serve automations to an agent'."
---

# FlowGlyph

FlowGlyph reads automation sources with deterministic parsers and answers, for every workflow,
operation and API call: its inputs and outputs, what it does to the world (its *effects*) and
whether running it twice is safe (its *idempotency*). Use its answers instead of guessing from
the XML: they are computed from every activity a workflow uses and every workflow it invokes.

If `flowglyph --version` fails, install it with `pip install "flowglyph[cli]"`, or with
`pip install -e ".[cli]"` from a clone of the FlowGlyph repository.

## Rules

1. **Read before you change.** In a UiPath project, run `flowglyph context .` and read the
   generated `AGENTS.md` before editing any workflow. Regenerate it after your changes.
2. **Never retry blindly.** A capability whose status is `review` changes something and nothing
   says it is safe to repeat. Do not run or retry it twice; ask, or run it through
   `flowglyph serve` with an idempotency key.
3. **Copy the project's own activities.** Before adding or changing an activity in a `.xaml`
   file, read its card in `.flowglyph/activities/<Activity>.md` and start from its template:
   replace each `[placeholder]` with this workflow's value and keep the settings as they are.
4. **Facts, not guesses.** Quote effects and idempotency from FlowGlyph's output. When it says
   `unknown`, say unknown.
5. **Notes are for people.** Text above `<!-- flowglyph:notes -->` in a generated file is
   rewritten on the next run; write anything you want kept below that marker.

## Tasks

| The user wants | Run | Then |
|---|---|---|
| Context for working on a UiPath project | `flowglyph context .` | read `AGENTS.md` and the cards in `.flowglyph/activities/` |
| Every function and whether it is safe to retry | `flowglyph idempotency .` | add `--format json` to read it programmatically, `--review` for what needs a decision |
| What one workflow does | `flowglyph inspect . <workflow>` | the card: arguments, effects, idempotency, steps |
| What calls what | `flowglyph inspect .` | the call tree from each entry point |
| A function by what it does | `flowglyph search . "words"` | ranked matches |
| A catalog to commit or compare | `flowglyph extract . -o catalog` | then `flowglyph diff old-catalog catalog --fail-on major` to catch breaking changes |
| Declare what the sources cannot say | write `flowglyph.overrides.yaml` next to the sources | then extract again; see below |
| Turn a workflow into BPMN or UiPath XAML | `flowglyph compile catalog <workflow> --to bpmn` | read the warnings it prints |
| Let an agent run automations safely | `flowglyph serve catalog --policy policy.yaml` | the gateway enforces policy, idempotency and audit |
| Formats FlowGlyph reads | `flowglyph adapters` | `uipath`, `sap`, `sap-cpi`, `sbpa`, `bpmn`, `n8n`, `openapi` |

## Reading the answers

- **Effects code:** `R`ead, `W`rite, `D`estroy, e`X`ternal. Upper case means yes, lower case
  means unknown, a missing letter means no. `RwX` reads, may write and calls another system.
- **Idempotency:** `natural` (repeating changes nothing), `key` (safe when deduplicated on the
  listed key fields), `conditional` (safe under documented conditions), `none` (every run has
  an effect).
- **Status:** `safe`, `keyed`, `declared` (the source or a person said how it behaves),
  `review` (decide before retrying), `n/a` (never runs on its own, such as an activity type).

## Declaring what the sources cannot say

When the user knows something the XAML or API document cannot say, write it in
`flowglyph.overrides.yaml` next to the sources and extract again. Ask before declaring anything
on the user's behalf.

```yaml
capabilities:
  uipath/MyProcess/Framework/SetTransactionStatus:
    idempotency: {mode: key, key_fields: [in_TransactionID]}
  uipath/MyProcess/Main:
    description: Process supplier invoices from the AP_Invoices queue.
    security: {approval_required: true}
```

Declared answers are marked `declared` and win over what FlowGlyph inferred; changing them
moves the capability's version.
