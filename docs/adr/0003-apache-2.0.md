# ADR-0003: Apache License 2.0

- Status: accepted
- Date: 2026-11-04

## Context

The expected adopters are integrators, consultancies and enterprises that would embed
FlowGlyph in internal tooling. A strong copyleft license would block most of them.

## Decision

FlowGlyph is licensed under Apache-2.0. Contributions are accepted under the Developer
Certificate of Origin (`git commit -s`) rather than a CLA.

## Consequences

- Commercial use, modification and redistribution are allowed, with an explicit patent grant.
- The license does not grant trademark rights, so the FlowGlyph name can be protected
  separately if needed.
- Third-party material is tracked in `NOTICE`. Code under licenses not meant for software, such
  as CC BY 4.0, is never vendored or depended on.
