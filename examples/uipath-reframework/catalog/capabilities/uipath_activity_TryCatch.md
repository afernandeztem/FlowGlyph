---
id: "uipath/activity/TryCatch"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# TryCatch

Securely fetch or create and use a set of credentials.

First, there is an attempt to fetch credentials from Orchestrator using the name received as argument. 
If it is not possible to retrieve those credentials from Orchestrator, there is an attempt to fetch them from the Windows Credential Manager (WCM). 
If the credentials are not defined in the WCM, the user is prompted to create the credentials that will be added to the WCM and returned for use during the process execution.

The Private property is used to prevent the generation of logs that might contain information about the credentials.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Catches` | any | yes |  |
| `Finally` | any | no |  |
| `Try` | any | yes |  |
| `Variables` | any | no |  |

## Used in

- `Framework/GetAppCredentials.xaml`
- `Framework/InitAllSettings.xaml`
- `Framework/SetTransactionStatus.xaml`
- `Main.xaml`
- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Catches": {
        "x-seen": "12/12",
        "x-clr-types": [
          "s:Exception",
          "ui:BusinessRuleException"
        ]
      },
      "Finally": {
        "x-seen": "2/12",
        "x-clr-types": [
          "scg:Dictionary(x:String, x:Object)",
          "x:Object"
        ]
      },
      "Try": {
        "x-seen": "12/12",
        "x-clr-types": [
          "s:Exception",
          "scg:Dictionary(x:String, x:Object)",
          "sd:DataTable",
          "ui:BusinessRuleException",
          "ui:GenericValue",
          "x:Int32",
          "x:String",
          "x:String, Argument"
        ]
      },
      "Variables": {
        "x-seen": "1/12",
        "x-clr-types": [
          "x:String"
        ]
      }
    },
    "required": [
      "Catches",
      "Try"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
