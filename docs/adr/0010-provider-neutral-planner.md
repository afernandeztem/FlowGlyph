# ADR-0010: Planner backends are pluggable and provider-neutral

- Status: accepted
- Date: 2026-11-06 (recorded after the feature shipped)

## Context

The first planner called the Claude API, which needs an API key. Many people who would try
FlowGlyph already use a coding assistant signed in with a subscription (Claude Code, Codex,
Gemini CLI, Cursor), or run a local model behind an OpenAI-compatible server. Tying planning to
one provider would keep them out, and nothing in planning depends on a provider.

## Decision

- A backend is anything implementing `PlanModel.propose(requirements, candidates) -> Plan`.
- Every backend receives the same input, the requirements and a card for each of about 20
  candidate capabilities found by BM25, and must answer with JSON that validates against
  `plan_json_schema()`, which is strict: no additional properties anywhere. The instructions ask
  for candidate ids only, and the resolver rejects any other.
- Built in:
  - `anthropic`: the Claude API with structured output.
  - `claude-code`, `codex`, `gemini`, `cursor`: the signed-in command line of each assistant,
    run headless with no tools, described by a `CommandSpec` preset.
  - `openai-compatible`: any chat completions server (OpenAI, Ollama, vLLM, LM Studio...).
- Other packages add backends under the `flowglyph.planners` entry point group, as a factory
  `(model, effort) -> PlanModel`.
- Whatever the backend, the resolver checks the plan against the catalog. A backend can propose
  a bad plan; it cannot make FlowGlyph accept one.

## Alternatives considered

- **One multi-provider SDK.** It would add a large dependency for a single call, and still not
  cover coding assistants' command lines.
- **Claude only.** Simplest to support, but it excludes people for reasons that have nothing to
  do with the quality of plans.

## Consequences

- Plan quality varies by backend. `tests/eval/test_planner_eval.py` runs the same ten cases on
  any backend (`FLOWGLYPH_PLANNER`, `FLOWGLYPH_MODEL`) so they can be compared.
- What leaves the machine is the same for every backend: the requirements and candidate cards,
  never sources, never configuration.
- Command-line backends depend on each tool's flags; presets are small so they are easy to fix
  when a tool changes.
