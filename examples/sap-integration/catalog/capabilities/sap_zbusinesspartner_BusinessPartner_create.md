---
id: "sap/zbusinesspartner/BusinessPartner/create"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: true
---

# BusinessPartner/create

Create a BusinessPartner

- **Source:** `odata/zbusinesspartner_v4.xml#BusinessPartner/create` (sap)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through OData V4 at `POST BusinessPartner`

> **Notes**
> - OData defines no idempotency key for creation; services usually reject duplicates on an external reference field instead

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `body` | object | yes |  |

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
      "body": {
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
        },
        "required": [
          "BusinessPartner"
        ]
      }
    },
    "required": [
      "body"
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
