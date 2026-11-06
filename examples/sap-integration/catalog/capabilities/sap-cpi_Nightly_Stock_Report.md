---
id: "sap-cpi/Nightly_Stock_Report"
kind: "workflow"
category: "Nightly_Stock_Report"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# Nightly Stock Report

Integration flow Nightly Stock Report, started by timer.

- **Source:** `integration/nightly-report/src/main/resources/scenarioflows/integrationflow/Nightly_Stock_Report.iflw` (sap-cpi)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a schedule through Timer
- **Configuration:** `STOCK_URL`

## Inputs

None.

## Outputs

| Name | Type | Description |
|---|---|---|
| `body` | any | response payload |

## Steps

1. **Read stock (HTTP GET {{STOCK_URL}})** (activity)

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {},
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
