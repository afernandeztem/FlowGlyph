---
id: "uipath/activity/InvokeMethod"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# InvokeMethod

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `MethodName` | any | yes |  |
| `TargetObject` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "MethodName": {
        "x-seen": "1/1",
        "examples": [
          "AppendChar"
        ]
      },
      "TargetObject": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ss:SecureString"
        ]
      }
    },
    "required": [
      "MethodName",
      "TargetObject"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
