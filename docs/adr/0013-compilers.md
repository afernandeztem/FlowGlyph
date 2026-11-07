# ADR-0013: Compiling workflow IR back into BPMN and UiPath XAML

- Status: accepted
- Date: 2026-11-07

## Context

The planner designs workflows over existing capabilities, and adapters extract workflows from
UiPath, SAP, BPMN and n8n. Both end as workflow IR: a graph of steps, conditions and joins. To be
useful outside FlowGlyph, that graph has to become something a team's own tool opens and runs.

## Decision

A **Compilation** context, `flowglyph.compilers`, with one compiler per target. Each takes a
workflow, the capability it belongs to and, optionally, the catalog that says what each step
calls; each returns the document and the list of what it could not carry over exactly.

- **BPMN 2.0.** Steps become tasks, decisions exclusive gateways, and calls to BPMN processes call
  activities. A step with `join: all` and several predecessors gets a parallel join in front of
  it; one with `join: any` takes its incoming flows directly. A decision's single unconditioned
  branch becomes its default flow, since an exclusive gateway may not leave any other way. Every
  element gets a diagram shape from a layered layout, so modelers display the result. The
  `camunda7` and `camunda8` engines add external task topics or job types named after the
  capability, so a worker for each capability can be written once and the process deploys as it
  is. A `flowglyph:capability` attribute keeps the link back to the catalog.
- **UiPath XAML.** A straight line of steps is a Sequence; anything else a Flowchart of FlowSteps
  and FlowDecisions. Calls to UiPath workflows become Invoke Workflow File with every argument of
  the called workflow listed, typed from its .NET type, ready to bind. Calls to other capabilities
  become Comments naming them: which activity reaches an SAP service or an API is a team's
  choice FlowGlyph cannot make.
- **Nothing is guessed.** Conditions are copied as written and the compilers say so; parallel
  branches a Flowchart cannot follow, and joins it cannot wait for, are reported.

## Alternatives considered

- **Generating code for a workflow engine** (Temporal, Airflow). Teams that run BPMN or UiPath
  would still have to translate; the formats they already review are a better first target.
- **Translating expressions between languages.** VB, FEEL, JUEL and n8n expressions differ in
  more than syntax; a wrong translation is worse than an honest copy with a warning.

## Consequences

- Compiled BPMN reads back through the BPMN adapter into the same steps, edges, conditions,
  joins and calls; the tests check it.
- Compiled XAML reads back through the UiPath adapter with the same calls. Neither output has
  been opened in Camunda Modeler or UiPath Studio by the tests; the structure follows what those
  tools write.
- Workflows that need parallel execution compile to BPMN faithfully but to a Flowchart only in
  part, with a warning.
