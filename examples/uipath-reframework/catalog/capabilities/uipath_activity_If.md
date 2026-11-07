---
id: "uipath/activity/If"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# If

The Private property is used to prevent the generation of logs that might contain information about the credentials.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Condition` | any | yes |  |
| `Else` | any | no |  |
| `Then` | any | yes |  |

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
      "Condition": {
        "x-seen": "16/16",
        "examples": [
          "[out_Username Is Nothing Or out_Password Is Nothing]",
          "[Not CredentialsFound]",
          "[out_TransactionItem isNot Nothing]"
        ]
      },
      "Else": {
        "x-seen": "4/16",
        "x-clr-types": [
          "x:Boolean",
          "x:Int32"
        ]
      },
      "Then": {
        "x-seen": "16/16",
        "x-clr-types": [
          "ss:SecureString",
          "ui:QueueItem",
          "x:Boolean",
          "x:Int32",
          "x:Object",
          "x:String",
          "x:String, InArgument"
        ]
      }
    },
    "required": [
      "Condition",
      "Then"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
