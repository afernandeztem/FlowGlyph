# ADR-0015: Context files for coding agents, written from the sources

- Status: accepted
- Date: 2026-11-07

## Context

Coding agents now build and change automations. They read a project's `AGENTS.md` before working
on it, and UiPath ships agent skills (UiPath/skills) that do three things:

- a *project discovery agent*, running on a language model, reads a UiPath project and writes
  `.claude/rules/project-context.md` and `AGENTS.md` from a template (overview, dependencies,
  structure, entry points, conventions, key workflows, architecture, quick reference). It reuses
  the file when it already exists;
- per activity package, Markdown documents with XAML snippets whose values are placeholders,
  so an agent copies structure instead of inventing it;
- idempotency appears as a design question ("idempotency key / pre-write check / queue unique
  reference") and as review checklists, judged by a model or a person.

FlowGlyph already knows, from the sources, everything the discovery agent infers, and computes
what it cannot: effects and retry safety per workflow, transitively.

## Decision

- **`flowglyph context` writes the same files, in the same sections**, generated from the catalog
  and `project.json`. It starts with the same `discovery-metadata` line and keeps within the same
  200-line budget. It adds sections a model cannot fill reliably: *Effects and Retry Safety*, the
  *Call Tree* and *Open Questions*. Because UiPath's discovery agent reuses an existing file,
  UiPath's own skills then work from computed facts.
- **Activity cards from the project itself.** The UiPath adapter keeps, per activity type, the
  XAML of its richest use in the project as a template: designer metadata dropped, settings
  (booleans, enums, numbers, `{x:Null}`) kept, every other value (expressions, text, paths,
  passwords) replaced by a `[placeholder]` named after the property, nested activities replaced
  by `<!-- activities -->`, and the project's own namespace prefixes listed. Generic per-package
  documentation tells an agent what an activity can do; a card shows how this team uses it.
- **Generated files are safe to regenerate.** Text below `<!-- flowglyph:notes -->` is kept; a
  file without FlowGlyph's marker is never replaced without `--force`.
- **An Agent Skill.** `SKILL.md` tells a coding agent when to run FlowGlyph and the rules it
  follows: read the context before changing a workflow, never retry what is marked `review`,
  start new activities from the card. It ships in the package (`flowglyph skill` installs it) and
  the repository carries plugin manifests for Claude Code, Codex, Cursor and Gemini CLI.

## Alternatives considered

- **A model writing the context**, as UiPath's agent does. It reads the same files and may still
  misread an argument type or invent a convention; FlowGlyph has the facts already.
- **Copying UiPath's activity documents.** They are generic and versioned per package; they
  already exist in UiPath's skills, and a project's own usage is what they cannot give.

## Consequences

- Templates are only as good as the project's own XAML: an activity used once with few settings
  gives a thin template.
- Values that look like settings (a capitalised word such as a sheet name) are kept; everything
  else is a placeholder, so no expression, path or secret reaches a card.
- Only UiPath projects get context files for now; other formats are served by the catalog, the
  wiki and the gateway.
