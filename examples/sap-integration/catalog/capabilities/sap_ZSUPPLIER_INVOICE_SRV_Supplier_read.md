---
id: "sap/ZSUPPLIER_INVOICE_SRV/Supplier/read"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# Supplier/read

Read one Supplier by its key

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#Supplier/read` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.9)
- **Started by:** a call through OData V2 at `GET Supplier(key)`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Supplier` | string | yes | Supplier |

## Outputs

| Name | Type | Description |
|---|---|---|
| `Supplier` | string | Supplier |
| `SupplierName` | string | Name |
| `SupplierID` | string | Technical ID |

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Supplier": {
        "type": "string",
        "x-edm-type": "Edm.String",
        "description": "Supplier",
        "maxLength": 10,
        "x-odata-key": true
      }
    },
    "required": [
      "Supplier"
    ],
    "additionalProperties": false
  },
  "output": {
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
```
