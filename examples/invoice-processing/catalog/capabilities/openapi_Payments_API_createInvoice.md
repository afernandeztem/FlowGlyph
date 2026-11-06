---
id: "openapi/Payments_API/createInvoice"
kind: "operation"
category: "invoices"
version: "1.0.0"
effects: "rWX"
idempotency: "key"
invocable: true
---

# createInvoice

Create a supplier invoice

Books the invoice in the ledger. Send the same Idempotency-Key to retry safely.

- **Source:** `payments.yaml#/paths/~1invoices/post` (openapi)
- **Effects:** reads: unknown, mutates state: yes, destructive: no, external: yes
- **Idempotency:** key, safe to retry when deduplicated on Idempotency-Key (inferred, confidence 0.9)
- **Started by:** a call through HTTP at `POST /invoices`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Idempotency-Key` | string | yes | Unique key per logical request. |
| `body` | object | yes |  |

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
      "Idempotency-Key": {
        "type": "string",
        "x-in": "header",
        "description": "Unique key per logical request."
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
      "Idempotency-Key",
      "body"
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
