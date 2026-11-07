---
id: "uipath/activity/ForEachRow"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# ForEachRow

- **Source:** `Framework/InitAllSettings.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Body` | any | yes |  |
| `DataTable` | any | yes |  |

## Used in

- `Framework/InitAllSettings.xaml`
- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Body": {
        "x-seen": "3/3",
        "x-clr-types": [
          "sd:DataRow"
        ]
      },
      "DataTable": {
        "x-seen": "3/3",
        "examples": [
          "[SettingsAndConstants]",
          "[Assets]",
          "[Tests]"
        ]
      }
    },
    "required": [
      "Body",
      "DataTable"
    ],
    "x-xaml-template": {
      "xml": "<ui:ForEachRow DataTable=\"[dataTable]\" DisplayName=\"For each configuration row\">\n  <ui:ForEachRow.Body>\n    <ActivityAction x:TypeArguments=\"sd:DataRow\">\n      <ActivityAction.Argument>\n        <DelegateInArgument x:TypeArguments=\"sd:DataRow\" Name=\"Row\" />\n      </ActivityAction.Argument>\n      <!-- activities -->\n    </ActivityAction>\n  </ui:ForEachRow.Body>\n</ui:ForEachRow>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "sd": "clr-namespace:System.Data;assembly=System.Data",
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
