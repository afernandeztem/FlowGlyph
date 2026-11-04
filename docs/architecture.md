# Architecture

FlowGlyph is a pipeline of small, independent stages. Each stage only consumes the output of
the previous one, so they can be used, tested and replaced on their own.

```
sources ──► adapters ──► Automation IR ──► catalog ──┬──► gateway (MCP) ──► executors
                                                      ├──► planner ──► workflow IR
                                                      └──► your code (import flowglyph)
```

| Package | Responsibility | Depends on |
|---|---|---|
| `flowglyph.ir` | The data model. No I/O. | pydantic |
| `flowglyph.adapters` | Source format to IR. Deterministic, offline. | `ir` |
| `flowglyph.catalog` | Versioning, overrides, search, persistence. | `ir`, `adapters` |
| `flowglyph.gateway` | Validation, policy, idempotency ledger, audit, MCP transport. | `catalog`, `mcp`, `jsonschema` |
| `flowglyph.planner` | Requirements to workflow IR. The only stage that calls an LLM. | `catalog`, `anthropic` |
| `flowglyph.cli` | The `flowglyph` command. Thin wrappers over the stages above. | `typer`, `rich` |

## Principles

**Structure is parsed, never guessed.** Everything that can be read from a source (types,
defaults, call graphs, HTTP semantics) is read by an adapter. The planner only chooses between
capabilities that already exist and is checked by a resolver that does not trust it.

**Unknown is an answer.** Effects are `yes`, `no` or `unknown`. Every consumer treats unknown
as a possible yes: the policy engine, the gateway's decision to use the ledger, the retry
advice on cards.

**Guarantees live in the gateway, not in hints.** MCP annotations and IR idempotency modes
describe intent. The gateway enforces it: one execution per key, enforced with an atomic
insert in SQLite, and a policy evaluated on every call.

**Output is reviewable.** Catalogs are plain JSON Lines, JSON, YAML and Markdown. Saving is
deterministic, so a catalog can be committed and its changes reviewed like code.

## Extending

- **A new source**: implement `flowglyph.adapters.Adapter` and register it under the
  `flowglyph.adapters` entry point group.
- **A new execution target**: implement `flowglyph.gateway.Executor` and pass it to `Gateway`.
- **Another model provider for planning**: implement `flowglyph.planner.PlanModel` and register
  a factory `(model, effort) -> PlanModel` under the `flowglyph.planners` entry point group.
  Coding assistants with a headless mode only need a `flowglyph.planner.command.CommandSpec`.
