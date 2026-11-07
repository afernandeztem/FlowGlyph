# Use cases

One FlowGlyph, six situations. Each page tells one of them on its own: who it is for, what
you run, what you see, and how to tell it to others. Every output quoted is the real output of
the commands, replayed on the sources in `tests/fixtures`; the handover folder used throughout
is a UiPath project, the OpenAPI document of a payments API and a two-page Word process
definition, side by side.

| Page | For | In one line |
|---|---|---|
| [1. Is it safe to run twice?](01-retry-safety-audit.md) | RPA leads, SAP integration teams, auditors | Every function of every automation, what it changes and whether a retry is a repeat, from the sources alone |
| [2. A wiki the LLM keeps](02-llm-wiki.md) | Automation CoEs, knowledge owners | One page per function that people and an LLM maintain together, rebuilt without losing a note |
| [3. Context for the coding agent](03-coding-agent-context.md) | UiPath developers using Claude Code, Codex, Cursor | `AGENTS.md` and activity cards written from the project, so the agent changes it the way the project does |
| [4. An agent that cannot break the rules](04-safe-agent-gateway.md) | AI platform teams, security | An MCP gateway you host: contract, policy, one run per key, audit |
| [5. A robot from the client's document](05-design-from-the-clients-document.md) | Solution architects, delivery teams | The process definition as it came, PDF or Word, turned into a checked workflow with the gaps named |
| [6. The same workflow in BPMN or Studio](06-bpmn-and-xaml.md) | Process owners, developers | A planned or existing workflow opened in a BPMN modeler or UiPath Studio |

The six run in order as one story in the [README](../../README.md#from-a-clients-package-to-a-new-robot);
[HOWTO.md](../../HOWTO.md) is the reference for every command they use.
