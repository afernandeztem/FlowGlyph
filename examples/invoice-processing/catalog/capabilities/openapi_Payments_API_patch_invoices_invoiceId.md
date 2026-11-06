---
id: "openapi/Payments_API/patch_invoices_invoiceId"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "rWdX"
idempotency: "none"
invocable: true
---

# patch_invoices_invoiceId

Update some fields of an invoice

- **Source:** `payments.yaml#/paths/~1invoices~1{invoiceId}/patch` (openapi)
- **Effects:** reads: unknown, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through HTTP at `PATCH /invoices/{invoiceId}`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `invoiceId` | string | yes | Identifier of the invoice. |
| `body` | object | no |  |

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
      },
      "body": {
        "type": "object",
        "x-in": "body"
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
