# Glossary

The words FlowGlyph uses in code, documentation and output, and what each one means. When code
and this page disagree, the code is wrong or this page is out of date: please open an issue.

## The model

**Automation IR**
: The vendor-neutral model of what an automation does, independent of how it is built and how
  an agent calls it. Two documents: capability and workflow. Specified in [ir-spec.md](ir-spec.md).

**Capability**
: One operation an agent can discover, reason about and, if *invocable*, run. Its contract
  (inputs, outputs), its *effects* and its *idempotency* are what FlowGlyph cares about.

**Capability kind**
: `workflow` (an automation you can start), `operation` (an API call) or `activity` (a
  building block, documented but not runnable on its own).

**Invocable**
: Whether a gateway may run the capability directly. Activity types and iFlows without an
  endpoint are not.

**Workflow**
: The graph behind a workflow capability: *nodes* connected by *edges*, plus the capabilities
  it *calls*.

**Node, edge, join**
: A node is a step of a workflow; an edge is control flow between two steps, optionally with a
  *condition*. An edge is *taken* when its source ran and its condition holds. A node's *join*
  says whether it needs `all` incoming edges taken or `any` one. A node that does not run is
  *skipped*, and skips propagate ([ADR-0004](adr/0004-skipped-steps.md)).

**Opaque node**
: A state machine, flowchart or parallel block whose internal control flow is not modelled
  yet. Its children follow it flattened, in document order.

**Unresolved call**
: An invocation that could not be matched to a capability: a missing file, an address no
  iFlow listens on, or a target computed at runtime.

**Effects**
: What running a capability does outside the caller: whether it *reads*, *mutates state*, is
  *destructive* and is *external*. Each is `yes`, `no` or `unknown`.

**Unknown**
: An honest answer when static analysis cannot decide. Every consumer treats it as a possible
  yes.

**Side effects**
: A capability has them when it may mutate state or destroy data, counting unknowns.

**Effects code**
: The compact form of effects: `R`ead, `W`rite, `D`estroy, e`X`ternal; upper case for yes,
  lower case for unknown, absent for no. `RwX` reads, may write and calls another system.

**Idempotency**
: Whether, and how, a capability can be called again safely. Its *mode* is `natural`
  (repeating has no further effect), `key` (safe when deduplicated on *key fields*),
  `conditional` (safe under documented conditions) or `none`.

**Provenance**
: Where an idempotency answer comes from: *declared* by the source (an SAP CPI idempotent
  process call, an exactly-once adapter) or by a person in an *override*, or *inferred* by a
  heuristic, with a *confidence*. Inference never replaces a declaration.

**Compensation**
: The capability that undoes this one, when there is one.

**Trigger**
: How a capability is started: its *kind* (`call`, `schedule` or `event`), the *channel* it
  arrives through (`HTTP`, `OData V4`, `ProcessDirect`, `Orchestrator`, `Timer`) and the
  *address* it listens on.

**Entry point**
: The main workflow of a project, the one an orchestrator starts. Call trees grow from it.

**Configuration**
: Names of externalized parameters a capability depends on, such as SAP CPI `{{parameters}}`.
  FlowGlyph records names, never values.

## Reading sources

**Source**
: Where automations are read from: a folder, a file, or a git repository URL, which is
  shallow-cloned into a cache.

**Adapter**
: The translator from one source format to the IR. Deterministic and offline: the same bytes
  always give the same result. Built in: `uipath`, `sap` (OData), `sap-cpi`, `openapi`.

**Artifact**
: One file an adapter read, such as a `.xaml` workflow, an EDMX document or an `.iflw` inside
  an exported `.zip`. The lock file records a hash of each.

**Diagnostic**
: Something an adapter noticed but did not fail on: `info`, `warning` or `error`, about one
  artifact.

**Taxonomy**
: The UiPath adapter's table of activity categories and the effects each implies
  (`adapters/uipath/taxonomy.yaml`).

**Design finding**
: A problem that makes an SAP CPI iFlow fragile or insecure, such as a router with no default
  route or a receiver with no timeout. Reported as a diagnostic and a note.

## The catalog

**Catalog**
: All capabilities and workflows extracted together, with their lock. It can be searched,
  saved and loaded.

**Lock file**
: `flowglyph.lock`: per artifact its hash, per capability its version and the hashes of its
  contract, metadata and documentation. No timestamps, so it only changes when sources do.

**Versioning, bump**
: Each capability has a semantic version computed against the previous lock. A *bump* is
  `major` (breaking contract change), `minor` (compatible change, or deprecation), `patch`
  (documentation only) or `none`.

**Override**
: A correction or addition a person writes in `flowglyph.overrides.yaml`, deep-merged into the
  capability. Idempotency set this way becomes declared.

**Representation levels: L0, L1, L2**
: Three sizes of the same capability. *L0* is a card of a few dozen bytes for scanning
  thousands; *L1* is the Markdown card for choosing; *L2* is the full contract for validating
  and running.

**Review status**
: The idempotency report's verdict per capability: `safe`, `keyed`, `declared`, `review` when
  it has side effects and no retry guarantee, which a person should settle, or `n/a` when it
  cannot be run on its own, such as an activity type, so the workflows using it decide instead.

## Using the catalog

**Gateway**
: The MCP server that lets agents discover and run capabilities, enforcing what the IR only
  describes.

**Policy**
: Rules the gateway evaluates on every call: `allow`, `deny` or `require_approval`, matched by
  capability id and effects.

**Ledger**
: The gateway's SQLite table of runs by *idempotency key*. Claiming a key is atomic, so a
  repeated call returns the first result instead of running again.

**Idempotency key**
: What identifies a run for deduplication, scoped to one capability: the key the caller passes,
  else the values of the capability's key fields, else a hash of all the arguments.

**Executor**
: What actually runs a capability for the gateway. The default is a dry run; the *connected*
  executor routes each capability to the *connection* that runs it.

**Connection**
: One entry of `flowglyph.connections.yaml`: a system (an HTTP API, an SAP OData service, a
  UiPath Orchestrator folder), how to authenticate with it, and the capability id patterns it
  runs. Credentials are named environment variables, never values.

**Plan, resolver**
: A *plan* is the workflow an LLM proposes from requirements. The *resolver* checks every step
  against the catalog, deterministically: a capability the model invents is reported, never
  accepted.

**Planner backend**
: Who proposes the plan: the Claude API, a coding assistant's command line, an
  OpenAI-compatible server, or a plugin.

**LLM wiki**
: Pages generated from the catalog, in the shape Andrej Karpathy describes: sources are the
  raw layer, FlowGlyph writes the structure, and people or an LLM add *notes* below a marker
  that every rebuild keeps. `AGENTS.md` is the *schema* that tells an LLM how to maintain it.
