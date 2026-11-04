<div align="center">

# FlowGlyph

**Turn enterprise automations into capabilities AI agents can discover, plan with and run safely.**

[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-3776ab)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-strict-success)](pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Status](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)

</div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/pipeline-dark.svg">
  <img alt="FlowGlyph pipeline: sources go through deterministic adapters into the Automation IR, which feeds a versioned catalog used by an MCP gateway, a planner and the Python library." src="docs/assets/pipeline-light.svg">
</picture>

## Why

Companies already have thousands of automations: UiPath robots, internal APIs, process models.
Agents could use them, but every platform describes its automations differently, and none of
them tells an agent the two things it needs before pressing a button: **what will this change
in the world, and is it safe to run twice?**

FlowGlyph reads automations with deterministic parsers, translates them into one small
vendor-neutral representation, the **Automation IR**, and serves that to agents through a
gateway that enforces policy and idempotency. The LLM never has to rediscover how a platform
works; it only reads short, typed cards.

## Quickstart

### As a command-line tool

```bash
uv tool install "flowglyph[cli]"          # or: pipx install "flowglyph[cli]"

flowglyph extract ./my-uipath-project -o catalog
flowglyph inspect catalog
```

The same command reads OpenAPI 3.x documents (`flowglyph extract openapi.yaml`): safe methods
become read-only capabilities, `PUT` and `DELETE` are idempotent, and `POST` is retry-safe only
when the operation accepts an `Idempotency-Key` header.

```text
Main RWdX none
├── InitiAllSettings RX natural
├── KillAllProcesses pure natural
├── Initialize Applications pure natural
├── GetTransactionData RWX none
├── Process pure natural
├── SetTransactionStatus RWdX none
│   ├── TakeScreenshot RWdX none
│   ├── CloseAllApplications pure natural
│   └── KillAllProcesses pure natural
└── CloseAllApplications pure natural
```

Every workflow shows its effects (`R` reads, `W` writes, `D` destructive, `X` external, lower
case when unknown) and whether it is safe to retry.

```bash
flowglyph search catalog "read configuration from excel"
flowglyph inspect catalog Framework/InitAllSettings     # the full card
flowglyph validate catalog                              # schema and reference checks
```

Run `extract` again after the sources change and FlowGlyph versions every capability with
semver, so you can tell a harmless edit from a breaking one:

```bash
flowglyph extract ./my-uipath-project -o catalog
flowglyph diff old.lock catalog --fail-on major         # use it as a CI gate
```

### As a Python library

The base package depends only on pydantic and PyYAML.

```bash
pip install flowglyph
```

```python
import flowglyph

catalog = flowglyph.extract("./my-uipath-project")

for capability in catalog.search("read configuration from excel", limit=5):
    print(capability.id, capability.effects.code(), capability.idempotency.mode)

settings = catalog.get("Framework/InitAllSettings")
print([p.name for p in settings.inputs], settings.effects.has_side_effects)

catalog.save("catalog")
catalog = flowglyph.load_catalog("catalog")
```

### As an MCP server for agents

```bash
pip install "flowglyph[mcp]"
flowglyph serve catalog
```

Register it with any MCP client, for example Claude Code:

```bash
claude mcp add flowglyph -- flowglyph serve /path/to/catalog
```

The gateway validates every call against the capability's schema, applies your policy, runs
anything with side effects at most once per idempotency key, and writes an audit log without
argument values. Steps that may destroy data wait for a person:

```bash
flowglyph approvals catalog                  # what is waiting
flowglyph approve catalog '<idempotency key>'
```

Execution is a dry run in this release: the agent gets exactly what would have been sent, with
every guarantee enforced. Policies are plain YAML:

```yaml
default: allow
rules:
  - {capabilities: "openapi/*/executePayment", action: deny, reason: payments are manual}
  - {capabilities: "uipath/*", if_effects: [destructive], action: require_approval}
```

### As a planner

```bash
pip install "flowglyph[llm]"
flowglyph plan requirements.md catalog -o plan
```

Pass `--via claude-code` to plan through the Claude Code CLI with the account it is signed in
with, instead of an API key.

