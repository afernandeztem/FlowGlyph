---
id: "uipath/activity/State"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# State

Read configuration file and initialize applications used in the process.

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Entry` | any | yes |  |
| `IsFinal` | any | no |  |
| `Transitions` | any | no |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Entry": {
        "x-seen": "4/4",
        "x-clr-types": [
          "s:Exception",
          "ui:BusinessRuleException",
          "x:Boolean",
          "x:String, Argument"
        ]
      },
      "IsFinal": {
        "x-seen": "1/4",
        "examples": [
          "True"
        ]
      },
      "Transitions": {
        "x-seen": "3/4",
        "x-clr-types": [
          "ui:BusinessRuleException",
          "x:Boolean"
        ]
      }
    },
    "required": [
      "Entry"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
