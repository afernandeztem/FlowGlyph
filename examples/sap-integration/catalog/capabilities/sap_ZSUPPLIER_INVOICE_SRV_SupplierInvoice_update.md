---
id: "sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/update"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.0.0"
effects: "WdX"
idempotency: "natural"
invocable: true
---

# SupplierInvoice/update

Change fields of a Supplier invoice

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#SupplierInvoice/update` (sap)
- **Effects:** reads: no, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.6)
- **Started by:** a call through OData V2 at `PATCH SupplierInvoice(key)`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `SupplierInvoice` | string | yes | Invoice document |
| `FiscalYear` | string | yes | Fiscal year |
| `body` | object | yes |  |

## Outputs

None.

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
      },
      "body": {
        "type": "object",
        "properties": {
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
    },
    "required": [
      "SupplierInvoice",
      "FiscalYear",
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
