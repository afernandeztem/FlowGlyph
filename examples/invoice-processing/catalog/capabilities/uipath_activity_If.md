---
id: "uipath/activity/If"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# If

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Condition` | any | yes |  |
| `Then` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Condition": {
        "x-seen": "1/1",
        "examples": [
          "[amount > in_Threshold]"
        ]
      },
      "Then": {
        "x-seen": "1/1"
      }
    },
    "required": [
      "Condition",
      "Then"
    ],
    "x-xaml-template": {
      "xml": "<If Condition=\"[condition]\" DisplayName=\"Above threshold?\">\n  <If.Then>\n    <!-- activities -->\n  </If.Then>\n</If>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities"
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
