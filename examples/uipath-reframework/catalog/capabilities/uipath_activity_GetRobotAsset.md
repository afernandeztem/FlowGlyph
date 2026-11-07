---
id: "uipath/activity/GetRobotAsset"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# GetRobotAsset

- **Source:** `Framework/InitAllSettings.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AssetName` | any | yes |  |
| `TimeoutMS` | any | yes |  |
| `Value` | any | yes |  |

## Used in

- `Framework/InitAllSettings.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "AssetName": {
        "x-seen": "1/1",
        "examples": [
          "[row(\"Asset\").ToString]"
        ]
      },
      "TimeoutMS": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Value": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ui:GenericValue"
        ]
      }
    },
    "required": [
      "AssetName",
      "TimeoutMS",
      "Value"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
