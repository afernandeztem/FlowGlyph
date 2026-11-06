---
id: "uipath/Invoices/Steps/RequestApproval"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: true
---

# RequestApproval

Request approval

- **Source:** `Steps/RequestApproval.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through Invoke Workflow File at `Steps/RequestApproval.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Approver` | string | yes |  |

## Outputs

None.

## Steps

1. **Mail approver** (activity) -> [SendMail](uipath_activity_SendMail.md)

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_Approver": {
        "type": "string",
        "x-clr-type": "InArgument(x:String)",
        "x-direction": "in"
      }
    },
    "required": [
      "in_Approver"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
