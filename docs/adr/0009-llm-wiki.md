# ADR-0009: The catalog as an LLM wiki

- Status: accepted
- Date: 2026-11-06 (recorded after the feature shipped)

## Context

A catalog answers "what can be called and is it safe to retry". The people who maintain
automations also need "what is this for, who owns it, what went wrong last time", which no
source states. Andrej Karpathy's "LLM Wiki" describes a pattern for that kind of knowledge: raw
sources that are never modified, a wiki of Markdown pages an LLM writes and keeps current, and a
schema file telling the LLM how.

## Decision

`flowglyph wiki build` writes such a wiki from a catalog, with one change to the pattern: the
structural part of every page is generated, not written by the LLM.

- **Raw layer**: the automation sources, read but never modified.
- **Pages**: one per capability, source and category, plus `index.md` and an overview. Above a
  `<!-- flowglyph:notes -->` marker, FlowGlyph writes contracts, effects, idempotency, call trees
  and backlinks, the same way every time. Below it, people or an LLM add what sources cannot say.
  Rebuilding replaces the part above the marker and keeps the rest.
- **Schema**: `AGENTS.md` tells an LLM what it may edit, what it must not, and how to log its work.
- **Log**: `log.md` is append-only: each build records what changed, by semantic version bump,
  and each lint pass records what it found.
- **Lint**: `flowglyph wiki lint` reports capabilities whose idempotency needs review, missing
  descriptions, design findings from the adapters, workflows nothing calls, calls to things not
  in the sources, broken links, and retired pages. Each pass is logged.
- Pages of capabilities that left the sources are deleted, unless they have notes: then they
  are kept with a banner saying so.

## Alternatives considered

- **Letting the LLM write whole pages**, as in the original pattern. Contracts and effects would
  then be only as reliable as the model, and would drift from the sources.
- **Notes in a separate file per page.** Safer to merge, but readers would have to open two files.

## Consequences

- The wiki is deterministic above the marker, so it can be committed and its diffs reviewed.
- Editing above the marker is lost on the next build; `AGENTS.md` says so.
- The wiki stores a copy of the catalog in `_data/` so it can be linted and rebuilt without the
  sources.
