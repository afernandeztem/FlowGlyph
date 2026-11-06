---
id: "uipath/activity/SendMail"
kind: "activity"
category: "integration.mail"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# SendMail

- **Source:** `Steps/RequestApproval.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Subject` | any | yes |  |
| `To` | any | yes |  |

## Used in

- `Steps/RequestApproval.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Subject": {
        "x-seen": "1/1",
        "examples": [
          "Approve invoice"
        ]
      },
      "To": {
        "x-seen": "1/1",
        "examples": [
          "[in_Approver]"
        ]
      }
    },
    "required": [
      "Subject",
      "To"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
