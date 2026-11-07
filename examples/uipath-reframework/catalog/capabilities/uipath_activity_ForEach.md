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
    ],
    "x-xaml-template": {
      "xml": "<ui:ForEach x:TypeArguments=\"x:Char\" DisplayName=\"For each character in password\" Values=\"[values]\">\n  <ui:ForEach.Body>\n    <ActivityAction x:TypeArguments=\"x:Char\">\n      <ActivityAction.Argument>\n        <DelegateInArgument x:TypeArguments=\"x:Char\" Name=\"PasswordCharacter\" />\n      </ActivityAction.Argument>\n      <!-- activities -->\n    </ActivityAction>\n  </ui:ForEach.Body>\n</ui:ForEach>",
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
