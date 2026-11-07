---
id: "uipath/activity/RequestCredential"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# RequestCredential

Request credentials from user.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Message` | any | yes |  |
| `Password` | any | yes |  |
| `Result` | any | yes |  |
| `Title` | any | yes |  |
| `Username` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Message": {
        "x-seen": "1/1",
        "examples": [
          "[\"Please provide \"\"\" + in_Credential + \"\"\" access credentials\"]"
        ]
      },
      "Password": {
        "x-seen": "1/1",
        "examples": [
          "[StringPassword]"
        ]
      },
      "Result": {
        "x-seen": "1/1",
        "examples": [
          "[CredentialsFound]"
        ]
      },
      "Title": {
        "x-seen": "1/1",
        "examples": [
          "Hello! This is Robot"
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
      "Message",
      "Password",
      "Result",
      "Title",
      "Username"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
