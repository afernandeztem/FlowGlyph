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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
