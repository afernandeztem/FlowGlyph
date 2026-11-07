---
id: "uipath/activity/ExcelReadRange"
kind: "activity"
category: "integration.excel"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# ExcelReadRange

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AddHeaders` | any | yes |  |
| `DataTable` | any | yes |  |
| `Range` | any | yes |  |
| `SheetName` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "AddHeaders": {
        "x-seen": "1/1",
        "examples": [
          "True"
        ]
      },
      "DataTable": {
        "x-seen": "1/1",
        "examples": [
          "[Tests]"
        ]
      },
      "Range": {
        "x-seen": "1/1",
        "x-clr-types": [
          "x:String"
        ]
      },
      "SheetName": {
        "x-seen": "1/1",
        "examples": [
          "Tests"
        ]
      }
    },
    "required": [
      "AddHeaders",
      "DataTable",
      "Range",
      "SheetName"
    ],
    "x-xaml-template": {
      "xml": "<ui:ExcelReadRange AddHeaders=\"True\" DataTable=\"[dataTable]\" DisplayName=\"Read Range (Defined tests)\" SheetName=\"Tests\">\n  <ui:ExcelReadRange.Range>\n    <InArgument x:TypeArguments=\"x:String\">\n      <Literal x:TypeArguments=\"x:String\" Value=\"[value]\" />\n    </InArgument>\n  </ui:ExcelReadRange.Range>\n</ui:ExcelReadRange>",
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
