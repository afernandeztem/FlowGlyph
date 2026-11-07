---
id: "uipath/activity/Assign"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Assign

Increment the TransactionNumber to get the next transaction to be processed.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `To` | any | yes |  |
| `Value` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`
- `Framework/GetTransactionData.xaml`
- `Framework/InitAllSettings.xaml`
- `Framework/SetTransactionStatus.xaml`
- `Framework/TakeScreenshot.xaml`
- `Main.xaml`
- `Tests/RunAllTests.xaml`
- `Tests/RunAllTests_Logging.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "To": {
        "x-seen": "37/37",
        "x-clr-types": [
          "s:Exception",
          "scg:Dictionary(x:String, x:Object)",
          "si:FileInfo",
          "ss:SecureString",
          "ui:BusinessRuleException",
          "ui:QueueItem",
          "x:Boolean",
          "x:Int32",
          "x:Object",
          "x:String"
        ]
      },
      "Value": {
        "x-seen": "37/37",
        "x-clr-types": [
          "s:Exception",
          "scg:Dictionary(x:String, x:Object)",
          "si:FileInfo",
          "ss:SecureString",
          "ui:BusinessRuleException",
          "ui:QueueItem",
          "x:Boolean",
          "x:Int32",
          "x:Object",
          "x:String"
        ]
      }
    },
    "required": [
      "To",
      "Value"
    ],
    "x-xaml-template": {
      "xml": "<Assign x:Key=\"BRE\" DisplayName=\"Assign out_Comment (BRE)\">\n  <Assign.To>\n    <OutArgument x:TypeArguments=\"x:String\">[to]</OutArgument>\n  </Assign.To>\n  <Assign.Value>\n    <InArgument x:TypeArguments=\"x:String\">[value]</InArgument>\n  </Assign.Value>\n</Assign>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Tests/RunAllTests_Logging.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
