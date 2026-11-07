---
id: "sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/read"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# SupplierInvoice/read

Read one Supplier invoice by its key

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#SupplierInvoice/read` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.9)
- **Started by:** a call through OData V2 at `GET SupplierInvoice(key)`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `SupplierInvoice` | string | yes | Invoice document |
| `FiscalYear` | string | yes | Fiscal year |

## Outputs

| Name | Type | Description |
|---|---|---|
| `SupplierInvoice` | string | Invoice document |
| `FiscalYear` | string | Fiscal year |
| `CompanyCode` | string | Company code |
| `InvoicingParty` | string | Supplier |
| `SupplierInvoiceIDByInvcgParty` | string | Supplier's invoice reference |
| `InvoiceGrossAmount` | number | Gross amount |
| `DocumentCurrency` | string | Currency |
| `PostingDate` | string | Posting date |
| `IsBlocked` | boolean | Blocked for payment |

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "SupplierInvoice": {
        "type": "string",
        "x-edm-type": "Edm.String",
        "description": "Invoice document",
        "maxLength": 10,
        "x-odata-key": true
      },
      "FiscalYear": {
        "type": "string",
        "x-edm-type": "Edm.String",
        "description": "Fiscal year",
        "maxLength": 4,
        "x-odata-key": true
      }
    },
    "required": [
      "SupplierInvoice",
      "FiscalYear"
    ],
    "additionalProperties": false
  },
  "output": {
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
```
