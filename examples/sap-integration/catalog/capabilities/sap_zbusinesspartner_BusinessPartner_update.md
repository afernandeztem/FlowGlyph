---
id: "sap/zbusinesspartner/BusinessPartner/update"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "WdX"
idempotency: "natural"
invocable: true
---

# BusinessPartner/update

Change fields of a BusinessPartner

- **Source:** `odata/zbusinesspartner_v4.xml#BusinessPartner/update` (sap)
- **Effects:** reads: no, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.6)
- **Started by:** a call through OData V4 at `PATCH BusinessPartner(key)`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `BusinessPartner` | string | yes |  |
| `body` | object | yes |  |

## Outputs

None.

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
      "body": {
        "type": "object",
        "properties": {
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
    },
    "required": [
      "BusinessPartner",
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
