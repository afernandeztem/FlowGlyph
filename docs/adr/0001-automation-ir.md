# ADR-0001: An Automation IR is the core of the project

- Status: accepted
- Date: 2026-11-04

## Context

Vendors already expose their own automations to agents: UiPath publishes workflows and
activities as MCP tools, SAP does the same with Automation Pilot and Integration Suite. A
project that only wraps one vendor's artifacts as MCP tools adds little and is coupled to that
vendor's format.

What is missing is a description of *what an automation does* that is independent of *how it is
implemented* and *how an agent calls it*: its inputs and outputs, its side effects, whether a
retry is safe, what it depends on.

## Decision

FlowGlyph is built around an intermediate representation, the Automation IR, with two objects:

- `Capability`: one operation, with typed input/output schemas, effects, an idempotency model,
  security requirements and a reference to its source artifact.
- `Workflow`: a graph of nodes that reference capabilities, with conditional edges.

Adapters translate a source format (UiPath XAML, OpenAPI) into IR and nothing else. Everything
downstream (catalog, MCP gateway, planner, future compilers) consumes only IR.

Adapters are deterministic. LLMs never discover structure; they may only add semantics on top
of IR produced statically, and their output is cached by source hash.

Effects are tri-state (`true`, `false`, `unknown`) because static analysis cannot prove the
absence of a side effect for UI automation. Idempotency carries a provenance (`declared` or
`inferred`). Enforcement is a runtime property of the gateway, not of the IR.

## Consequences

- New sources only need an adapter; new targets only need a consumer of IR.
- The IR is a public contract and is versioned with semver (`IR_VERSION`). Field removals are
  breaking changes and require a new ADR.
- Some source semantics will not fit the IR at first (state machines, parallel branches). They
  are represented as opaque nodes until the IR can express them.
