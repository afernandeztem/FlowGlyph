---
id: "uipath/activity/Assign"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Assign

- **Source:** `Steps/ValidateVendor.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `To` | any | yes |  |
| `Value` | any | yes |  |

## Used in

- `Steps/ValidateVendor.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "To": {
        "x-seen": "1/1",
        "x-clr-types": [
          "x:Boolean"
        ]
      },
      "Value": {
        "x-seen": "1/1",
        "x-clr-types": [
          "x:Boolean"
        ]
      }
    },
    "required": [
      "To",
      "Value"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
