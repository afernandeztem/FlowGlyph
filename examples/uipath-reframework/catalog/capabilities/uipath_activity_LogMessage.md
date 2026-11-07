---
id: "uipath/activity/LogMessage"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# LogMessage

- **Source:** `Framework/CloseAllApplications.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Level` | any | yes |  |
| `Message` | any | yes |  |

## Used in

- `Framework/CloseAllApplications.xaml`
- `Framework/InitAllApplications.xaml`
- `Framework/InitAllSettings.xaml`
- `Framework/KillAllProcesses.xaml`
- `Framework/SetTransactionStatus.xaml`
- `Framework/TakeScreenshot.xaml`
- `Main.xaml`
- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Level": {
        "x-seen": "22/22",
        "examples": [
          "Trace",
          "Warn",
          "Info"
        ]
      },
      "Message": {
        "x-seen": "22/22",
        "examples": [
          "Closing applications...",
          "Opening applications...",
          "[\"Loading asset \" + Row(\"Asset\").ToString + \" failed: \" + Exception.Message]"
        ]
      }
    },
    "required": [
      "Level",
      "Message"
    ],
    "x-xaml-template": {
      "xml": "<ui:LogMessage DisplayName=\"Log message (close applications)\" Level=\"Trace\" Message=\"[message]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities"
      },
      "from": "Framework/CloseAllApplications.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
