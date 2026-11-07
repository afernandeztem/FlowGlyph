---
id: "uipath/activity/AddLogFields"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# AddLogFields

Add the process name to the logs generated after this point. 
This log field can be used to create reports and visualizations about the process.

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Fields` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`
- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Fields": {
        "x-seen": "4/4",
        "x-clr-types": [
          "x:String"
        ]
      }
    },
    "required": [
      "Fields"
    ],
    "x-xaml-template": {
      "xml": "<ui:AddLogFields DisplayName=\"Add transaction log fields (Successful)\">\n  <ui:AddLogFields.Fields>\n    <InArgument x:TypeArguments=\"x:String\" x:Key=\"logF_TransactionStatus\">[fields]</InArgument>\n    <InArgument x:TypeArguments=\"x:String\" x:Key=\"logF_TransactionNumber\">[fields]</InArgument>\n    <InArgument x:TypeArguments=\"x:String\" x:Key=\"logF_TransactionID\">[fields]</InArgument>\n    <InArgument x:TypeArguments=\"x:String\" x:Key=\"logF_TransactionField1\">[fields]</InArgument>\n    <InArgument x:TypeArguments=\"x:String\" x:Key=\"logF_TransactionField2\">[fields]</InArgument>\n  </ui:AddLogFields.Fields>\n</ui:AddLogFields>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/SetTransactionStatus.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
