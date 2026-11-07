---
id: "uipath/activity/ForEach"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# ForEach

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Body` | any | yes |  |
| `Values` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`
- `Framework/InitAllSettings.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Body": {
        "x-seen": "2/2",
        "x-clr-types": [
          "x:Char",
          "x:String"
        ]
      },
      "Values": {
        "x-seen": "2/2",
        "examples": [
          "[StringPassword.ToCharArray]",
          "[in_ConfigSheets]"
        ]
      }
    },
    "required": [
      "Body",
      "Values"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
