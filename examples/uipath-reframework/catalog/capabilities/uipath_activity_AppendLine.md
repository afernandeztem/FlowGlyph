---
id: "uipath/activity/AppendLine"
kind: "activity"
category: "data"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# AppendLine

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `FileName` | any | yes |  |
| `Text` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`
- `Tests/RunAllTests_Logging.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "FileName": {
        "x-seen": "7/7",
        "examples": [
          "[in_TestLogFile]"
        ]
      },
      "Text": {
        "x-seen": "7/7",
        "examples": [
          "[Environment.NewLine+\"=================================================\"]",
          "[\"Starting new set of \"+Tests.Rows.Count.ToString+\" tests at \"+now.ToString(\"hh:",
          "================================================="
        ]
      }
    },
    "required": [
      "FileName",
      "Text"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
