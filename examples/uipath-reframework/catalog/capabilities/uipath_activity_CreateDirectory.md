---
id: "uipath/activity/CreateDirectory"
kind: "activity"
category: "filesystem"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# CreateDirectory

- **Source:** `Framework/TakeScreenshot.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ContinueOnError` | any | yes |  |
| `Path` | any | yes |  |

## Used in

- `Framework/TakeScreenshot.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ContinueOnError": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Path": {
        "x-seen": "1/1",
        "examples": [
          "[ScreenshotFileInfo.DirectoryName]"
        ]
      }
    },
    "required": [
      "ContinueOnError",
      "Path"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
