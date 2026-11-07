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
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
