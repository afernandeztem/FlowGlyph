# ADR-0002: Python as implementation language

- Status: accepted
- Date: 2026-11-04

## Context

The project needs XML and YAML parsing, JSON Schema, an MCP server, LLM SDKs and a CLI, and it
should be usable as a library from other tools. A prototype already exists in Python.

## Decision

FlowGlyph is written in Python, supports CPython 3.12 to 3.14 and is developed on 3.14.

- Packaging with hatchling and a `src/` layout; version from git tags via hatch-vcs.
- The base install depends only on pydantic and PyYAML. CLI, MCP and LLM support are optional
  extras (`cli`, `mcp`, `llm`).
- Strict typing with pyright and a shipped `py.typed`.

## Consequences

- `pip install flowglyph` gives a small, importable library without pulling an MCP server or an
  LLM client.
- Distribution as a single static binary, as suggested in the research notes, is out of scope.
  `uv tool install flowglyph[cli]` covers the command-line use case.
- 3.15 joins the supported set once it is released; until then it runs in CI as experimental.
