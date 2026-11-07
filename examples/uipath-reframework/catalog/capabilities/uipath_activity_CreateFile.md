---
id: "uipath/activity/CreateFile"
kind: "activity"
category: "filesystem"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# CreateFile

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ContinueOnError` | any | yes |  |
| `Name` | any | yes |  |
| `Path` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ContinueOnError": {
        "x-seen": "1/1",
        "examples": [
          "True"
        ]
      },
      "Name": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Path": {
        "x-seen": "1/1",
        "examples": [
          "[in_TestLogFile]"
        ]
      }
    },
    "required": [
      "ContinueOnError",
      "Name",
      "Path"
    ],
    "x-xaml-template": {
      "xml": "<ui:CreateFile Name=\"{x:Null}\" ContinueOnError=\"True\" DisplayName=\"Create Log file\" Path=\"[path]\" />",
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
