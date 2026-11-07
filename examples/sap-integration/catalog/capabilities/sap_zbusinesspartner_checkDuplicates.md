---
id: "sap/zbusinesspartner/checkDuplicates"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# checkDuplicates

checkDuplicates

- **Source:** `odata/zbusinesspartner_v4.xml#checkDuplicates` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through OData V4 at `GET checkDuplicates()`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `FullName` | string | yes |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `value` | array |  |

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "FullName": {
        "type": "string",
        "x-edm-type": "Edm.String"
      }
    },
    "required": [
      "FullName"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "value": {
        "type": "array",
        "items": {
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
}
```
