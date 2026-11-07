---
id: "uipath/activity/ExcelWriteRange"
kind: "activity"
category: "integration.excel"
version: "1.0.0"
effects: "WdX"
idempotency: "none"
invocable: false
---

# ExcelWriteRange

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `AddHeaders` | any | yes |  |
| `DataTable` | any | yes |  |
| `SheetName` | any | yes |  |
| `StartingCell` | any | yes |  |

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
      "SheetName": {
        "x-seen": "1/1",
        "examples": [
          "Result"
        ]
      },
      "StartingCell": {
        "x-seen": "1/1",
        "examples": [
          "A1"
        ]
      }
    },
    "required": [
      "AddHeaders",
      "DataTable",
      "SheetName",
      "StartingCell"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
