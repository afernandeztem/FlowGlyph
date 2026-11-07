---
id: "uipath/activity/TakeScreenshot"
kind: "activity"
category: "ui"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# TakeScreenshot

The whole screen is captured.

- **Source:** `Framework/TakeScreenshot.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Screenshot` | any | yes |  |
| `Target` | any | yes |  |
| `WaitBefore` | any | yes |  |

## Used in

- `Framework/TakeScreenshot.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Screenshot": {
        "x-seen": "1/1",
        "examples": [
          "[Screenshot]"
        ]
      },
      "Target": {
        "x-seen": "1/1"
      },
      "WaitBefore": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      }
    },
    "required": [
      "Screenshot",
      "Target",
      "WaitBefore"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
