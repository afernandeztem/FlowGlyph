---
id: "openapi/Payments_API/replaceInvoice"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "rWdX"
idempotency: "natural"
invocable: true
---

# replaceInvoice

- **Source:** `payments.yaml#/paths/~1invoices~1{invoiceId}/put` (openapi)
- **Effects:** reads: unknown, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through HTTP at `PUT /invoices/{invoiceId}`

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
        "required": [
          "vendor",
          "amount",
          "currency",
          "reference"
        ],
        "properties": {
          "vendor": {
            "type": "string"
          },
          "amount": {
            "type": "number"
          },
          "currency": {
            "type": "string",
            "minLength": 3,
            "maxLength": 3
          },
          "reference": {
            "type": "string"
          },
          "customer": {
            "$ref": "customers.yaml#/components/schemas/Customer"
          }
        },
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
