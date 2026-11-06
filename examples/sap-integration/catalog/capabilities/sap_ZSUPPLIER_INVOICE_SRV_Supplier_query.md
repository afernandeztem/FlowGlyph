---
id: "sap/ZSUPPLIER_INVOICE_SRV/Supplier/query"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# Supplier/query

List Supplier records

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#Supplier/query` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.9)
- **Started by:** a call through OData V2 at `GET Supplier`

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
            "Supplier": {
              "type": "string",
              "x-edm-type": "Edm.String",
              "description": "Supplier",
              "maxLength": 10
            },
            "SupplierName": {
              "type": "string",
              "x-edm-type": "Edm.String",
              "description": "Name",
              "maxLength": 80
            },
            "SupplierID": {
              "type": "string",
              "format": "uuid",
              "x-edm-type": "Edm.Guid",
              "description": "Technical ID"
            }
          }
        }
      }
    }
  }
}
```
