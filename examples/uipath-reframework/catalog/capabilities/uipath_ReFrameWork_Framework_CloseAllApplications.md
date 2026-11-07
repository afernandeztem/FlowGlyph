---
id: "uipath/ReFrameWork/Framework/CloseAllApplications"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# CloseAllApplications

Do necessary procedures for ending the process (e.g., logout) and close the applications used in the process.

- **Source:** `Framework/CloseAllApplications.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Framework/CloseAllApplications.xaml`

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
