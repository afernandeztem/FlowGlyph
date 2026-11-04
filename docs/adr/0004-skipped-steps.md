# ADR-0004: Skipped steps and joins

- Status: accepted
- Date: 2026-11-04

## Context

IR 0.1 had conditional edges but did not say what happens to a step whose predecessor did not
run. The first real plan made the gap visible: "create the invoice" came after "ask for
approval", which only runs above a threshold. Below it, should the invoice be created or not?
Both readings were possible, and an executor or an agent would have had to guess.

## Decision

- An edge is **taken** when its source ran and its condition, if any, holds.
- Every node has a `join`: with `all` (the default) it runs only when every incoming edge is
  taken; with `any` one taken edge is enough. Nodes without incoming edges always run.
- A node that does not run is **skipped**, and none of its outgoing edges are taken, so skips
  propagate.
- A failing step aborts the workflow. Error edges are out of scope for now.
- `Workflow.simulate(holds)` evaluates these rules, so tests, tools and future executors share
  one definition.

The UiPath adapter sets `join: any` where branches of an `If` meet, because a XAML sequence runs
the step after a branch whichever way the branch went. The planner asks the model for a `join`
per step, and the resolver warns when a step with `join: all` mixes predecessors that may be
skipped with ones that always run: the optional-approval pattern.

## Consequences

- IR version 0.2.0. The field has a default, so 0.1 documents still load and mean what they
  were meant to: every predecessor must run.
- Catalog versions do not change, since joins are part of the graph, not of a contract.
- Conditions are still opaque strings; `simulate` takes a function to decide them.
