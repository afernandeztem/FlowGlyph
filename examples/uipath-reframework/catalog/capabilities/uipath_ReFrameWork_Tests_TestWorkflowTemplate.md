---
id: "uipath/ReFrameWork/Tests/TestWorkflowTemplate"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# TestWorkflowTemplate

Template workflow used to create tests for workflows in the process.
Create a new test workflow by copying and renaming this file.

- **Source:** `Tests/TestWorkflowTemplate.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Tests/TestWorkflowTemplate.xaml`

## Inputs

None.

## Outputs

None.

## Steps

1. **Initialize All Settings** (invoke) -> [InitiAllSettings](uipath_ReFrameWork_Framework_InitAllSettings.md)

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
