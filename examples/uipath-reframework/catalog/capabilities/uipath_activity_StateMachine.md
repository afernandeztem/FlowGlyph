---
id: "uipath/activity/StateMachine"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# StateMachine

[Process title]
[Process description]
[Additional information (e.g., author, contact information and applications involved and required external setup)]

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `InitialState` | any | yes |  |
| `Variables` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "InitialState": {
        "x-seen": "1/1",
        "x-clr-types": [
          "s:Exception"
        ]
      },
      "Variables": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ui:QueueItem"
        ]
      }
    },
    "required": [
      "InitialState",
      "Variables"
    ],
    "x-xaml-template": {
      "xml": "<StateMachine DisplayName=\"General Business Process\">\n  <StateMachine.InitialState>\n    <!-- activities -->\n  </StateMachine.InitialState>\n  <StateMachine.Variables>\n    <Variable x:TypeArguments=\"ui:QueueItem\" Name=\"TransactionItem\" />\n    <Variable x:TypeArguments=\"s:Exception\" Name=\"SystemError\" />\n    <Variable x:TypeArguments=\"ui:BusinessRuleException\" Name=\"BusinessRuleException\" />\n    <Variable x:TypeArguments=\"x:Int32\" Default=\"1\" Name=\"TransactionNumber\" />\n    <Variable x:TypeArguments=\"scg:Dictionary(x:String, x:Object)\" Name=\"Config\" />\n    <Variable x:TypeArguments=\"x:Int32\" Default=\"0\" Name=\"RetryNumber\" />\n    <Variable x:TypeArguments=\"x:String\" Name=\"TransactionField2\" />\n    <Variable x:TypeArguments=\"x:String\" Name=\"TransactionField1\" />\n    <Variable x:TypeArguments=\"x:String\" Name=\"TransactionID\" />\n    <Variable x:TypeArguments=\"sd:DataTable\" Name=\"TransactionData\" />\n  </StateMachine.Variables>\n  <sads:DebugSymbol.Symbol>[symbol]</sads:DebugSymbol.Symbol>\n</StateMachine>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "s": "clr-namespace:System;assembly=mscorlib",
        "sads": "http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger",
        "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
        "sd": "clr-namespace:System.Data;assembly=System.Data",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
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
