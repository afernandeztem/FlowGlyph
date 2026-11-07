---
id: "uipath/activity/InvokeWorkflowFile"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# InvokeWorkflowFile

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `WorkflowFileName` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "WorkflowFileName": {
        "x-seen": "4/4",
        "examples": [
          "Steps\\ValidateVendor.xaml",
          "Steps\\RequestApproval.xaml",
          "Steps\\BookInvoice.xaml"
        ]
      }
    },
    "required": [
      "WorkflowFileName"
    ],
    "x-xaml-template": {
      "xml": "<ui:InvokeWorkflowFile DisplayName=\"Validate vendor\" WorkflowFileName=\"[workflowFileName]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities"
      },
      "from": "Main.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
