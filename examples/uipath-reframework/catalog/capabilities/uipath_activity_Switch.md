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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
