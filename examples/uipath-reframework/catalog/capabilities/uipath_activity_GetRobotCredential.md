---
id: "uipath/activity/GetRobotCredential"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# GetRobotCredential

Attempt to retrieve credentials from Orchestrator.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AssetName` | any | yes |  |
| `Password` | any | yes |  |
| `TimeoutMS` | any | yes |  |
| `Username` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "AssetName": {
        "x-seen": "1/1",
        "examples": [
          "[in_Credential]"
        ]
      },
      "Password": {
        "x-seen": "1/1",
        "examples": [
          "[out_Password]"
        ]
      },
      "TimeoutMS": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Username": {
        "x-seen": "1/1",
        "examples": [
          "[out_Username]"
        ]
      }
    },
    "required": [
      "AssetName",
      "Password",
      "TimeoutMS",
      "Username"
    ],
    "x-xaml-template": {
      "xml": "<ui:GetRobotCredential TimeoutMS=\"{x:Null}\" AssetName=\"[assetName]\" DisplayName=\"Get credentials\" Password=\"[password]\" Username=\"[username]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/GetAppCredentials.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
