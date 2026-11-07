---
id: "uipath/activity/AddCredential"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "W"
idempotency: "none"
invocable: false
---

# AddCredential

Add provided credentials to the Windows Credential Manager to avoid requesting them in later executions of the process.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: no
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `CredentialType` | any | yes |  |
| `Password` | any | yes |  |
| `PersistanceType` | any | yes |  |
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
          "[StringPassword]"
        ]
      },
      "PersistanceType": {
        "x-seen": "1/1",
        "examples": [
          "Enterprise"
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
      "Target",
      "Username"
    ],
    "x-xaml-template": {
      "xml": "<ui:AddCredential CredentialType=\"Generic\" DisplayName=\"Add Credential\" Password=\"[password]\" PersistanceType=\"Enterprise\" Target=\"[target]\" Username=\"[username]\" />",
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
