---
id: "uipath/activity/ShouldStop"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# ShouldStop

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Result` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Result": {
        "x-seen": "1/1",
        "examples": [
          "[ShouldStop]"
        ]
      }
    },
    "required": [
      "Result"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
