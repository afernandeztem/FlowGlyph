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

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Level` | any | yes |  |
| `Message` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Level": {
        "x-seen": "1/1",
        "examples": [
          "Info"
        ]
      },
      "Message": {
        "x-seen": "1/1",
        "examples": [
          "[\"Start\"]"
        ]
      }
    },
    "required": [
      "Level",
      "Message"
    ],
    "x-xaml-template": {
      "xml": "<ui:LogMessage Level=\"Info\" Message=\"[message]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities"
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
