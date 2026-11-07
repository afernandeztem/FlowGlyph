# ADR-0012: BPMN, n8n and SAP Build Process Automation adapters

- Status: accepted
- Date: 2026-11-07

## Context

Automations do not all live in UiPath and SAP Integration Suite. Process engines run BPMN models
(Camunda 7 and 8 are the most common), low-code teams build in n8n, and SAP customers model
approvals in SAP Build Process Automation. Each describes processes as a graph of steps, but in
its own format and with its own idea of what a step does.

## Decision

Three adapters, each reading the format as its tool exports it, with the same rules as the others:
offline, deterministic, and unknown when the format does not say.

- **BPMN** (`bpmn`) reads `.bpmn` files with Camunda 7 (`camunda:`) and Camunda 8 (`zeebe:`)
  extensions. Every process is a capability. Its start event decides how it is started: none is a
  call, a message start an event, a timer a schedule that no caller can start.
- **n8n** (`n8n`) reads workflow exports, one object or a list. The trigger node decides how a
  workflow is started; webhooks are callable, sub-workflows are only called by other workflows.
- **SAP Build Process Automation** (`sbpa`) reads `.mtar` exports, an archive with a
  `content.zip` per project, or a project already unpacked. Processes, automations and decisions
  are capabilities; processes invoke the other two in their graph.

Shared rules:

- **Starting a process creates an instance.** For BPMN and SAP Build Process Automation the
  capability always writes state and is never naturally idempotent, whatever its steps do.
  n8n executions are not business state, so n8n workflows take only their nodes' effects.
- **Steps decide the effects**, from the step type (BPMN), the node type with its method or
  operation (n8n), or the task class (SAP). Code, scripts and service tasks without a known
  implementation are unknown.
- **Calls cross files.** Call activities, `Execute Workflow` nodes and automation tasks become
  `calls` in the workflow graph, and effects propagate along them.
- **Configuration is named, never read.** n8n credentials are recorded by type and name, which
  is all an export holds.

## Alternatives considered

- **One generic graph adapter with per-tool plugins.** The tools differ more in how they are
  started and what a step means than in how their graphs look; a shared core would have been a
  set of special cases.
- **Reading a live engine or n8n instance through its API.** Needs credentials, and what is
  deployed is not what is reviewed in git.

## Consequences

- The SAP Build Process Automation format is not documented by SAP. The adapter is written
  against real exports from SAP's own samples, and reads what it does not recognise as unknown
  steps instead of failing.
- BPMN inputs are only typed when a Camunda 7 start form declares them; otherwise a process
  accepts any variables.
- Executors for these engines are not part of this decision: running a BPMN process or an n8n
  webhook needs its own connection type.
