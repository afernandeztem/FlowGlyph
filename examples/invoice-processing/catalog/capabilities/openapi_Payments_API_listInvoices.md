---
id: "openapi/Payments_API/listInvoices"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# listInvoices

List invoices

- **Source:** `payments.yaml#/paths/~1invoices/get` (openapi)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through HTTP at `GET /invoices`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `limit` | integer | no | Maximum number of invoices to return. |
| `status` | string | no |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `body` | array |  |

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "limit": {
        "type": "integer",
        "maximum": 100,
        "x-in": "query",
        "description": "Maximum number of invoices to return."
      },
      "status": {
        "type": "string",
        "enum": [
          "draft",
          "booked",
          "paid"
        ],
        "x-in": "query"
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "body": {
        "type": "array",
        "items": {
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
}
```
