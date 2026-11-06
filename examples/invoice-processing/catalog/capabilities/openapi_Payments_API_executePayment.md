---
id: "openapi/Payments_API/executePayment"
kind: "operation"
category: "payments"
version: "1.0.0"
effects: "rWX"
idempotency: "none"
invocable: true
---

# executePayment

Pay an invoice

- **Source:** `payments.yaml#/paths/~1payments/post` (openapi)
- **Effects:** reads: unknown, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through HTTP at `POST /payments`
- **Deprecated** in its source

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `X-Tenant` | string | yes |  |
| `body` | object | yes |  |

## Outputs

None.

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "X-Tenant": {
        "type": "string",
        "x-in": "header"
      },
      "body": {
        "type": "object",
        "required": [
          "invoiceId",
          "amount"
        ],
        "properties": {
          "invoiceId": {
            "type": "string"
          },
          "amount": {
            "type": "number"
          }
        },
        "x-in": "body"
      }
    },
    "required": [
      "X-Tenant",
      "body"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
