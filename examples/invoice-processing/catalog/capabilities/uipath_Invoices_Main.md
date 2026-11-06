---
id: "uipath/Invoices/Main"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: true
---

# Main

Validate an invoice and book it, asking for approval above the threshold.

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through Orchestrator at `Main.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_InvoicePath` | string | yes | Path of the invoice PDF. |
| `in_Threshold` | number | no |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_InvoiceId` | string |  |

## Steps

1. **Validate vendor** (invoke) -> [ValidateVendor](uipath_Invoices_Steps_ValidateVendor.md)
2. **If amount > in_Threshold** (decision)
3. **Request approval** (invoke) -> [RequestApproval](uipath_Invoices_Steps_RequestApproval.md)
4. **Book invoice** (invoke, runs if any predecessor ran) -> [BookInvoice](uipath_Invoices_Steps_BookInvoice.md)
5. **Archive** (invoke)

Branches:

- `If_1` -> `Invoke_2` when `amount > in_Threshold`

Unresolved invocations:

- `Steps/Missing.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_InvoicePath": {
        "type": "string",
        "x-clr-type": "InArgument(x:String)",
        "description": "Path of the invoice PDF.",
        "x-direction": "in"
      },
      "in_Threshold": {
        "type": "number",
        "x-clr-type": "InArgument(x:Decimal)",
        "x-default-expression": "10000",
        "x-direction": "in"
      }
    },
    "required": [
      "in_InvoicePath"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_InvoiceId": {
        "type": "string",
        "x-clr-type": "OutArgument(x:String)"
      }
    }
  }
}
```
