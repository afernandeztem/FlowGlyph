---
id: "sap/zbusinesspartner/BusinessPartner/block"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "rwdX"
idempotency: "none"
invocable: true
---

# BusinessPartner/block

block

- **Source:** `odata/zbusinesspartner_v4.xml#BusinessPartner/block` (sap)
- **Effects:** reads: unknown, mutates state: unknown, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.6)
- **Started by:** a call through OData V4 at `POST BusinessPartner(key)/zbusinesspartner.block()`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `BusinessPartner` | string | yes |  |
| `Reason` | string | yes |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `value` | object |  |

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "BusinessPartner": {
        "type": "string",
        "x-edm-type": "Edm.String",
        "maxLength": 10,
        "x-odata-key": true
      },
      "Reason": {
        "type": "string",
        "x-edm-type": "Edm.String"
      }
    },
    "required": [
      "BusinessPartner",
      "Reason"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "value": {
        "type": "object",
        "properties": {
          "BusinessPartner": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "maxLength": 10
          },
          "FullName": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "maxLength": 81
          },
          "Country": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "maxLength": 3
          },
          "CreatedOn": {
            "type": "string",
            "format": "date",
            "x-edm-type": "Edm.Date"
          },
          "Revenue": {
            "type": "number",
            "x-edm-type": "Edm.Decimal"
          }
        }
      }
    }
  }
}
```
