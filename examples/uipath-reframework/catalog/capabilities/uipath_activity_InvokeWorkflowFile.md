---
id: "uipath/activity/InvokeWorkflowFile"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# InvokeWorkflowFile

Kills all Windows processes representing applications used in this business process to assure that the execution starts in a clean state.
Since the applications are assumed to be already closed, CloseAllApplications is skipped and just KillAllProcess is invoked.

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Arguments` | any | yes |  |
| `ContinueOnError` | any | yes |  |
| `UnSafe` | any | yes |  |
| `WorkflowFileName` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`
- `Main.xaml`
- `Tests/RunAllTests.xaml`
- `Tests/TestWorkflowTemplate.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Arguments": {
        "x-seen": "16/16",
        "x-clr-types": [
          "scg:Dictionary(x:String, x:Object)",
          "ui:QueueItem",
          "x:Int32",
          "x:String",
          "x:String, Argument"
        ]
      },
      "ContinueOnError": {
        "x-seen": "16/16",
        "examples": [
          "{x:Null}"
        ]
      },
      "UnSafe": {
        "x-seen": "16/16",
        "examples": [
          "False"
        ]
      },
      "WorkflowFileName": {
        "x-seen": "16/16",
        "examples": [
          "Framework\\TakeScreenshot.xaml",
          "Framework\\CloseAllApplications.xaml",
          "Framework\\KillAllProcesses.xaml"
        ]
      }
    },
    "required": [
      "Arguments",
      "ContinueOnError",
      "UnSafe",
      "WorkflowFileName"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
