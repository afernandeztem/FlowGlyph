# How to use FlowGlyph's tools

Every tool FlowGlyph has, what it does, and how to use it. Each entry says what the tool is for,
shows a command, and tells you what you get back.

For a walkthrough that uses these tools one after another on sample projects, read
[docs/guide.md](docs/guide.md). This file is the reference to come back to.

## What FlowGlyph does

FlowGlyph reads your automations (UiPath robots, SAP services and integration flows, BPMN
processes, n8n workflows, APIs) and builds a **catalog**: one entry per function, called a
*capability*, saying what it takes, what it returns, what it changes in other systems, and
whether running it twice is safe. Every tool below either builds that catalog or uses it.

| You want to | Use |
|---|---|
| Know what your automations do | [`extract`](#extract), [`inspect`](#inspect), [`search`](#search), [`idempotency`](#idempotency) |
| Know what is safe to retry | [`idempotency`](#idempotency), then [overrides](#flowglyphoverridesyaml) |
| Catch breaking changes | [`diff`](#diff), [`validate`](#validate) |
| Document them for people and LLMs | [`enrich`](#enrich), [`wiki build`](#wiki-build), [`context`](#context), [`skill`](#skill) |
| Let an AI agent run them safely | [`serve`](#serve), [`approvals`](#approvals), [`approve`](#approve) |
| Design new workflows | [`plan`](#plan), [`compile`](#compile) |

## Install

```bash
pip install "flowglyph[cli]"     # the command line
pip install "flowglyph[mcp]"     # adds the gateway for AI agents
pip install "flowglyph[llm]"     # adds the Anthropic backend for plan and enrich
pip install "flowglyph[all]"     # everything
```

Every command has `--help`. Wherever a command takes a `SOURCE`, it can be a folder, a file, a
git URL, or a catalog you saved before.

## Read your automations

### extract

**What it does:** reads every automation under a folder, file or git repository and saves the
catalog. Run it again after changes: each function gets a new version only when it really
changed.

```bash
flowglyph extract ./automations -o catalog
flowglyph extract https://github.com/UiPath/ReFrameWork -o catalog
flowglyph extract ./automations -o catalog --adapter uipath     # only one kind of source
```

**You get:** a `catalog/` folder you can commit: `catalog.jsonl` (every capability),
`graph.json` (what calls what), `flowglyph.lock` (versions), `INDEX.md` and one Markdown card
per capability. Warnings are printed for things worth knowing, such as a workflow chosen at
runtime.

**Options:** `--adapter` to read one kind of source, `--ref` for a branch, tag or commit of a
repository, `--strict` to fail when a file cannot be parsed.

### adapters

**What it does:** lists the formats FlowGlyph can read, including plugins you installed.

```bash
flowglyph adapters
```

| Adapter | Reads |
|---|---|
| `uipath` | UiPath Studio projects (`project.json`, `.xaml`) |
| `sap` | SAP OData `$metadata`, V2 and V4 |
| `sap-cpi` | SAP Cloud Integration iFlows, `.zip` or unpacked |
| `sbpa` | SAP Build Process Automation projects (`.mtar`) |
| `bpmn` | BPMN 2.0, with Camunda 7 and Camunda 8 extensions |
| `n8n` | n8n workflow exports (`.json`) |
| `openapi` | OpenAPI 3.0 and 3.1 documents |

## Understand them

### inspect

**What it does:** shows what calls what, starting from each entry point, or everything about
one capability.

```bash
flowglyph inspect catalog                                  # the call tree
flowglyph inspect catalog Framework/GetTransactionData     # one capability's card
```

**You get:** a tree where every line is a workflow with its effects and idempotency, or a card
with its description, inputs and outputs with their types, effects, idempotency, steps and full
contract.

### search

**What it does:** finds capabilities by what they do, in plain words.

```bash
flowglyph search catalog "read the configuration from excel"
flowglyph search catalog "queue item" --invocable --limit 5
```

**You get:** the best matches, with their kind, effects, idempotency and description.
`--invocable` leaves out building blocks that cannot run on their own.

### idempotency

**What it does:** lists every function with what it changes and whether it is safe to run
twice. This is the report to review with the people who own the processes.

```bash
flowglyph idempotency catalog
flowglyph idempotency catalog --review                        # only what needs a decision
flowglyph idempotency catalog --side-effects --kind workflow  # only workflows that change things
flowglyph idempotency catalog --format csv -o report.csv      # for a spreadsheet
```

**You get:** one row per function with its effects, idempotency and status (see
[reading the answers](#reading-the-answers)). Formats: `table`, `markdown`, `csv`, `json`.
Filters: `--kind`, `--provider`, `--side-effects`, `--review`.

## Check nothing broke

### validate

**What it does:** checks a saved catalog for broken references: a workflow calling something
missing, a version that does not match the lock file.

```bash
flowglyph validate catalog
```

**You get:** `Valid ...`, or the list of problems and a non-zero exit code.

### diff

**What it does:** compares two catalogs and says which functions changed and how much.

```bash
flowglyph diff old-catalog catalog
flowglyph diff old-catalog catalog --fail-on major     # for CI
```

**You get:** a table of added, removed and changed functions with their version bump. A
**major** change can break a caller (an input removed or made required), **minor** keeps
callers working (a new input, different effects), **patch** is documentation. With
`--fail-on major`, the command fails only on changes that can break a caller.

## Document them

### enrich

**What it does:** asks a language model, once, to describe the functions your sources left
without a description, and to say what each one does for the business (verb, entity, domain).

```bash
flowglyph enrich catalog --via claude-code
flowglyph enrich catalog --via anthropic --limit 20
```

**You get:** the descriptions in the catalog, marked as written by a model. Answers are cached
in `catalog/flowglyph.enrichment.json`, keyed by the source: the next `extract` reuses them
without calling the model, and only functions whose source changed are asked again. The model
sees names, inputs, outputs, effects and steps, never your sources. It never touches
idempotency.

**Options:** `--via` picks who answers (same choices as [`plan`](#plan)), `--model`,
`--effort`, `--limit`.

### wiki build

**What it does:** writes a wiki of the catalog that people and an LLM can keep up to date.

```bash
flowglyph wiki build catalog -o wiki
```

**You get:** one page per function, category and source, with its contract, effects, call tree
and links, plus `index.md`, `overview.md`, an append-only `log.md`, and `AGENTS.md`, which tells
an LLM how to maintain the pages. Anything written under a page's **Notes** heading survives
every rebuild.

### wiki lint

**What it does:** lists what is still open in the wiki.

```bash
flowglyph wiki lint wiki
flowglyph wiki lint wiki --strict     # non-zero exit when there are warnings
```

**You get:** functions to review, workflows nothing calls, calls to things not in the sources,
design problems the adapters found, and broken links.

### context

**What it does:** writes, into every UiPath project, the files a coding agent (Claude Code,
Codex, Cursor, Gemini CLI, UiPath's own skills) reads before working on it. Everything in them
is read from the project, not written by a model.

```bash
flowglyph context ./robots
flowglyph context ./robots --catalog catalog     # with your overrides and enriched descriptions
```

**You get, per project:**

| File | In it |
|---|---|
| `AGENTS.md` and `.claude/rules/project-context.md` | overview, dependencies, structure, entry points with typed arguments, key workflows, what every workflow changes and whether it is safe to retry, the call tree, open questions |
| `.flowglyph/activities/<Activity>.md` | for every activity the project uses, a XAML template from its own workflows: settings kept, values as `[placeholders]` |

Run it again after changes. What you write under **Notes** at the end of these files is kept,
and a file you wrote yourself is never replaced without `--force`. `--out` writes somewhere
else instead of into the projects.

### skill

**What it does:** installs the FlowGlyph skill, the instructions a coding agent loads to know
when and how to use FlowGlyph.

```bash
flowglyph skill                                  # into .claude/skills/flowglyph/
flowglyph skill --to ~/.codex/skills/flowglyph
```

**You get:** a `SKILL.md` telling the agent which command answers which question, and the
rules it follows: read the context before changing a workflow, never retry what is marked
`review`, start new activities from the project's own cards.

## Let an AI agent use them safely

### serve

**What it does:** starts the gateway, an MCP server an AI agent connects to. The agent finds
functions and asks to run them; the gateway decides whether they run.

```bash
flowglyph serve catalog --policy policy.yaml
flowglyph serve catalog --policy policy.yaml --connections flowglyph.connections.yaml
claude mcp add flowglyph -- flowglyph serve /path/to/catalog     # connect Claude Code
```

**On every call the gateway:** checks the arguments against the function's contract, applies
your [policy](#policyyaml), runs anything that changes something at most once per idempotency
key (a retry gets the first result back), and writes the decision to an audit log.

**Options:**
- `--policy`: what an agent may run. Without it, destructive functions wait for a person.
- `--connections`: run for real against the systems in a [connections file](#flowglyphconnectionsyaml). Without it, every run is a dry run that shows what would be sent.
- `--expose`: `all` gives the agent one tool per function, `meta` only the search tools, and `auto` (the default) picks `meta` above 40 functions.
- `--state`: where the ledger and audit log are kept.

The [tools the agent gets](#tools-an-ai-agent-gets) are listed below.

### approvals

**What it does:** lists the runs the policy held for a person.

```bash
flowglyph approvals catalog
```

**You get:** each waiting run's key, function and version.

### approve

**What it does:** lets a held run go ahead. The agent's next attempt with the same key runs.

```bash
flowglyph approve catalog '<key>'
```

The gateway gives the exact command, key included, in its answer to the agent.

## Design new workflows

### plan

**What it does:** designs a workflow from a description in plain language, using only functions
in the catalog. A model proposes the steps; FlowGlyph checks every one.

```bash
flowglyph plan requirements.md catalog -o plan --via claude-code
```

**You get:** `plan/workflow.plan.yaml` (the model's proposal) and `plan/workflow.ir.yaml` (the
checked workflow). A step nothing in the catalog can do is reported as **missing**, never
invented.

**`--via`:**

| Value | Uses | Needs |
|---|---|---|
| `anthropic` (default) | the Anthropic API | `flowglyph[llm]` and an API key |
| `claude-code`, `codex`, `gemini`, `cursor` | that coding assistant, run without its tools | the assistant installed and signed in |
| `openai-compatible` | OpenAI, Ollama, vLLM, LM Studio, OpenRouter | `--model`, and `OPENAI_BASE_URL` / `OPENAI_API_KEY` when needed |

### compile

**What it does:** turns a workflow, planned or already in a catalog, into a file its tool
opens.

```bash
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to bpmn -o invoice.bpmn
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to xaml -o Main.xaml
flowglyph compile catalog uipath/ReFrameWork/Main --to bpmn --engine camunda8 -o main.bpmn
```

| `--to` | You get |
|---|---|
| `bpmn` | BPMN 2.0 with a diagram for any modeler; `--engine camunda7` or `camunda8` adds what that engine needs to run it |
| `xaml` | a UiPath Studio workflow: a Sequence for a straight line, a Flowchart when it branches, with each call's arguments ready to bind |

The command prints what it could not carry over exactly, such as conditions written for another
tool's expression language.

## Tools an AI agent gets

When an agent connects to [`serve`](#serve), it gets these MCP tools:

| Tool | What it does |
|---|---|
| `catalog_search` | finds functions by what they do; returns short cards (a few dozen bytes each) so an agent can scan thousands |
| `catalog_card` | one function's card: inputs, outputs, steps, how to retry it |
| `catalog_contract` | one function's full contract: schemas, effects, idempotency |
| `run_capability` | asks the gateway to run a function, with its arguments and an optional `idempotency_key` |
| `run_status` | the outcome of an earlier run, by its key |
| one tool per function | with `--expose all` (or `auto` and up to 40 functions), each function is its own tool; the optional `_idempotency_key` argument plays the same role |

It can also read the catalog index and every card as MCP resources (`flowglyph://index`,
`flowglyph://cards/...`).

Every run answers with one of these statuses:

| Status | Means |
|---|---|
| `done` | it ran; the result is included |
| `replayed` | it already ran with this key; the first result is returned and nothing ran again |
| `in_progress` | a run with this key is still going |
| `approval_required` | the policy holds it for a person; the answer says how to approve it |
| `denied` | the policy forbids it |
| `invalid` | the arguments do not match the contract, or the function cannot run on its own |
| `conflict` | the key was already used with different arguments |
| `failed` | the system answered with an error; the run can be retried |

## Files you write

### flowglyph.overrides.yaml

Next to the sources. What you know and the sources cannot say. It wins over anything FlowGlyph
inferred.

```yaml
capabilities:
  uipath/ReFrameWork/Framework/SetTransactionStatus:
    idempotency: {mode: key, key_fields: [in_TransactionID]}
  uipath/ReFrameWork/Main:
    description: Process supplier invoices from the AP_Invoices queue.
    idempotency: {mode: natural}
    security: {approval_required: true}
```

### policy.yaml

What an agent may run through the gateway. The first matching rule decides.

```yaml
default: allow
rules:
  - {capabilities: "sap/*/*/delete", action: deny, reason: deletions go through change management}
  - {capabilities: "uipath/ReFrameWork/Main", action: require_approval, reason: live queue}
  - {if_effects: [destructive], action: require_approval, reason: may destroy data}
```

Actions are `allow`, `deny` and `require_approval`. A rule matches by capability id pattern,
by effects (`reads`, `mutates_state`, `destructive`, `external`), or both.

### flowglyph.connections.yaml

The systems the gateway runs against with `--connections`. It holds addresses and the **names**
of environment variables, never passwords or tokens, so it can be committed. `serve` refuses to
start until every variable it names is set.

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
    type: http                       # any API described by an OpenAPI document
    base_url: https://api.example.com/v1
    auth: {type: bearer, token_env: PAYMENTS_TOKEN}
    capabilities: ["openapi/Payments_API/*"]
```

Authentication types: `none`, `bearer`, `basic`, `header` (an API key in a header you name) and
`client_credentials` (OAuth). Every address, token URLs included, must be `https://`; a
connection with `allow_insecure: true` may use `http://`, for a server on your own machine.

## Files FlowGlyph writes

| File | Written by | Holds |
|---|---|---|
| `catalog/catalog.jsonl`, `graph.json`, `INDEX.md`, `capabilities/*.md` | `extract` | the catalog and its cards |
| `catalog/flowglyph.lock` | `extract` | versions; the next `extract` compares against it |
| `catalog/flowglyph.enrichment.json` | `enrich` | cached model answers, reused by `extract` |
| `wiki/` | `wiki build` | the wiki; your notes under **Notes** are kept |
| `AGENTS.md`, `.claude/rules/project-context.md`, `.flowglyph/activities/` | `context` | context for coding agents; your notes are kept |
| `catalog/.flowglyph/ledger.sqlite`, `audit.jsonl` | `serve` | which runs happened, and every decision |
| `plan/workflow.plan.yaml`, `workflow.ir.yaml` | `plan` | the proposal and the checked workflow |

All of them are plain text except the ledger, and the same sources always give the same
catalog, so you can commit them and review their changes.

## From Python

Everything is also a library:

| Call | Does |
|---|---|
| `flowglyph.extract(path)` | builds a catalog, like `extract` |
| `flowglyph.load_catalog(directory)` | loads a saved catalog |
| `catalog.search(text)`, `catalog.get(id)`, `catalog.workflow(id)` | find and read capabilities |
| `catalog.save(directory)` | writes the catalog |
| `report.rows(catalog, statuses=["review"])` | the idempotency report as rows (`from flowglyph import report`) |
| `compilers.compile_workflow(...)` | compiles a workflow, like `compile` (`from flowglyph import compilers`) |
| `Gateway(catalog_dir).run(id, arguments)` | runs a capability through the gateway, without MCP (`from flowglyph.gateway import Gateway`; needs `flowglyph[mcp]`) |

```python
import flowglyph
from flowglyph.views import effects_code

catalog = flowglyph.extract("./automations")
for capability in catalog.search("book an invoice", limit=3):
    print(capability.id, effects_code(capability.effects), capability.idempotency.mode)
```

## Reading the answers

**Effects code:** `R`ead, `W`rite, `D`estroy, e`X`ternal. Upper case means yes, lower case
means it may, a missing letter means no. `RwX` reads, may write and calls another system;
`none` changes nothing.

**Idempotency:**

| Mode | Means |
|---|---|
| `natural` | repeating it changes nothing more |
| `key` | safe when repeated with the same key fields |
| `conditional` | safe only under the conditions its notes describe |
| `none` | every run has an effect |

**Status in the report:**

| Status | Means |
|---|---|
| `safe` | no side effects, or naturally idempotent |
| `keyed` | safe when called with its idempotency key |
| `declared` | the source or a person said how it behaves |
| `review` | it changes something and nothing says it is safe to repeat: decide, and write it in the overrides |
| `n/a` | it never runs on its own, such as an activity type or a timer-only flow |
