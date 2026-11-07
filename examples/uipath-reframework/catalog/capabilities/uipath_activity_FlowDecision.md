---
id: "uipath/activity/FlowDecision"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# FlowDecision

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Condition` | any | yes |  |
| `False` | any | yes |  |
| `True` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Condition": {
        "x-seen": "5/5",
        "examples": [
          "[in_BusinessRuleException is Nothing and in_SystemError is Nothing]",
          "[in_BusinessRuleException isnot Nothing]",
          "[cint(in_Config(\"MaxRetryNumber\"))>0]"
        ]
      },
      "False": {
        "x-seen": "5/5",
        "x-clr-types": [
          "x:Boolean",
          "x:Int32",
          "x:String, InArgument"
        ]
      },
      "True": {
        "x-seen": "5/5",
        "x-clr-types": [
          "x:Int32",
          "x:String, InArgument"
        ]
      }
    },
    "required": [
      "Condition",
      "False",
      "True"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
