---
id: "uipath/activity/ExcelApplicationScope"
kind: "activity"
category: "integration.excel"
version: "1.0.0"
effects: "RwX"
idempotency: "none"
invocable: false
---

# ExcelApplicationScope

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: yes, mutates state: unknown, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Body` | any | yes |  |
| `Password` | any | yes |  |
| `WorkbookPath` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Body": {
        "x-seen": "1/1",
        "x-clr-types": [
          "ui:WorkbookApplication"
        ]
      },
      "Password": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "WorkbookPath": {
        "x-seen": "1/1",
        "examples": [
          "Tests\\_Tests.xlsx"
        ]
      }
    },
    "required": [
      "Body",
      "Password",
      "WorkbookPath"
    ],
    "x-xaml-template": {
      "xml": "<ui:ExcelApplicationScope Password=\"{x:Null}\" DisplayName=\"Excel application scope\" WorkbookPath=\"[workbookPath]\">\n  <ui:ExcelApplicationScope.Body>\n    <ActivityAction x:TypeArguments=\"ui:WorkbookApplication\">\n      <ActivityAction.Argument>\n        <DelegateInArgument x:TypeArguments=\"ui:WorkbookApplication\" Name=\"ExcelWorkbookScope\" />\n      </ActivityAction.Argument>\n      <!-- activities -->\n    </ActivityAction>\n  </ui:ExcelApplicationScope.Body>\n</ui:ExcelApplicationScope>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Tests/RunAllTests.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
