---
id: "sap-cpi/Notify_Customer"
kind: "workflow"
category: "Notify_Customer"
version: "1.1.0"
effects: "rWX"
idempotency: "key"
invocable: true
---

# Notify Customer

Integration flow Notify Customer, started by ProcessDirect /notify.

- **Source:** `integration/notify/src/main/resources/scenarioflows/integrationflow/Notify_Customer.iflw` (sap-cpi)
- **Effects:** reads: unknown, mutates state: yes, destructive: no, external: yes
- **Idempotency:** key, safe to retry when deduplicated on body (declared, confidence 1.0)
- **Started by:** a call through ProcessDirect at `/notify`
- **Configuration:** `SMTP_HOST`

> **Notes**
> - a Data Store write without overwrite rejects repeated ${header.OrderNumber}; retries are safe only if it runs before any external call
> - warning: the main process has no exception subprocess: a failure ends unhandled

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `body` | any | no | Payload for the ProcessDirect endpoint /notify |

## Outputs

| Name | Type | Description |
|---|---|---|
| `body` | any | response payload |

## Steps

1. **Remember notification** (activity)

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "body": {
        "description": "Payload for the ProcessDirect endpoint /notify",
        "x-endpoint": "/notify",
        "x-adapter": "ProcessDirect"
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
