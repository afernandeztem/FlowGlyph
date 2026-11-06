# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Automation IR (`Capability`, `Workflow`, `Effects`, `Idempotency`) with JSON Schemas.
- UiPath adapter: typed arguments with defaults and annotations, a taxonomy of activities with
  tri-state effects, workflow graphs with branches, transitive effects through invocations.
- Catalog with deterministic `save`/`load_catalog`, BM25 search, L0 cards, Markdown cards and
  an index, a lock file with automatic semver bumps, and `flowglyph.overrides.yaml`.
- `flowglyph` command line: `extract`, `validate`, `diff`, `inspect` and `search`.
- README with Excalidraw diagrams rendered to light and dark SVG by `make diagrams`.
- OpenAPI 3.0 and 3.1 adapter: parameters and bodies as one input schema, local `$ref`
  resolution with recursion cut-off, effects and idempotency from HTTP semantics and
  `Idempotency-Key` headers, OAuth scopes and error responses.
- MCP gateway (`flowglyph serve`): L0/L1/L2 discovery tools, one tool per capability or
  search-only exposure, JSON Schema validation, YAML policies with allow, deny and approval,
  an SQLite idempotency ledger with atomic claims and TTL, an audit log without argument
  values, and `flowglyph approve` / `approvals` for people.
- Planner (`flowglyph plan`): BM25 shortlist, a plan proposed by Claude with structured output
  and server-side refusal fallbacks, and a deterministic resolver that rejects invented
  capabilities and broken references and reports missing capabilities as gaps.
- The planner works with any provider. `--via` selects the Anthropic API, a signed-in coding
  assistant run headless (`claude-code`, `codex`, `gemini`, `cursor`, or any tool described with
  a `CommandSpec`), any OpenAI-compatible server (OpenAI, Ollama, vLLM, LM Studio, OpenRouter)
  through the standard library, or a plugin registered under `flowglyph.planners`. Plans use a
  strict JSON Schema that all of them accept.
- SAP adapter (`--adapter sap`): reads OData V2 and V4 `$metadata` (EDMX) from SAP S/4HANA,
  SAP Gateway or SAP BTP. One capability per operation the service allows, honouring
  `sap:creatable`/`updatable`/`deletable` and the V4 Capabilities vocabulary, with typed keys and
  bodies, SAP labels as descriptions, function imports, functions and bound actions.
- Extraction from whole trees and git repositories: `flowglyph extract <folder|file|git URL>`
  reads every project and document it finds, records the origin and commit in the lock, and
  `--adapter` limits it to one source type.
- `flowglyph idempotency`: the catalog and nothing else, one row per function with its effects,
  idempotency and a status (`safe`, `keyed`, `declared`, `review`), filterable by kind, provider,
  side effects or pending review, as a table, Markdown, CSV or JSON. Also `flowglyph.report`.
- `flowglyph adapters` lists the source formats available, plugins included.
- `flowglyph wiki build` and `wiki lint`: an LLM wiki of the catalog in the shape of Karpathy's
  "LLM Wiki". Generated pages per capability, category and source with backlinks, an index, an
  overview, an append-only log of ingests and lint passes, an `AGENTS.md` schema for the LLM that
  maintains it, and Notes sections that survive every rebuild. Lint reports idempotency to
  review, invocations outside the sources, orphan workflows, broken links and retired pages.
- The UiPath taxonomy covers cloud, infrastructure, directory and SaaS connector packages (Azure,
  AWS, Google Cloud, Citrix, Hyper-V, VMware, Active Directory, Jira...) and derives effects from
  the verb in an activity's name (`Get`, `Create`, `Set`, `Delete`, `...Scope`) where the category
  alone cannot tell. On UiPath's IT automation solutions, unclassified activities drop from 118
  to 1 of 172.
- Repository URLs that point at a folder download only that folder (sparse checkout), and the
  checkout is named after the repository.
- Services or APIs published twice in one source, such as the same SAP service as OData V2 and
  V4, keep separate ids. SAP metadata that uses the `sap:` prefix without declaring it is read.
- SAP Cloud Integration adapter (`--adapter sap-cpi`): iFlows exported as `.zip` (read in
  memory, with size and compression limits) or unpacked. One capability per endpoint, effects from
  receivers and steps, ProcessDirect calls resolved across iFlows (from steps, message end events,
  local processes and exception subprocesses), idempotency declared by the iFlow itself, and a
  design review whose findings reach `wiki lint`. Parameter values are never read.
- `wiki lint` lists the notes adapters attach to capabilities.
- `examples/sap-integration`: OData services and Cloud Integration iFlows taken through the
  report, overrides, the wiki and the gateway, with real output. `make examples` regenerates the
  committed example catalogs, and a test fails when they are out of date.
- Documentation: an architecture guide by bounded context, a glossary, decision records 0005 to
  0010, and guides with tested examples for writing an adapter or a planner backend.

### Changed

- IR 0.3.0 (ADR-0005): `Capability` gains typed `trigger`, `entry_point`, `configuration`,
  `used_in` and `deprecated` fields instead of prefixed strings in `tags`. Presentation moves out
  of the IR into `flowglyph.views`: `effects_code`, `retry_advice` and `l0_card` replace
  `Effects.code()`, `Idempotency.advice()` and `Capability.card()`.
- Marking a capability deprecated is now a minor version bump, as semver requires.
- `flowglyph.catalog` is a package (`lock`, `versioning`, `overrides`, `extraction`, `model`);
  its public names are unchanged.
- The gateway applies deny rules before validating arguments, so an agent is not asked to fix
  the arguments of a call it may not make.
- The command line is split into one module per context; `flowglyph.cli.main:app` is unchanged.
- IR 0.2.0: nodes have a `join` (`all` or `any`) and skipped steps propagate, so a workflow
  says what runs after an optional step. `Workflow.simulate` evaluates the rules. The UiPath
  adapter marks branch merges as `any`; the planner chooses a join per step and warns about
  steps that would be skipped with an optional predecessor.

### Fixed

- XML sources that declare a DTD after the first 4 KiB, for example behind a long comment, are
  refused like any other DTD.
- The command line printed source text as Rich markup, so diagnostics lost expressions such as
  `[in_target]`. Source text is now escaped.
- The approval command the gateway suggests includes `--state` when the gateway keeps its state
  elsewhere, and quotes its arguments for the shell.
- The OpenAI-compatible planner refuses a base URL that is not `http` or `https`, so
  `OPENAI_BASE_URL` cannot point the standard library at local files.
- Catalogs, lock files, wikis and plans are written with LF line endings on every platform, so a
  catalog saved on Windows is byte-identical to one saved on Linux or macOS.
- Repositories read from a Windows path are cached under their own name instead of the whole
  path, and git runs with long paths enabled, so deep repositories clone on Windows.
- On Windows, command-line planner backends refuse a `.cmd` or `.bat` launcher when the
  arguments it would receive contain cmd.exe syntax, such as the JSON Schema, instead of letting
  cmd.exe cut them short or redirect them. Arguments without it, such as file paths, still work.
