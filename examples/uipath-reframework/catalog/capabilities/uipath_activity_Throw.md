---
id: "uipath/activity/Throw"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Throw

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Exception` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Exception": {
        "x-seen": "1/1",
        "examples": [
          "[new Exception(\"Credentials not supplied\")]"
        ]
      }
    },
    "required": [
      "Exception"
    ],
    "x-xaml-template": {
      "xml": "<Throw DisplayName=\"Throw (no credentials)\" Exception=\"[exception]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities"
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
