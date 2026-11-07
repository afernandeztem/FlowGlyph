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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
