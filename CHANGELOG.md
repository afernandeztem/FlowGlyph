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
