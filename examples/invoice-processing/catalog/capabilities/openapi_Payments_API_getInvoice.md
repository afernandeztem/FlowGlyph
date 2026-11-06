---
id: "openapi/Payments_API/getInvoice"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# getInvoice

- **Source:** `payments.yaml#/paths/~1invoices~1{invoiceId}/get` (openapi)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through HTTP at `GET /invoices/{invoiceId}`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `invoiceId` | string | yes | Identifier of the invoice. |

## Outputs

| Name | Type | Description |
|---|---|---|
| `body` | any |  |

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
    "properties": {
      "body": {
        "allOf": [
          {
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
            }
          },
          {
            "type": "object",
            "properties": {
              "id": {
                "type": "string"
              },
              "status": {
                "type": "string"
              },
              "replaces": {
                "type": "object",
                "x-recursive-ref": "#/components/schemas/Invoice"
              }
            }
          }
        ]
      }
    }
  }
}
```
