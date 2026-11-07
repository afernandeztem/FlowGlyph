# How to use FlowGlyph

This guide walks through every feature in the order you would use them. Each step is one or two
commands, what they give you, and what to do next. You can follow it with your own automations,
or with the samples in this repository (the commands below use them).
For every option of every tool, see [HOWTO.md](../HOWTO.md).

```
  your automations          1 extract        2 look           3 settle         4 check
  UiPath, SAP, BPMN,   ──►  a catalog   ──►  what does   ──►  what the    ──►  nothing broke
  n8n, OpenAPI               of every         each one do?     sources          in CI
                             function                          cannot say

                            5 describe       6 let agents     7 design and
                       ──►  wiki and    ──►  run it      ──►  compile new
                            enrichment       safely           workflows
```

## 0. Install

```bash
pip install "flowglyph[cli]"         # the command line
pip install "flowglyph[all]"         # everything: the MCP gateway and the Anthropic planner too
```

Python 3.12 or newer. To follow this guide with the samples:

```bash
git clone https://github.com/afernandeztem/FlowGlyph
cd FlowGlyph
cp -R examples/uipath-reframework/sources robots
cp examples/uipath-reframework/overrides.yaml examples/uipath-reframework/policy.yaml .
cp -R examples/sap-integration/sources sap
```

`robots` is UiPath's ReFrameWork template; `sap` holds SAP Cloud Integration iFlows and two SAP
OData services; `overrides.yaml` and `policy.yaml` are used in steps 3 and 6. Until there is a
release on PyPI, the clone is also the way to get the command: `uv sync --all-extras` once,
then run every command below as `uv run flowglyph ...`.

## 1. Build a catalog

```bash
flowglyph extract robots -o catalog
```

FlowGlyph reads every automation under the folder and writes a **catalog**: one entry, called a
*capability*, per function it found, with its inputs, outputs, what it does to the world
(*effects*) and whether it is safe to run twice (*idempotency*).

```
Extracted 13 invocable capabilities and 38 that cannot be run on their own into catalog
  warning ReFrameWork/Tests/RunAllTests.xaml: invokes a workflow chosen at runtime by ...
```

Warnings are things worth knowing, not failures.

**Where it can read from:**

| You have | Run |
|---|---|
| a folder | `flowglyph extract ./automations -o catalog` |
| one file | `flowglyph extract ./api.yaml -o catalog` |
| a git repository | `flowglyph extract https://github.com/UiPath/ReFrameWork -o catalog` |
| one folder of a repository | `flowglyph extract https://github.com/org/repo/tree/main/flows -o catalog` |

**What it understands** (`flowglyph adapters` lists them):

| `--adapter` | Reads |
|---|---|
| `uipath` | UiPath Studio projects (`project.json`, `.xaml`) |
| `sap` | SAP OData `$metadata` (V2 and V4) |
| `sap-cpi` | SAP Cloud Integration iFlows, `.zip` or unpacked |
| `sbpa` | SAP Build Process Automation projects (`.mtar`) |
| `bpmn` | BPMN 2.0, including Camunda 7 and 8 |
| `n8n` | n8n workflow exports (`.json`) |
| `openapi` | OpenAPI 3.0 and 3.1 |

By default every adapter is tried. To read only one kind:

```bash
flowglyph extract sap --adapter sap -o sap-catalog       # only the OData services
```

**What is in `catalog/`:** `catalog.jsonl` (every capability, one per line), `graph.json` (how
workflows call each other), `flowglyph.lock` (versions), `INDEX.md` and one Markdown card per
capability in `capabilities/`. Everything is plain text, the same every time for the same
sources, so you can commit it and review its changes.

## 2. See what you have

**The call tree**, starting from each entry point:

```bash
flowglyph inspect catalog
```

```
Main RWdX none
├── InitiAllSettings RX natural
├── GetTransactionData RWX none
...
```

Each line is a workflow, its effects and its idempotency. The effects code reads `R`ead,
`W`rite, `D`estroy, e`X`ternal: upper case means yes, lower case means it may (the sources do not
say), a missing letter means no.

**One capability in full:** `flowglyph inspect catalog Framework/GetTransactionData`

**Find something by what it does:** `flowglyph search catalog "queue item"`

**The idempotency report**, every function and whether it is safe to retry:

```bash
flowglyph idempotency catalog
flowglyph idempotency catalog --review                       # only what needs a decision
flowglyph idempotency catalog --format csv -o report.csv     # for a spreadsheet
```

| Status | Means |
|---|---|
| `safe` | no side effects, or repeating it changes nothing |
| `keyed` | safe when called with its idempotency key |
| `declared` | someone (the source or a person) declared how it behaves |
| `review` | it changes something and nothing says it is safe to repeat: decide |
| `n/a` | it never runs on its own (an activity type, a timer-only flow) |

