---
id: "sap/zbusinesspartner/BusinessPartner/query"
kind: "operation"
category: "zbusinesspartner"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# BusinessPartner/query

List BusinessPartner records

- **Source:** `odata/zbusinesspartner_v4.xml#BusinessPartner/query` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.9)
- **Started by:** a call through OData V4 at `GET BusinessPartner`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `$filter` | string | no | OData filter expression. |
| `$select` | string | no | Comma-separated properties to return. |
| `$orderby` | string | no |  |
| `$top` | integer | no |  |
| `$skip` | integer | no |  |

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
      "$filter": {
        "type": "string",
        "description": "OData filter expression."
      },
      "$select": {
        "type": "string",
        "description": "Comma-separated properties to return."
      },
      "$orderby": {
        "type": "string"
      },
      "$top": {
        "type": "integer",
        "minimum": 0
      },
      "$skip": {
        "type": "integer",
        "minimum": 0
      }
    },
    "required": [],
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
