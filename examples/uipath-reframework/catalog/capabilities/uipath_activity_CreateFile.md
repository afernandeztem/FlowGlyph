---
id: "uipath/activity/CreateFile"
kind: "activity"
category: "filesystem"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# CreateFile

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ContinueOnError` | any | yes |  |
| `Name` | any | yes |  |
| `Path` | any | yes |  |

## Used in

- `Tests/RunAllTests.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ContinueOnError": {
        "x-seen": "1/1",
        "examples": [
          "True"
        ]
      },
      "Name": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "Path": {
        "x-seen": "1/1",
        "examples": [
          "[in_TestLogFile]"
        ]
      }
    },
    "required": [
      "ContinueOnError",
      "Name",
      "Path"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
