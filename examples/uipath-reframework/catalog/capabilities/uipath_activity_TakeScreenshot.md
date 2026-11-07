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
    ],
    "x-xaml-template": {
      "xml": "<ui:TakeScreenshot WaitBefore=\"{x:Null}\" DisplayName=\"Take screenshot\" Screenshot=\"[screenshot]\">\n  <ui:TakeScreenshot.Target>\n    <ui:Target ClippingRegion=\"{x:Null}\" Element=\"{x:Null}\" Selector=\"{x:Null}\" TimeoutMS=\"{x:Null}\" WaitForReady=\"INTERACTIVE\" />\n  </ui:TakeScreenshot.Target>\n</ui:TakeScreenshot>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/TakeScreenshot.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
