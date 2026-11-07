---
id: "uipath/activity/RemoveLogFields"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# RemoveLogFields

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Fields` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Fields": {
        "x-seen": "3/3",
        "x-clr-types": [
          "InArgument(x:String)"
        ]
      }
    },
    "required": [
      "Fields"
    ],
    "x-xaml-template": {
      "xml": "<ui:RemoveLogFields DisplayName=\"Remove transaction log fields (Successful)\">\n  <ui:RemoveLogFields.Fields>\n    <scg:List x:TypeArguments=\"InArgument(x:String)\" Capacity=\"8\">\n      <InArgument x:TypeArguments=\"x:String\">[fields]</InArgument>\n      <InArgument x:TypeArguments=\"x:String\">[fields]</InArgument>\n      <InArgument x:TypeArguments=\"x:String\">[fields]</InArgument>\n      <InArgument x:TypeArguments=\"x:String\">[fields]</InArgument>\n      <InArgument x:TypeArguments=\"x:String\">[fields]</InArgument>\n    </scg:List>\n  </ui:RemoveLogFields.Fields>\n</ui:RemoveLogFields>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
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
