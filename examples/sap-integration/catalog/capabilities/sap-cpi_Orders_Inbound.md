---
id: "sap-cpi/Orders_Inbound"
kind: "workflow"
category: "Orders_Inbound"
version: "1.0.0"
effects: "RWX"
idempotency: "key"
invocable: true
---

# Orders Inbound

Integration flow Orders Inbound, started by HTTPS /orders.

- **Source:** `integration/orders/src/main/resources/scenarioflows/integrationflow/Orders_Inbound.iflw` (sap-cpi)
- **Effects:** reads: yes, mutates state: yes, destructive: no, external: yes
- **Idempotency:** key, safe to retry when deduplicated on ${header.OrderNumber} (declared, confidence 0.9)
- **Started by:** a call through HTTPS at `/orders`
- **Configuration:** `ERP_Credential`, `ERP_URL`

> **Notes**
> - declared by the iFlow: an idempotent process call deduplicates on ${header.OrderNumber}
> - warning: HTTP receiver uses plain HTTP: http://legacy.example.com/stock
> - info: HTTP receiver address is hard-coded; externalize http://legacy.example.com/stock
> - warning: HTTP receiver http://legacy.example.com/stock has no request timeout
> - info: CSRF protection is off on endpoint /orders
> - warning: 'Keep original order' copies the whole body into a property, doubling memory
> - warning: router 'Order type' has no default route

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `body` | any | no | Payload for the HTTPS endpoint /orders |

## Outputs

| Name | Type | Description |
|---|---|---|
| `body` | any | response payload |

## Steps

1. **Process each order once: local process Integration Process** (container)
2. **Order type** (decision)
3. **Book in ERP (HTTP POST {{ERP_URL}}/orders)** (activity, runs if any predecessor ran)
4. **Check stock (HTTP GET http://legacy.example.com/stock)** (activity)

Branches:

- `ExclusiveGateway_Type` -> `ServiceTask_Book` when `${header.OrderType} = 'STD'`
- `ExclusiveGateway_Type` -> `ServiceTask_Stock` when `${header.OrderType} = 'BACK'`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "body": {
        "description": "Payload for the HTTPS endpoint /orders",
        "x-endpoint": "/orders",
        "x-adapter": "HTTPS"
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "body": {
        "description": "response payload"
      }
    }
  }
}
```
