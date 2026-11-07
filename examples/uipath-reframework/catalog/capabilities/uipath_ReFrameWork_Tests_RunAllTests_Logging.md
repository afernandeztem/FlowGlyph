---
id: "uipath/ReFrameWork/Tests/RunAllTests_Logging"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# RunAllTests_Logging

Log the result of running the test, based on the type of test and its outcome.

- **Source:** `Tests/RunAllTests_Logging.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Tests/RunAllTests_Logging.xaml`

> **Notes**
> - argument out_Status is named like out_ but is in

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_TestCounter` | integer | yes | Overall counter for tests. |
| `io_FailedTestsCounter` | integer | yes | Counter for tests that failed. |
| `in_TestLogFile` | string or null | yes | Filepath to which logs about tests should be written. |
| `out_Status` | string or null | yes | Status of the test to be written to the report. |
| `io_PassedTestsCounter` | integer | yes | Counter for tests that succeeded. |
| `in_ExpectedOutcome` | string or null | yes | Expected outcome of the test. It can be "Success", "AppEx" or "BRE". |
| `in_WorkflowFilename` | string or null | yes | Filename of the workflow that implements a test. |
| `in_Exception` | object or null | yes | Exception thrown by tests and used for logging purposes. |
| `in_ActualOutcome` | string or null | yes | Actual outcome of the test. It can be "Success", "AppEx" or "BRE". |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_Comments` | string or null | Comment about the test to be written to the report. |

## Steps


## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_TestCounter": {
        "type": "integer",
        "x-clr-type": "InArgument(x:Int32)",
        "description": "Overall counter for tests.",
        "x-direction": "in"
      },
      "io_FailedTestsCounter": {
        "type": "integer",
        "x-clr-type": "InOutArgument(x:Int32)",
        "description": "Counter for tests that failed.",
        "x-direction": "inout"
      },
      "in_TestLogFile": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Filepath to which logs about tests should be written.",
        "x-direction": "in"
      },
      "out_Status": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Status of the test to be written to the report.",
        "x-direction": "in"
      },
      "io_PassedTestsCounter": {
        "type": "integer",
        "x-clr-type": "InOutArgument(x:Int32)",
        "description": "Counter for tests that succeeded.",
        "x-direction": "inout"
      },
      "in_ExpectedOutcome": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Expected outcome of the test. It can be \"Success\", \"AppEx\" or \"BRE\".",
        "x-direction": "in"
      },
      "in_WorkflowFilename": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Filename of the workflow that implements a test.",
        "x-direction": "in"
      },
      "in_Exception": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(s:Exception)",
        "description": "Exception thrown by tests and used for logging purposes.",
        "x-direction": "in"
      },
      "in_ActualOutcome": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Actual outcome of the test. It can be \"Success\", \"AppEx\" or \"BRE\".",
        "x-direction": "in"
      }
    },
    "required": [
      "in_TestCounter",
      "io_FailedTestsCounter",
      "in_TestLogFile",
      "out_Status",
      "io_PassedTestsCounter",
      "in_ExpectedOutcome",
      "in_WorkflowFilename",
      "in_Exception",
      "in_ActualOutcome"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_Comments": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)",
        "description": "Comment about the test to be written to the report."
      }
    }
  }
}
```
