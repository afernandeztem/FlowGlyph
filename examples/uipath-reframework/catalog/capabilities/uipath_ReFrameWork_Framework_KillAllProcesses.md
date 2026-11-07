---
id: "uipath/ReFrameWork/Framework/KillAllProcesses"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# KillAllProcesses

Use the Kill Process activity to force the termination of the Windows processes representing applications used in the business process.
Note that killing processes might have undesired outcomes, like losing unsaved changes to files.

- **Source:** `Framework/KillAllProcesses.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Framework/KillAllProcesses.xaml`

## Inputs

None.

## Outputs

None.

## Steps


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
