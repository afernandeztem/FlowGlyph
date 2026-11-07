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
    ],
    "x-xaml-template": {
      "xml": "<ui:GetRobotAsset TimeoutMS=\"{x:Null}\" AssetName=\"[assetName]\" DisplayName=\"Get Asset\">\n  <ui:GetRobotAsset.Value>\n    <OutArgument x:TypeArguments=\"ui:GenericValue\">[value]</OutArgument>\n  </ui:GetRobotAsset.Value>\n</ui:GetRobotAsset>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/InitAllSettings.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
