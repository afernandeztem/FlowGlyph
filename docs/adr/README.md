# Decision records

Each record explains one decision: the context, what was decided, what else was considered and
what follows from it. Records are not edited once accepted; a later record supersedes them.

| # | Decision | Status |
|---|---|---|
| [0001](0001-automation-ir.md) | A vendor-neutral Automation IR is the product | accepted |
| [0002](0002-python.md) | Python | accepted |
| [0003](0003-apache-2.0.md) | Apache License 2.0 | accepted |
| [0004](0004-skipped-steps.md) | Skipped steps and joins | accepted |
| [0005](0005-typed-capability-facts-and-views.md) | Typed capability facts, and presentation outside the IR | accepted |
| [0006](0006-sap-odata-adapter.md) | SAP OData services are read from their metadata | accepted |
| [0007](0007-sap-cloud-integration-adapter.md) | SAP Cloud Integration iFlows, one capability per endpoint | accepted |
| [0008](0008-sources-folders-files-and-git.md) | Sources are folders, files or git repositories | accepted |
| [0009](0009-llm-wiki.md) | The catalog as an LLM wiki | accepted |
| [0010](0010-provider-neutral-planner.md) | Planner backends are pluggable and provider-neutral | accepted |
| [0011](0011-executors-and-connections.md) | Executors run through declared connections | accepted |
| [0012](0012-process-engine-adapters.md) | BPMN, n8n and SAP Build Process Automation adapters | accepted |
| [0013](0013-compilers.md) | Compiling workflow IR back into BPMN and UiPath XAML | accepted |
| [0014](0014-llm-enrichment.md) | Enrichment by a language model, cached by source hash | accepted |
| [0015](0015-context-for-coding-agents.md) | Context files for coding agents, written from the sources | accepted |

To propose a new decision, copy the shape of the most recent record, number it next, and open a
pull request with status `proposed`.
