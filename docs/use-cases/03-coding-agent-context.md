# 3. Context for the coding agent

**For:** UiPath developers who work with Claude Code, Codex, Cursor or Gemini CLI.
**Takes:** one command per project. **Needs:** `pip install "flowglyph[cli]"`.

## The situation

A coding agent opened on a UiPath project sees XML. It does not know which workflow is the
entry point, what the arguments mean, which activity the project uses to write to a queue or
how it configures it, or that one workflow must never be run twice. So it guesses, and the
guess looks plausible. The fix is the same as for a human newcomer: a briefing, except that
it has to stay true after every change.

## What you do

```bash
flowglyph context ./handover                       # every UiPath project under the folder
flowglyph context ./handover --catalog catalog     # with your overrides and enriched descriptions
flowglyph skill                                    # the agent's instructions for using FlowGlyph
```

## What you see

```text
Context Invoices: 9 files written, 0 unchanged, in handover/Invoices
```

`handover/Invoices/AGENTS.md`, read from the project and nothing else:

```markdown
## Entry Points

| File | Input Arguments | Output Arguments | Purpose |
|---|---|---|---|
| `Main.xaml` | `in_Threshold`: number | `out_InvoiceId`: string or null | Validate an invoice and book it, asking for approval above the threshold. |

## Effects and Retry Safety

| Workflow | Effects | Idempotency | Status | Retrying |
|---|---|---|---|---|
| `Main.xaml` | WX | none | review | not idempotent: run through the gateway with an idempotency key |
| `Steps/BookInvoice.xaml` | WX | key | declared | safe to retry when deduplicated on in_Invoice |
| `Steps/ValidateVendor.xaml` | none | natural | safe | safe to retry |
```

`.flowglyph/activities/AddQueueItem.md`, one card per activity the project uses:

```markdown
# AddQueueItem — as used in Invoices

- **Effects**: WX (changes state, calls other systems)
- **Used in**: `Steps/BookInvoice.xaml`

## Template
From `Steps/BookInvoice.xaml`, its richest use in this project.

<ui:AddQueueItem DisplayName="Queue booking" QueueType="Invoices" />
```

The same content goes to `.claude/rules/project-context.md`, so Claude Code loads it on its
own; the skill installed by `flowglyph skill` adds the rules: read the context before changing a
workflow, never retry what is marked `review`, start a new activity from the project's own card.

## What changes

The agent adds an activity the way this project adds it, with the same properties, binds
arguments by their real names and types, and knows which workflows it must not run twice. Run
`flowglyph context` again after every change; what you write under **Notes** is kept, and a
file you wrote yourself is never replaced without `--force`.

## Telling it

- **Hook:** `AGENTS.md` for a UiPath project, written from the project itself, not by a model,
  so it is right after every commit.
- **Three points:** entry points with typed arguments and the call tree; an XAML template per
  activity taken from the project's richest use of it; retry safety the agent cannot miss.
- **Demo:** `flowglyph context` on the ReFrameWork, then ask Claude Code to "add a step that
  logs the transaction number after GetTransactionData" and show it using the project's own
  `LogMessage` card.
- **Where:** the UiPath Community Forum and UiPath developer channels, a Claude Code /
  Codex-focused post on X or dev.to, a LinkedIn version for RPA teams adopting coding agents.
