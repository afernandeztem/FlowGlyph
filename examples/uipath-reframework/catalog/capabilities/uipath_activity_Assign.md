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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
