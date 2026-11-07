---
id: "sap/ZSUPPLIER_INVOICE_SRV/GetDuplicateCandidates"
kind: "operation"
category: "ZSUPPLIER_INVOICE_SRV"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# GetDuplicateCandidates

Find possible duplicates

- **Source:** `odata/ZSUPPLIER_INVOICE_SRV.edmx#GetDuplicateCandidates` (sap)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through OData V2 at `GET GetDuplicateCandidates()`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `InvoicingParty` | string | no |  |
| `InvoiceGrossAmount` | number | no |  |

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
      "InvoicingParty": {
        "type": "string",
        "x-edm-type": "Edm.String"
      },
      "InvoiceGrossAmount": {
        "type": "number",
        "x-edm-type": "Edm.Decimal"
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
}
```