Describe what you need in plain language and FlowGlyph designs the workflow with the
capabilities you already have. Claude proposes the plan; a deterministic resolver then checks
every capability, argument and reference against the catalog. A step that nothing in the
catalog can do is reported as **missing** instead of being invented, so the plan doubles as a
gap analysis. See [examples/invoice-processing](examples/invoice-processing).

## How it works

1. **Adapters parse, deterministically.** An adapter turns one source format into IR. It never
   calls an LLM or the network, so the same input always gives the same output. The UiPath
   adapter reads argument types, defaults and annotations, classifies every activity with an
   [editable taxonomy](src/flowglyph/adapters/uipath/taxonomy.yaml), follows `Invoke Workflow
   File` across the project and keeps branch conditions.

2. **The Automation IR says what an automation does, not how.** A `Capability` has a typed
   contract, effects and an idempotency model. A `Workflow` is the graph behind it. Effects are
   `yes`, `no` or `unknown`, because a parser cannot prove that a click is harmless, and
   pretending otherwise is how agents break production systems.

   ```yaml
   id: uipath/reframework/Framework/GetTransactionData
   kind: workflow
   effects: {reads: yes, mutates_state: yes, destructive: no, external: yes}
   idempotency: {mode: none, provenance: inferred, confidence: 0.7}
   input_schema:
     properties:
       in_TransactionNumber: {type: integer, description: Sequential counter of transaction items.}
   ```

   The full specification is in [docs/ir-spec.md](docs/ir-spec.md).

3. **The catalog is versioned and reviewable.** `catalog.jsonl`, `graph.json` and Markdown cards
   are plain files you can commit and diff. `flowglyph.lock` records content hashes, so an
   unchanged project produces byte-identical output and a changed one gets the right semver
   bump. What the parser can only guess, a person can declare in `flowglyph.overrides.yaml`.

4. **Agents load only what they are about to use.**

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/token-flow-dark.svg">
  <img alt="An agent discovers capabilities as L0 cards, reads a few L1 cards, and calls one tool whose L2 contract is validated by the gateway's policy, idempotency ledger and audit log." src="docs/assets/token-flow-light.svg">
</picture>

| Level | What the agent gets | Size |
|---|---|---|
| L0 | id, one-line description, parameter names, effects, idempotency | ~40 tokens |
| L1 | the Markdown card: inputs, outputs, steps, retry advice | ~300 tokens |
| L2 | the full JSON Schema contract | only for the call being made |

## How FlowGlyph compares

| | FlowGlyph | UiPath native MCP servers | XAML parsers such as `xaml-parser` | Generic OpenAPI to MCP converters |
|---|---|---|---|---|
| Sources | UiPath, OpenAPI, pluggable | UiPath artifacts | UiPath | OpenAPI |
| Vendor-neutral model | yes, the Automation IR | no | no | no |
| Effects and retry safety | tri-state effects, idempotency with provenance | hints | no | hints from HTTP verbs at best |
| Versioning of contracts | semver from a lock file | platform versions | no | no |
| Runs locally, offline | yes | no, cloud platform | yes | yes |
| License | Apache-2.0 | proprietary | CC BY 4.0 | varies |

## Roadmap

- [x] Automation IR, UiPath adapter, versioned catalog, CLI
- [x] OpenAPI 3.0 and 3.1 adapter
- [x] MCP gateway with policy, idempotency ledger and audit log (dry-run executor)
- [ ] Executors that run against UiPath Orchestrator and HTTP APIs
- [x] Planner: requirements in plain language to checked workflow IR
- [ ] LLM enrichment cached by source hash, more adapters (BPMN, SAP), compilers back to BPMN and XAML

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md): it explains the setup
(`make install`, `make check`), the code style and how to write a new adapter. Diagrams are
edited in [Excalidraw](https://excalidraw.com) from the `.excalidraw` files in `docs/assets/`
and re-rendered with `make diagrams`.

Security issues: see [SECURITY.md](SECURITY.md).

## License

[Apache License 2.0](LICENSE). Test fixtures from UiPath ReFrameWork are MIT-licensed, see
[NOTICE](NOTICE).

UiPath and SAP are trademarks of their respective owners. FlowGlyph is an independent project
and is not affiliated with or endorsed by them.
