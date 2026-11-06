# ADR-0007: SAP Cloud Integration iFlows, one capability per endpoint

- Status: accepted
- Date: 2026-11-06 (recorded after the adapter shipped)

## Context

SAP Cloud Integration (part of SAP Integration Suite) runs integration flows: BPMN 2.0 documents
(`.iflw`) packaged with a manifest and externalized parameters, exported as `.zip` artifacts or
kept unpacked in git. An iFlow is started by a sender channel or a timer, calls systems through
receiver channels, and can call other iFlows through ProcessDirect.

An existing community repository, sap-cpi-skills-pack, documents CPI practices for LLMs as prose.
It has no license, so nothing from it is reused; FlowGlyph's goal is different in any case: to
read the iFlows themselves.

## Decision

- **Capabilities.** Every sender endpoint of an iFlow becomes a workflow capability. An iFlow
  with no sender becomes one capability, started on a schedule when it has a timer start event.
  Only endpoints whose adapter can be called directly (HTTPS, SOAP, OData, ProcessDirect, IDoc,
  AS2, AS4...) are invocable.
- **Effects** combine those of the receivers (by adapter type and, for OData and HTTP, by
  operation or method) and of steps that change state (Data Store writes, scripts, which are
  unknown). Exception subprocesses and local processes count: they call systems too.
- **Idempotency is declared before it is inferred.** An idempotent process call, an
  exactly-once sender, or a Data Store write that refuses duplicates is what the iFlow itself
  promises; the adapter records it as `declared` with a note saying where it comes from. Only
  without one does it infer from effects.
- **ProcessDirect links** between iFlows read together become `calls` in the workflow graph, and
  effects propagate along them until nothing changes, so an iFlow that only forwards to another
  inherits its effects.
- **Design findings**, such as a main process with no exception subprocess, a router with no
  default route, a receiver without a timeout, plain HTTP or a hard-coded address, are reported as
  diagnostics and notes, so the report and `wiki lint` can point at them.
- **Configuration values are never read.** `parameters.prop` often holds hosts, users and keys;
  the adapter records only parameter names, in `configuration`.

## Alternatives considered

- **The Cloud Integration OData API.** It lists deployed artifacts and their runtime state, but
  needs a tenant and credentials, and what is deployed is not what is reviewed in git.
- **One capability per iFlow.** Simpler, but an iFlow with an HTTPS and a ProcessDirect sender is
  two different contracts to its callers.

## Consequences

- Detection of an idempotent process call matches its activity type and properties loosely
  (`idempot`), because it has not been checked against every export format. A false positive is
  visible: the note says why the answer is declared.
- Message mappings, value mappings and scripts are not analysed beyond their effects.
- An address no iFlow in the source listens on stays an unresolved call: read related packages
  together to resolve it.
