---
id: "uipath/activity/RemoveLogFields"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# RemoveLogFields

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Fields` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Fields": {
        "x-seen": "3/3",
        "x-clr-types": [
          "InArgument(x:String)"
        ]
      }
    },
    "required": [
      "Fields"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
