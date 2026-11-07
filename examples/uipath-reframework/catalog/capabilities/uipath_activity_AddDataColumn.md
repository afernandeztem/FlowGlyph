---
id: "uipath/activity/AddDataColumn"
kind: "activity"
category: "data"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# AddDataColumn

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AllowDBNull` | any | yes |  |
| `AutoIncrement` | any | yes |  |
| `Column` | any | yes |  |
| `ColumnName` | any | yes |  |
| `DataTable` | any | yes |  |
| `DefaultValue` | any | yes |  |
| `MaxLength` | any | yes |  |
| `Unique` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "AllowDBNull": {
        "x-seen": "2/2",
        "examples": [
          "True"
        ]
      },
      "AutoIncrement": {
        "x-seen": "2/2",
        "examples": [
          "False"
        ]
      },
      "Column": {
        "x-seen": "2/2",
        "examples": [
          "{x:Null}"
        ]
      },
      "ColumnName": {
        "x-seen": "2/2",
        "examples": [
          "Status",
          "Comments"
        ]
      },
      "DataTable": {
        "x-seen": "2/2",
        "examples": [
          "[Tests]"
        ]
      },
      "DefaultValue": {
        "x-seen": "2/2",
        "examples": [
          "{x:Null}"
        ]
      },
      "MaxLength": {
        "x-seen": "2/2",
        "examples": [
          "-1"
        ]
      },
      "Unique": {
        "x-seen": "2/2",
        "examples": [
          "False"
        ]
      }
    },
    "required": [
      "AllowDBNull",
      "AutoIncrement",
      "Column",
      "ColumnName",
      "DataTable",
      "DefaultValue",
      "MaxLength",
      "Unique"
    ],
    "x-xaml-template": {
      "xml": "<ui:AddDataColumn x:TypeArguments=\"x:String\" Column=\"{x:Null}\" DefaultValue=\"{x:Null}\" AllowDBNull=\"True\" AutoIncrement=\"False\" ColumnName=\"Status\" DataTable=\"[dataTable]\" DisplayName=\"Add Status column\" MaxLength=\"-1\" Unique=\"False\" />",
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
