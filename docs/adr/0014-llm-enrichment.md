# ADR-0014: Enrichment by a language model, cached by source hash

- Status: accepted
- Date: 2026-11-07

## Context

ADR-0001 keeps language models out of extraction: everything in a catalog is read from a source.
Many sources say little. The ReFrameWork's `Main` keeps the template's `[Process title]`
description; n8n workflows rarely have notes; BPMN processes often lack documentation. Search,
the planner and the people reading cards all work worse on capabilities nobody described, and no
capability had business semantics (verb, entity, domain) at all.

## Decision

- **A separate step, `flowglyph enrich`**, after extraction. It sends a model what the catalog
  already knows about each capability (id, title, description, inputs, outputs, effects, step
  labels) and asks for a one-sentence summary and the business verb, entity and domain. Sources
  and configuration never leave the machine.
- **Only what the sources left empty.** A description is written only when there is none, it is
  a template placeholder, or it says nothing beyond the title. Semantics are written only when
  none are known. Activity types are skipped: their vendor documents them.
- **Marked as generated.** IR 0.4.0 adds `Capability.generated`, the fields a model wrote. Cards
  say a model wrote them. Overrides still win: a person's description is never replaced.
- **Never idempotency.** A model's guess must not move a capability out of review. Retry safety
  stays with sources and people.
- **Cached by source hash.** Answers live in `flowglyph.enrichment.json` next to the catalog,
  keyed by capability id and source hash, with a prompt version. `extract` into that directory
  applies them after overrides and before versioning, through a generic `refine` step, so an
  unchanged source gives an unchanged catalog and lock. A changed source invalidates only its
  own answers.
- **Any backend.** Planner backends gained `answer(system, prompt, shape)`, a structured answer
  for any pydantic model; planning and enrichment both use it. Answers about ids that were not
  asked about are dropped.

## Alternatives considered

- **Enriching during extraction.** Extraction would need credentials, a network and a model, and
  would stop being deterministic.
- **A cache keyed by model.** Changing model would then ask everything again; the source is what
  decides whether an answer is still true.

## Consequences

- The first enrichment of a capability is a patch version: its documentation changed.
- Enrichment quality depends on the backend and on how much the catalog knows; a capability with
  no inputs, outputs or steps gets a thin summary, and says no more than it was given.
