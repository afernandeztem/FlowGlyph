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

Take a screenshot of the current state of the screen to facilitate debugging.

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
    ],
    "x-xaml-template": {
      "xml": "<TryCatch DisplayName=\"Private: Get Application Credentials\">\n  <TryCatch.Variables>\n    <Variable x:TypeArguments=\"x:String\" Name=\"StringPassword\" />\n  </TryCatch.Variables>\n  <TryCatch.Try>\n    <!-- activities -->\n  </TryCatch.Try>\n  <TryCatch.Catches>\n    <Catch x:TypeArguments=\"s:Exception\">\n      <ActivityAction x:TypeArguments=\"s:Exception\">\n        <ActivityAction.Argument>\n          <DelegateInArgument x:TypeArguments=\"s:Exception\" Name=\"Exception\" />\n        </ActivityAction.Argument>\n        <!-- activities -->\n      </ActivityAction>\n    </Catch>\n  </TryCatch.Catches>\n  <sads:DebugSymbol.Symbol>[symbol]</sads:DebugSymbol.Symbol>\n</TryCatch>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "s": "clr-namespace:System;assembly=mscorlib",
        "sads": "http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/GetAppCredentials.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
