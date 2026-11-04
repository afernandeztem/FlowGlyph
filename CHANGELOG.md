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
