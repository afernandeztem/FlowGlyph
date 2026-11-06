---
id: "openapi/Payments_API/deleteInvoice"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "WDX"
idempotency: "natural"
invocable: true
---

# deleteInvoice

- **Source:** `payments.yaml#/paths/~1invoices~1{invoiceId}/delete` (openapi)
- **Effects:** reads: no, mutates state: yes, destructive: yes, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through HTTP at `DELETE /invoices/{invoiceId}`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `invoiceId` | string | yes | Identifier of the invoice. |

## Outputs

None.

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "invoiceId": {
        "type": "string",
        "x-in": "path",
        "description": "Identifier of the invoice."
      }
    },
    "required": [
      "invoiceId"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
