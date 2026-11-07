---
id: "uipath/activity/Transition"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Transition

Business Rule Exception

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Action` | any | no |  |
| `Condition` | any | yes |  |
| `To` | any | yes |  |

## Used in

- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Action": {
        "x-seen": "4/7"
      },
      "Condition": {
        "x-seen": "7/7",
        "examples": [
          "[SystemError IsNot Nothing]",
          "[BusinessRuleException IsNot Nothing]",
          "[SystemError Is Nothing And BusinessRuleException is Nothing]"
        ]
      },
      "To": {
        "x-seen": "7/7",
        "x-clr-types": [
          "ui:BusinessRuleException",
          "x:Boolean",
          "x:String, Argument"
        ],
        "examples": [
          "{x:Reference __ReferenceID0}",
          "{x:Reference __ReferenceID1}",
          "{x:Reference __ReferenceID2}"
        ]
      }
    },
    "required": [
      "Condition",
      "To"
    ],
    "x-xaml-template": {
      "xml": "<Transition DisplayName=\"Successful initialization\">\n  <Transition.To>\n    <!-- activities -->\n  </Transition.To>\n  <Transition.Action>\n    <!-- activities -->\n  </Transition.Action>\n  <Transition.Condition>[condition]</Transition.Condition>\n</Transition>",
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
