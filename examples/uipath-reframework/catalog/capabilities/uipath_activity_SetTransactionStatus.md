---
id: "uipath/activity/SetTransactionStatus"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "WX"
idempotency: "none"
invocable: false
---

# SetTransactionStatus

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ContinueOnError` | any | yes |  |
| `ErrorType` | any | yes |  |
| `Output` | any | yes |  |
| `Reason` | any | yes |  |
| `ServiceBaseAddress` | any | yes |  |
| `Status` | any | yes |  |
| `TimeoutMS` | any | yes |  |
| `TransactionItem` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ContinueOnError": {
        "x-seen": "3/3",
        "examples": [
          "{x:Null}"
        ]
      },
      "ErrorType": {
        "x-seen": "3/3",
        "examples": [
          "Application",
          "Business"
        ]
      },
      "Output": {
        "x-seen": "3/3",
        "x-clr-types": [
          "x:String, InArgument"
        ]
      },
      "Reason": {
        "x-seen": "3/3",
        "examples": [
          "{x:Null}",
          "[in_BusinessRuleException.Message]",
          "[in_SystemError.Message]"
        ]
      },
      "ServiceBaseAddress": {
        "x-seen": "3/3",
        "examples": [
          "{x:Null}"
        ]
      },
      "Status": {
        "x-seen": "3/3",
        "examples": [
          "Successful",
          "Failed"
        ]
      },
      "TimeoutMS": {
        "x-seen": "3/3",
        "examples": [
          "{x:Null}"
        ]
      },
      "TransactionItem": {
        "x-seen": "3/3",
        "examples": [
          "[in_TransactionItem]"
        ]
      }
    },
    "required": [
      "ContinueOnError",
      "ErrorType",
      "Output",
      "Reason",
      "ServiceBaseAddress",
      "Status",
      "TimeoutMS",
      "TransactionItem"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
