---
id: "uipath/activity/AddQueueItem"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# AddQueueItem

- **Source:** `Steps/BookInvoice.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `QueueType` | any | yes |  |

## Used in

- `Steps/BookInvoice.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "QueueType": {
        "x-seen": "1/1",
        "examples": [
          "Invoices"
        ]
      }
    },
    "required": [
      "QueueType"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
