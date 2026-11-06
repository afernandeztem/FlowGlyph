---
id: "uipath/Invoices/Steps/ValidateVendor"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# ValidateVendor

Validate vendor

- **Source:** `Steps/ValidateVendor.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Steps/ValidateVendor.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_VendorId` | string | yes |  |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_Exists` | boolean |  |

## Steps


## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_VendorId": {
        "type": "string",
        "x-clr-type": "InArgument(x:String)",
        "x-direction": "in"
      }
    },
    "required": [
      "in_VendorId"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_Exists": {
        "type": "boolean",
        "x-clr-type": "OutArgument(x:Boolean)"
      }
    }
  }
}
```
