---
id: "uipath/activity/GetSecureCredential"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "R"
idempotency: "natural"
invocable: false
---

# GetSecureCredential

Attempt to retrieve credentials from the Windows Credential Manager.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `CredentialType` | any | yes |  |
| `Password` | any | yes |  |
| `PersistanceType` | any | yes |  |
| `Result` | any | yes |  |
| `Target` | any | yes |  |
| `Username` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "CredentialType": {
        "x-seen": "1/1",
        "examples": [
          "Generic"
        ]
      },
      "Password": {
        "x-seen": "1/1",
        "examples": [
          "[out_Password]"
        ]
      },
      "PersistanceType": {
        "x-seen": "1/1",
        "examples": [
          "Enterprise"
        ]
      },
      "Result": {
        "x-seen": "1/1",
        "examples": [
          "[CredentialsFound]"
        ]
      },
      "Target": {
        "x-seen": "1/1",
        "examples": [
          "[in_Credential]"
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
      "CredentialType",
      "Password",
      "PersistanceType",
      "Result",
      "Target",
      "Username"
    ],
    "x-xaml-template": {
      "xml": "<ui:GetSecureCredential CredentialType=\"Generic\" DisplayName=\"Get secure credential\" Password=\"[password]\" PersistanceType=\"Enterprise\" Result=\"[result]\" Target=\"[target]\" Username=\"[username]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities"
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
