---
id: "uipath/activity/AddLogFields"
kind: "activity"
category: "logging"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# AddLogFields

Add the process name to the logs generated after this point. 
This log field can be used to create reports and visualizations about the process.

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Fields` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`
- `Main.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Fields": {
        "x-seen": "4/4",
        "x-clr-types": [
          "x:String"
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
