---
id: "uipath/activity/SaveImage"
kind: "activity"
category: "filesystem"
version: "1.0.0"
effects: "WdX"
idempotency: "none"
invocable: false
---

# SaveImage

- **Source:** `Framework/TakeScreenshot.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `FileName` | any | yes |  |
| `Image` | any | yes |  |

## Used in

- `Framework/TakeScreenshot.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "FileName": {
        "x-seen": "1/1",
        "examples": [
          "[io_FilePath]"
        ]
      },
      "Image": {
        "x-seen": "1/1",
        "examples": [
          "[Screenshot]"
        ]
      }
    },
    "required": [
      "FileName",
      "Image"
    ],
    "x-xaml-template": {
      "xml": "<ui:SaveImage DisplayName=\"Save screenshot\" FileName=\"[fileName]\" Image=\"[image]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities"
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