## 3. Settle what the sources cannot say

A source cannot tell FlowGlyph that a workflow takes items from a queue that never hands out the
same item twice, or that setting a status twice is harmless. You can. Write it in
`flowglyph.overrides.yaml` **next to the sources**:

```yaml
capabilities:
  uipath/ReFrameWork/Framework/SetTransactionStatus:
    idempotency: {mode: key, key_fields: [in_TransactionID]}
  uipath/ReFrameWork/Main:
    description: Process supplier invoices from the AP_Invoices queue.
    idempotency: {mode: natural}
    security: {approval_required: true}
```

```bash
cp overrides.yaml robots/flowglyph.overrides.yaml      # the sample's overrides
flowglyph extract robots -o catalog
```

```
Capability                                         Change   Bump   Version
uipath/ReFrameWork/Framework/SetTransactionStatus  changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Main                            changed  minor  1.0.0 -> 1.1.0
...
```

What you declare is marked `declared` and wins over anything FlowGlyph inferred. Run
`flowglyph idempotency catalog --review` again: the list gets shorter. Repeat until it is empty.

**Versions** move on their own: `major` when a change can break a caller (an input removed or
made required), `minor` when callers keep working but should know (a new input, different
effects or idempotency), `patch` for documentation.

## 4. Check nothing broke, in CI

```bash
flowglyph validate catalog                              # broken references inside a catalog
```

`diff` compares two catalogs, so keep the one from step 3 before changing anything:

```bash
cp -R catalog old-catalog
flowglyph extract robots -o catalog                     # after a change to a workflow
flowglyph diff old-catalog catalog --fail-on major      # exits 1 only on breaking changes
```

Keep the catalog in git, extract on every pull request and run `diff` against `main`: a change
to a workflow that would break the agents or processes calling it fails the build.

## 5. Describe it, for people and for LLMs

**Descriptions for what nobody described.** Templates keep placeholder descriptions and many
workflows have none. A language model can write them, once:

```bash
flowglyph enrich catalog --via claude-code
```

It sees only what the catalog knows (names, inputs, outputs, effects, steps), never your
sources. Every text it writes is marked as written by a model. Answers are cached in
`catalog/flowglyph.enrichment.json` and reused by every later `extract` into the same folder;
only functions whose source changed are asked again.

**A wiki** your team and an LLM can keep up to date:

```bash
flowglyph wiki build catalog -o wiki
flowglyph wiki lint wiki
```

One page per function, process and category, with its contract, effects, call tree and links.
Write what the sources cannot say under the **Notes** heading of any page: it survives every
rebuild. `wiki/AGENTS.md` tells an LLM (Claude Code, Codex, Cursor...) how to maintain the
pages. `wiki lint` lists what is still open.

## 6. Let an AI agent use the automations safely

```bash
pip install "flowglyph[mcp]"
flowglyph serve catalog --policy policy.yaml
```

This is an MCP server: connect any agent to it, for example
`claude mcp add flowglyph -- flowglyph serve /path/to/catalog`. The agent finds functions,
reads their cards and asks to run them. The gateway, not the agent, decides:

1. it checks the arguments against the function's contract;
2. it applies your policy: allow, deny, or wait for a person;
3. it runs anything with side effects at most once per idempotency key, so a retry gets the
   first result instead of running again;
4. it writes every decision to an audit log.

A **policy** says what an agent may do:

```yaml
default: allow
rules:
  - {capabilities: "uipath/ReFrameWork/Tests/*", action: deny, reason: tests run in Studio}
  - {capabilities: "uipath/ReFrameWork/Main", action: require_approval, reason: live queue}
  - {if_effects: [destructive], action: require_approval, reason: may destroy data}
```

When a run waits for a person, approve it from a terminal:

```bash
flowglyph approvals catalog            # what is waiting
flowglyph approve catalog '<key>'      # let it run; the agent's next attempt goes through
```

**Dry run or real.** Without anything else, every run is a dry run that shows what would be
sent. To run for real, describe each system once in `flowglyph.connections.yaml` and add
`--connections flowglyph.connections.yaml`:

