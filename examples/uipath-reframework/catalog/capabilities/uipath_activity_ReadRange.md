---
id: "uipath/activity/ReadRange"
kind: "activity"
category: "integration.excel"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: false
---

# ReadRange

- **Source:** `Framework/InitAllSettings.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AddHeaders` | any | yes |  |
| `DataTable` | any | yes |  |
| `Range` | any | yes |  |
| `SheetName` | any | yes |  |
| `WorkbookPath` | any | yes |  |

## Used in

- `Framework/InitAllSettings.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "AddHeaders": {
        "x-seen": "2/2",
        "examples": [
          "True"
        ]
      },
      "DataTable": {
        "x-seen": "2/2",
        "examples": [
          "[SettingsAndConstants]",
          "[Assets]"
        ]
      },
      "Range": {
        "x-seen": "2/2",
        "examples": [
          "{x:Null}"
        ]
      },
      "SheetName": {
        "x-seen": "2/2",
        "examples": [
          "[Sheet]",
          "Assets"
        ]
      },
      "WorkbookPath": {
        "x-seen": "2/2",
        "examples": [
          "[in_ConfigFile]"
        ]
      }
    },
    "required": [
      "AddHeaders",
      "DataTable",
      "Range",
      "SheetName",
      "WorkbookPath"
    ],
    "x-xaml-template": {
      "xml": "<ui:ReadRange Range=\"{x:Null}\" AddHeaders=\"True\" DataTable=\"[dataTable]\" DisplayName=\"Read range (Settings and Constants sheets)\" SheetName=\"[sheetName]\" WorkbookPath=\"[workbookPath]\" />",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
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
