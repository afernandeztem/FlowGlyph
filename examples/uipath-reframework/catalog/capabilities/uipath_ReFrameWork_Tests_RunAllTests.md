---
id: "uipath/ReFrameWork/Tests/RunAllTests"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "RWdX"
idempotency: "none"
invocable: true
---

# RunAllTests

Run all tests defined in _Tests.xlsx and log their results.
All tests are invoked in the same order they are defined in the Excel file, and this can affect their output.

- **Source:** `Tests/RunAllTests.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through Invoke Workflow File at `Tests/RunAllTests.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_TestLogFile` | string or null | no | Path to the file to which test logs will be written. |
| `in_OutputExcel` | string or null | yes | Path to the Excel file to which the result of the tests will be written. |

## Outputs

None.

## Steps

1. **If Not File.Exists(in_TestLogFile)** (decision)
2. **Create Log file** (activity) -> [CreateFile](uipath_activity_CreateFile.md)
3. **Read Range (Defined tests)** (activity) -> [ExcelReadRange](uipath_activity_ExcelReadRange.md)
4. **Invoke Test File** (invoke)
5. **Invoke Test Logging (Success)** (invoke) -> [RunAllTests_Logging](uipath_ReFrameWork_Tests_RunAllTests_Logging.md)
6. **Invoke Test Logging (Application Exception)** (invoke) -> [RunAllTests_Logging](uipath_ReFrameWork_Tests_RunAllTests_Logging.md)
7. **Invoke Test Logging (BRE)** (invoke) -> [RunAllTests_Logging](uipath_ReFrameWork_Tests_RunAllTests_Logging.md)
8. **Write Range (Tests results)** (activity) -> [ExcelWriteRange](uipath_activity_ExcelWriteRange.md)
9. **Open application (Notepad)** (activity) -> [OpenApplication](uipath_activity_OpenApplication.md)
   Open log file in a Notepad window.
10. **Excel application scope** (container, runs if any predecessor ran) -> [ExcelApplicationScope](uipath_activity_ExcelApplicationScope.md)

Branches:

- `If_4` -> `CreateFile_1` when `Not File.Exists(in_TestLogFile)`

Unresolved invocations:

- `[Row("WorkflowFile").ToString]`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_TestLogFile": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Path to the file to which test logs will be written.",
        "x-default-expression": "Tests\\TestLog.txt",
        "x-direction": "in"
      },
      "in_OutputExcel": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Path to the Excel file to which the result of the tests will be written.",
        "x-direction": "in"
      }
    },
    "required": [
      "in_OutputExcel"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