```yaml
connections:
  erp:
    type: odata                      # SAP OData V2 or V4
    service_url: https://erp.example.com/sap/opu/odata/sap/ZSUPPLIER_INVOICE_SRV
    auth: {type: basic, user_env: SAP_USER, password_env: SAP_PASSWORD}
    capabilities: ["sap/ZSUPPLIER_INVOICE_SRV/*"]
  robots:
    type: uipath                     # UiPath Orchestrator: starts the process as a job
    url: https://cloud.uipath.com/acme/finance/orchestrator_
    folder: Finance
    auth: {type: client_credentials, token_url: https://cloud.uipath.com/identity_/connect/token,
           client_id_env: UIPATH_CLIENT_ID, client_secret_env: UIPATH_CLIENT_SECRET}
    capabilities: ["uipath/*"]
  payments:
    type: http                       # any API from an OpenAPI document
    base_url: https://api.example.com/v1
    auth: {type: bearer, token_env: PAYMENTS_TOKEN}
    capabilities: ["openapi/Payments_API/*"]
```

The file holds addresses and the **names** of environment variables, never passwords or
tokens, so you can commit it. `serve` refuses to start until every variable it names is set.

## 7. Design new workflows, and turn them into BPMN or UiPath

**Plan** a workflow from a description in plain language:

```bash
flowglyph plan requirements.md catalog -o plan --via claude-code
```

A model proposes the steps, using only functions that exist in the catalog; FlowGlyph checks
every step. What nothing in the catalog can do is reported as **missing**, never invented. Use
whatever you already have: `--via claude-code`, `codex`, `gemini`, `cursor` (the coding
assistant you are signed in to), `anthropic` (an API key) or `openai-compatible` (OpenAI,
Ollama, vLLM...).

**Compile** a planned workflow, or any workflow in a catalog, into a file its tool opens:

```bash
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to bpmn -o invoice.bpmn
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to xaml -o Main.xaml
flowglyph compile catalog uipath/ReFrameWork/Main --to bpmn --engine camunda8 -o main.bpmn
```

| `--to` | Opens in |
|---|---|
| `bpmn` | any BPMN modeler; with `--engine camunda7` or `camunda8`, ready for that engine |
| `xaml` | UiPath Studio: calls to UiPath workflows come with their arguments to bind |

The compiler lists what it could not carry over exactly, such as conditions written for another
tool's expression language.

## 8. Give coding agents the context to work on a project

Before an agent changes a UiPath project, it should know what each workflow does. Write it down
for it, from the sources:

```bash
flowglyph context robots        # into every UiPath project under the folder
flowglyph skill                 # teach your coding agent when and how to use FlowGlyph
```

Each project gets an `AGENTS.md` (read by Claude Code, Codex, Cursor and Gemini CLI) and the
same text in `.claude/rules/project-context.md` (read by UiPath's own skills), with its entry
points, arguments and their types, call tree, and what every workflow changes and whether it is
safe to retry. For every activity the project uses there is a card in
`.flowglyph/activities/` with a XAML template from the project's own workflows: an agent adding
a Send Email copies how this project already sends email, and fills in the `[placeholders]`.

Run it again after changing the project. What you write under **Notes** at the end of these
files is kept; a file you wrote yourself is never replaced unless you add `--force`. With
`--catalog catalog` it uses a saved catalog, so your overrides and enriched descriptions carry
through.

## From Python

Everything above is also a library:

```python
import flowglyph
from flowglyph import report
from flowglyph.views import effects_code

catalog = flowglyph.extract("robots")
for capability in catalog.search("get the next queue item", limit=3):
    print(capability.id, effects_code(capability.effects), capability.idempotency.mode)

for row in report.rows(catalog, statuses=["review"]):
    print("review:", row.id)

catalog.save("catalog")
catalog = flowglyph.load_catalog("catalog")
```

## Every command

Every command has `--help`, and [HOWTO.md](../HOWTO.md) describes each one: what it does, an
example, what you get back and its options.

## When something goes wrong

| You see | Do |
|---|---|
| `nothing to extract in ...` | the folder holds nothing an adapter recognises; check the path, or name the adapter with `--adapter` |
| `git clone failed` | the repository is private or the URL is wrong; clone it yourself and extract the folder |
| `set these environment variables before serving` | export the variables your connections file names |
| `the gateway needs: pip install 'flowglyph[mcp]'` | install the extra it names |
| `no Anthropic credentials` | export `ANTHROPIC_API_KEY`, or plan with the assistant you are signed in to: `--via claude-code`, `codex`, `gemini` or `cursor` |
| `the 'claude' command is not on PATH` | install that assistant's command line, or choose another `--via` |
| `... is a batch file, and cmd.exe cannot pass it the plan schema` | on Windows, use the assistant's native executable or `--via anthropic` |
| `conditions are copied as written` | rewrite those conditions in the target tool's expression language |
| many rows in `review` | normal at first: declare what you know in `flowglyph.overrides.yaml` and extract again |

For how FlowGlyph is built, read [architecture.md](architecture.md); for its words,
[glossary.md](glossary.md); for why things are the way they are, the
[decision records](adr/README.md).
