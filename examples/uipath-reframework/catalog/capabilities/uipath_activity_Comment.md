---
id: "uipath/activity/Comment"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Comment

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Text` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Text": {
        "x-seen": "1/1",
        "examples": [
          "Default transition is picked up if there are no errors during initialization"
        ]
      }
    },
    "required": [
      "Text"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
