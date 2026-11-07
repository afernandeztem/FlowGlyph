---
id: "uipath/activity/StateMachine"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# StateMachine

[Process title]
[Process description]
[Additional information (e.g., author, contact information and applications involved and required external setup)]

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `InitialState` | any | yes |  |
| `Variables` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "InitialState": {
        "x-seen": "1/1",
        "x-clr-types": [
          "s:Exception"
        ]
      },
      "Variables": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ui:QueueItem"
        ]
      }
    },
    "required": [
      "InitialState",
      "Variables"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
