---
id: "uipath/activity/Switch"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Switch

- **Source:** `Tests/RunAllTests_Logging.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Expression` | any | yes |  |

## Used in

- `Tests/RunAllTests_Logging.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Expression": {
        "x-seen": "1/1",
        "examples": [
          "[in_ExpectedOutcome]"
        ]
      }
    },
    "required": [
      "Expression"
    ],
    "x-xaml-template": {
      "xml": "<Switch x:TypeArguments=\"x:String\" DisplayName=\"Switch to choose test comment\" Expression=\"[expression]\">\n  <!-- activities -->\n</Switch>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Tests/RunAllTests_Logging.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
