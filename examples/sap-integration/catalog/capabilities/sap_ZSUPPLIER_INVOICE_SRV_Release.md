---
id: "sap/ZSUPPLIER_INVOICE_SRV/Release"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.1.0"
effects: "rwdX"
idempotency: "natural"
invocable: true
---

# Release

Release blocked invoice

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#Release` (sap)
- **Effects:** reads: unknown, mutates state: unknown, destructive: unknown, external: yes
- **Idempotency:** natural, safe to retry (declared, confidence 1.0)
- **Started by:** a call through OData V2 at `POST Release()`
- **Approval:** required before every run

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `SupplierInvoice` | string | no |  |
| `FiscalYear` | string | no |  |

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
      "SupplierInvoice": {
        "type": "string",
        "x-edm-type": "Edm.String"
      },
      "FiscalYear": {
        "type": "string",
        "x-edm-type": "Edm.String"
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "value": {
        "type": "object",
        "properties": {
          "SupplierInvoice": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Invoice document",
            "maxLength": 10
          },
          "FiscalYear": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Fiscal year",
            "maxLength": 4
          },
          "CompanyCode": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Company code",
            "maxLength": 4
          },
          "InvoicingParty": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Supplier",
            "maxLength": 10
          },
          "SupplierInvoiceIDByInvcgParty": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Supplier's invoice reference",
            "maxLength": 16
          },
          "InvoiceGrossAmount": {
            "type": "number",
            "x-edm-type": "Edm.Decimal",
            "description": "Gross amount"
          },
          "DocumentCurrency": {
            "type": "string",
            "x-edm-type": "Edm.String",
            "description": "Currency",
            "maxLength": 5
          },
          "PostingDate": {
            "type": "string",
            "format": "date-time",
            "x-edm-type": "Edm.DateTime",
            "description": "Posting date"
          },
          "IsBlocked": {
            "type": "boolean",
            "x-edm-type": "Edm.Boolean",
            "description": "Blocked for payment"
          }
        }
      }
    }
  }
}
```
