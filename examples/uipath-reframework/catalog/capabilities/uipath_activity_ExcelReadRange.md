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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
