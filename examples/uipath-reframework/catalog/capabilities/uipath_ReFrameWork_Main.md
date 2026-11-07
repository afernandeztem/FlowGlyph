---
id: "uipath/ReFrameWork/Main"
kind: "workflow"
category: "workflow"
version: "1.1.0"
effects: "RWdX"
idempotency: "natural"
invocable: true
---

# Main

Process supplier invoices from the AP_Invoices queue: take each item, book it in the ERP and set its status in Orchestrator.

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** natural, safe to retry (declared, confidence 1.0)
- **Started by:** a call through Orchestrator at `Main.xaml`
- **Approval:** required before every run

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_OrchestratorQueueName` | string or null | yes | Allows the Orchestrator queue name to be passed as an argument, instead of only being defined in the configuration file. |

## Outputs

None.

## Steps

1. **General Business Process** (opaque)
   [Process title]
2. **If Config is Nothing** (decision)
   An uninitialized Config dictionary indicates that this is the first run of the process.
3. **Invoke InitAllSettings workflow** (invoke) -> [InitiAllSettings](uipath_ReFrameWork_Framework_InitAllSettings.md)
4. **If Not string.IsNullOrEmpty(in_OrchestratorQueueName)** (decision)
   Overwrite queue name from in configuration file in case the argument OrchestratorQueueName is specified.
5. **Invoke KillAllProcesses workflow (first run)** (invoke) -> [KillAllProcesses](uipath_ReFrameWork_Framework_KillAllProcesses.md)
   Kills all Windows processes representing applications used in this business process to assure that the execution starts in a clean state.
6. **Invoke InitiAllApplications workflow** (invoke, runs if any predecessor ran) -> [Initialize Applications](uipath_ReFrameWork_Framework_InitAllApplications.md)
7. **If ShouldStop** (decision)
8. **Invoke GetTransactionData workflow** (invoke) -> [GetTransactionData](uipath_ReFrameWork_Framework_GetTransactionData.md)
9. **Invoke Process workflow** (invoke, runs if any predecessor ran) -> [Process](uipath_ReFrameWork_Process.md)
10. **Invoke SetTransactionStatus workflow** (invoke) -> [SetTransactionStatus](uipath_ReFrameWork_Framework_SetTransactionStatus.md)
11. **Invoke CloseAllApplications workflow** (invoke) -> [CloseAllApplications](uipath_ReFrameWork_Framework_CloseAllApplications.md)
12. **Invoke KillAllProcesses workflow (End process)** (invoke) -> [KillAllProcesses](uipath_ReFrameWork_Framework_KillAllProcesses.md)

Branches:

- `If_1` -> `InvokeWorkflowFile_12` when `Config is Nothing`
- `If_11` -> `InvokeWorkflowFile_20` when `not (ShouldStop)`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_OrchestratorQueueName": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Allows the Orchestrator queue name to be passed as an argument, instead of only being defined in the configuration file.",
        "x-direction": "in"
      }
    },
    "required": [
      "in_OrchestratorQueueName"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
