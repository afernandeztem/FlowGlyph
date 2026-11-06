# Catalog

17 invocable capabilities, 0 activity types.

## Invocable

| Capability | Description | Inputs | Effects | Idempotency | Version |
|---|---|---|---|---|---|
| [Nightly Stock Report](capabilities/sap-cpi_Nightly_Stock_Report.md) | Integration flow Nightly Stock Report, started by timer. | none | RX | natural | 1.0.0 |
| [Notify Customer](capabilities/sap-cpi_Notify_Customer.md) | Integration flow Notify Customer, started by ProcessDirect /notify. | `body` | rWX | key | 1.1.0 |
| [Orders Inbound](capabilities/sap-cpi_Orders_Inbound.md) | Integration flow Orders Inbound, started by HTTPS /orders. | `body` | RWX | key | 1.0.0 |
| [GetDuplicateCandidates](capabilities/sap_ZSUPPLIER_INVOICE_SRV_GetDuplicateCandidates.md) | Find possible duplicates | `InvoicingParty`, `InvoiceGrossAmount` | RX | natural | 1.0.0 |
| [Release](capabilities/sap_ZSUPPLIER_INVOICE_SRV_Release.md) | Release blocked invoice | `SupplierInvoice`, `FiscalYear` | rwdX | natural | 1.1.0 |
| [Supplier/query](capabilities/sap_ZSUPPLIER_INVOICE_SRV_Supplier_query.md) | List Supplier records | `$filter`, `$select`, `$orderby`, `$top`, `$skip` | RX | natural | 1.0.0 |
| [Supplier/read](capabilities/sap_ZSUPPLIER_INVOICE_SRV_Supplier_read.md) | Read one Supplier by its key | `Supplier` | RX | natural | 1.0.0 |
| [SupplierInvoice/create](capabilities/sap_ZSUPPLIER_INVOICE_SRV_SupplierInvoice_create.md) | Post a supplier invoice. The service rejects a second invoice with the same SupplierInvoiceIDByInvc… | `body` | WX | key | 1.1.0 |
| [SupplierInvoice/query](capabilities/sap_ZSUPPLIER_INVOICE_SRV_SupplierInvoice_query.md) | List Supplier invoice records | `$filter`, `$select`, `$orderby`, `$top`, `$skip` | RX | natural | 1.0.0 |
| [SupplierInvoice/read](capabilities/sap_ZSUPPLIER_INVOICE_SRV_SupplierInvoice_read.md) | Read one Supplier invoice by its key | `SupplierInvoice`, `FiscalYear` | RX | natural | 1.0.0 |
| [SupplierInvoice/update](capabilities/sap_ZSUPPLIER_INVOICE_SRV_SupplierInvoice_update.md) | Change fields of a Supplier invoice | `SupplierInvoice`, `FiscalYear`, `body` | WdX | natural | 1.0.0 |
| [BusinessPartner/block](capabilities/sap_zbusinesspartner_BusinessPartner_block.md) | block | `BusinessPartner`, `Reason` | rwdX | none | 1.0.0 |
| [BusinessPartner/create](capabilities/sap_zbusinesspartner_BusinessPartner_create.md) | Create a BusinessPartner | `body` | WX | none | 1.0.0 |
| [BusinessPartner/query](capabilities/sap_zbusinesspartner_BusinessPartner_query.md) | List BusinessPartner records | `$filter`, `$select`, `$orderby`, `$top`, `$skip` | RX | natural | 1.0.0 |
| [BusinessPartner/read](capabilities/sap_zbusinesspartner_BusinessPartner_read.md) | Read one BusinessPartner by its key | `BusinessPartner` | RX | natural | 1.0.0 |
| [BusinessPartner/update](capabilities/sap_zbusinesspartner_BusinessPartner_update.md) | Change fields of a BusinessPartner | `BusinessPartner`, `body` | WdX | natural | 1.0.0 |
| [checkDuplicates](capabilities/sap_zbusinesspartner_checkDuplicates.md) | checkDuplicates | `FullName` | RX | natural | 1.0.0 |
Effects codes: R reads, W mutates state, D destructive, X external. Upper case means yes, lower case means unknown.
