---
id: "uipath/activity/OpenApplication"
kind: "activity"
category: "system"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# OpenApplication

Open log file in a Notepad window.

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ApplicationWindow` | any | yes |  |
| `Arguments` | any | yes |  |
| `Body` | any | yes |  |
| `ContinueOnError` | any | yes |  |
| `FileName` | any | yes |  |
| `Selector` | any | yes |  |
| `TimeoutMS` | any | yes |  |
| `WorkingDirectory` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ApplicationWindow": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Arguments": {
        "x-seen": "1/1",
        "examples": [
          "[in_TestLogFile]"
        ]
      },
      "Body": {
        "x-seen": "1/1",
        "x-clr-types": [
          "x:Object"
        ]
      },
      "ContinueOnError": {
        "x-seen": "1/1",
        "examples": [
          "True"
        ]
      },
      "FileName": {
        "x-seen": "1/1",
        "examples": [
          "C:\\windows\\system32\\notepad.exe"
        ]
      },
      "Selector": {
        "x-seen": "1/1",
        "examples": [
          "<wnd app='notepad.exe' cls='Notepad' title='TestLog.txt - Notepad' />"
        ]
      },
      "TimeoutMS": {
        "x-seen": "1/1",
        "examples": [
          "5000"
        ]
      },
      "WorkingDirectory": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      }
    },
    "required": [
      "ApplicationWindow",
      "Arguments",
      "Body",
      "ContinueOnError",
      "FileName",
      "Selector",
      "TimeoutMS",
      "WorkingDirectory"
    ],
    "x-xaml-template": {
      "xml": "<ui:OpenApplication ApplicationWindow=\"{x:Null}\" WorkingDirectory=\"{x:Null}\" Arguments=\"[arguments]\" ContinueOnError=\"True\" DisplayName=\"Open application (Notepad)\" FileName=\"[fileName]\" Selector=\"[selector]\" TimeoutMS=\"5000\">\n  <ui:OpenApplication.Body>\n    <ActivityAction x:TypeArguments=\"x:Object\">\n      <ActivityAction.Argument>\n        <DelegateInArgument x:TypeArguments=\"x:Object\" Name=\"ContextTarget\" />\n      </ActivityAction.Argument>\n    </ActivityAction>\n  </ui:OpenApplication.Body>\n</ui:OpenApplication>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Tests/RunAllTests.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
