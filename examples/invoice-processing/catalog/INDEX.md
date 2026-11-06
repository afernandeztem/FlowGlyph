# Catalog

11 invocable capabilities, 7 activity types.

## Invocable

| Capability | Description | Inputs | Effects | Idempotency | Version |
|---|---|---|---|---|---|
| [createInvoice](capabilities/openapi_Payments_API_createInvoice.md) | Create a supplier invoice | `Idempotency-Key`, `body` | rWX | key | 1.0.0 |
| [deleteInvoice](capabilities/openapi_Payments_API_deleteInvoice.md) |  | `invoiceId` | WDX | natural | 1.0.0 |
| [executePayment](capabilities/openapi_Payments_API_executePayment.md) | Pay an invoice | `X-Tenant`, `body` | rWX | none | 1.0.0 |
| [getInvoice](capabilities/openapi_Payments_API_getInvoice.md) |  | `invoiceId` | RX | natural | 1.0.0 |
| [listInvoices](capabilities/openapi_Payments_API_listInvoices.md) | List invoices | `limit`, `status` | RX | natural | 1.0.0 |
| [patch_invoices_invoiceId](capabilities/openapi_Payments_API_patch_invoices_invoiceId.md) | Update some fields of an invoice | `invoiceId`, `body` | rWdX | none | 1.0.0 |
| [replaceInvoice](capabilities/openapi_Payments_API_replaceInvoice.md) |  | `invoiceId`, `body` | rWdX | natural | 1.0.0 |
| [Main](capabilities/uipath_Invoices_Main.md) | Validate an invoice and book it, asking for approval above the threshold. | `in_InvoicePath`, `in_Threshold` | WX | none | 1.0.0 |
| [BookInvoice](capabilities/uipath_Invoices_Steps_BookInvoice.md) | Book invoice | `in_Invoice` | WX | none | 1.0.0 |
| [RequestApproval](capabilities/uipath_Invoices_Steps_RequestApproval.md) | Request approval | `in_Approver` | WX | none | 1.0.0 |
| [ValidateVendor](capabilities/uipath_Invoices_Steps_ValidateVendor.md) | Validate vendor | `in_VendorId` | none | natural | 1.0.0 |

## Activity types

### control

- [Assign](capabilities/uipath_activity_Assign.md)
- [If](capabilities/uipath_activity_If.md)
- [InvokeWorkflowFile](capabilities/uipath_activity_InvokeWorkflowFile.md)
- [Sequence](capabilities/uipath_activity_Sequence.md)

### integration.mail

- [SendMail](capabilities/uipath_activity_SendMail.md) (side effects)

### logging

- [LogMessage](capabilities/uipath_activity_LogMessage.md)

### orchestrator

- [AddQueueItem](capabilities/uipath_activity_AddQueueItem.md) (side effects)

Effects codes: R reads, W mutates state, D destructive, X external. Upper case means yes, lower case means unknown.
