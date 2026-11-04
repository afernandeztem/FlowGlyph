# Contributing to FlowGlyph

Thanks for taking the time to contribute. This document covers how to set up the project,
the conventions the codebase follows, and how changes get merged.

## Development setup

You need [uv](https://docs.astral.sh/uv/) 0.13 or newer. Node 26 is only needed to
regenerate the README diagrams.

```bash
git clone https://github.com/flowglyph/flowglyph
cd flowglyph
make install   # uv sync --all-extras + pre-commit hooks
make check     # ruff, pyright, pytest
```

Tests that call a real LLM provider are marked `llm` and skipped by default. Run them with
`make test-llm` and an `ANTHROPIC_API_KEY` in your environment.

## Project layout

| Path | What lives there |
|---|---|
| `src/flowglyph/ir.py` | The Automation IR models. Changing them is a spec change, see below. |
| `src/flowglyph/adapters/` | One subpackage per source format. Adapters only produce IR. |
| `src/flowglyph/catalog.py` | Catalog, lock file, search and persistence. |
| `src/flowglyph/gateway/` | MCP server, policy engine, idempotency ledger, audit log. |
| `src/flowglyph/planner/` | Requirements to workflow IR. The only place that calls an LLM. |
| `src/flowglyph/_internal/` | Private helpers. Not part of the public API. |
| `tests/golden/` | Expected outputs. Regenerate with `pytest --update-golden` and review the diff. |

## Code style

The bar is code that reads as if one careful person wrote all of it.

- English everywhere: code, docstrings, error messages, commit messages.
- Google-style docstrings on public modules, classes and functions, only when they say
  something the signature does not. Private helpers usually need none.
- No inline comments that describe *what* a line does. A comment is allowed only to explain a
  non-obvious *why*: a workaround, a spec reference, a deliberate trade-off.
- No section banners. If a module needs sections, it needs to be split into modules.
- No commented-out code, no emoji, no `TODO` without a linked issue.
- Full names over abbreviations. `workflow`, not `wf`; `activity`, not `a`.
- Data that crosses a module boundary is a typed model, never an anonymous `dict`.
- Project exceptions derive from `FlowGlyphError`. Never catch bare `Exception`.
- Keep functions small and single-purpose; ruff enforces the limits.

`ruff check`, `ruff format --check` and `pyright` (strict) must pass. Pre-commit runs all
three.

## Changing the IR

The IR is the project's contract with every adapter, catalog and agent that consumes it.
Changes to `ir.py` need:

1. An ADR in `docs/adr/` explaining the change and its migration path.
2. An update to `docs/ir-spec.md` and the generated JSON Schemas (`make schemas`).
3. A bump of `IR_VERSION` following semver: removing or renaming a field is a major change.

## Writing an adapter

Implement the `flowglyph.adapters.Adapter` protocol and register it through the
`flowglyph.adapters` entry point group in your own package. Adapters must be deterministic:
the same input bytes always produce the same IR. No network access, no LLM calls.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`.
- Sign off every commit (`git commit -s`). This certifies the
  [Developer Certificate of Origin](https://developercertificate.org/): that you wrote the
  change or have the right to submit it under the project's license.
- Add an entry under `Unreleased` in `CHANGELOG.md` for user-facing changes.
- Keep pull requests focused. A refactor and a feature are two pull requests.

## Reporting bugs and proposing features

Use the issue templates. For security issues, follow [SECURITY.md](SECURITY.md) instead.

By participating you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
