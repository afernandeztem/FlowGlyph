---
id: "uipath/Invoices/Steps/BookInvoice"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: true
---

# BookInvoice

Book invoice

- **Source:** `Steps/BookInvoice.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through Invoke Workflow File at `Steps/BookInvoice.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Invoice` | object or null | yes |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_InvoiceId` | string or null |  |

## Steps

1. **Queue booking** (activity) -> [AddQueueItem](uipath_activity_AddQueueItem.md)

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_Invoice": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "x-direction": "in"
      }
    },
    "required": [
      "in_Invoice"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_InvoiceId": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)"
      }
    }
  }
}
```
