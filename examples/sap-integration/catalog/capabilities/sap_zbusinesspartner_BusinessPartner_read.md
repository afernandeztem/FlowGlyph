---
id: "sap/zbusinesspartner/BusinessPartner/read"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# BusinessPartner/read

Read one BusinessPartner by its key

- **Source:** `odata/zbusinesspartner_v4.xml#BusinessPartner/read` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.9)
- **Started by:** a call through OData V4 at `GET BusinessPartner(key)`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `BusinessPartner` | string | yes |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `BusinessPartner` | string |  |
| `FullName` | string |  |
| `Country` | string |  |
| `CreatedOn` | string |  |
| `Revenue` | number |  |

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
      }
    },
    "required": [
      "BusinessPartner"
    ],
    "additionalProperties": false
  },
  "output": {
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
```
