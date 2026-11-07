---
id: "uipath/activity/InvokeMethod"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# InvokeMethod

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `MethodName` | any | yes |  |
| `TargetObject` | any | yes |  |

## Used in

- `Framework/GetAppCredentials.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "MethodName": {
        "x-seen": "1/1",
        "examples": [
          "AppendChar"
        ]
      },
      "TargetObject": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ss:SecureString"
        ]
      }
    },
    "required": [
      "MethodName",
      "TargetObject"
    ],
    "x-xaml-template": {
      "xml": "<InvokeMethod DisplayName=\"Invoke method (AppendChar)\" MethodName=\"AppendChar\">\n  <InvokeMethod.TargetObject>\n    <InArgument x:TypeArguments=\"ss:SecureString\">[targetObject]</InArgument>\n  </InvokeMethod.TargetObject>\n  <InArgument x:TypeArguments=\"x:Char\">[invokeMethod]</InArgument>\n</InvokeMethod>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ss": "clr-namespace:System.Security;assembly=mscorlib",
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
