---
id: "uipath/ReFrameWork/Framework/SetTransactionStatus"
kind: "workflow"
category: "workflow"
version: "1.1.0"
effects: "RWdX"
idempotency: "key"
invocable: true
---

# SetTransactionStatus

Set and log the transaction's status along with extra log fields. 
There can be three possible statuses: Success, Business Rule Exception and System Error (Application Exception).

Business Rule Exception characterizes an irregular situation according to the process's rules and prevents the transaction to be processed. The transaction is not retried in this case, since the result will be the same until the problem that causes the exception is solved.
For example, it can be considered a BusinessRuleException if a process expects to read an email's attachment, but the sender didn't attach any file. In this case, immediate retries of the transaction will not yield a different result.

On the other hand, system errors are characterized by exceptions whose types are different than BusinessRuleException. When this kind of exception happens, the transaction item can be retried after closing and reopening the applications involved in the process. The rationale behind this is that the exception was caused by a problem in the applications, which might be solved by restarting them.

If Orchestrator queues are the source of transactions, the Set Transaction Status activity is used to update the status. In addition, the retry mechanism is also implemented by Orchestrator.

If Orchestrator queues are not used, the status can be set, for example, by writing to a specific column in a spreadsheet. In such cases, the retry mechanism is covered by the framework and the number of retries is defined in the configuration file.

At the end, io_TransactionNumber is incremented, which makes the framework get the next transaction to be processed.

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** key, safe to retry when deduplicated on in_TransactionID (declared, confidence 1.0)
- **Started by:** a call through Invoke Workflow File at `Framework/SetTransactionStatus.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Config` | object or null | yes | Dictionary structure to store configuration data. |
| `in_SystemError` | object or null | yes | Exception variable that is used during transitions between states. |
| `in_BusinessRuleException` | object or null | yes | Exception variable that is used during transitions between states. |
| `in_TransactionItem` | object or null | no | Transaction item to be processed. |
| `io_RetryNumber` | integer | yes | This variable controls the number of attempts of retrying the process in case of System Error. |
| `io_TransactionNumber` | integer | yes | Sequential counter of transaction items. |
| `in_TransactionField1` | string or null | yes | Allow the optional addition of information about the transaction item. |
| `in_TransactionField2` | string or null | yes | Allow the optional addition of information about the transaction item. |
| `in_TransactionID` | string or null | yes | Transaction ID used for information and logging purposes. |

## Outputs

None.

## Steps

1. **Set Transaction Status** (opaque)
   Set and log the transaction's status along with extra log fields.
2. **If in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))** (decision)
3. **Set transaction status (Successful)** (activity) -> [SetTransactionStatus](uipath_activity_SetTransactionStatus.md)
4. **If in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))** (decision, runs if any predecessor ran)
5. **Set transaction status (BusinessRuleException status** (activity) -> [SetTransactionStatus](uipath_activity_SetTransactionStatus.md)
6. **If in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))** (decision, runs if any predecessor ran)
7. **Set transaction status (SystemError)** (activity) -> [SetTransactionStatus](uipath_activity_SetTransactionStatus.md)
8. **Retry current transaction** (opaque, runs if any predecessor ran)
9. **Take Screenshot** (invoke) -> [TakeScreenshot](uipath_ReFrameWork_Framework_TakeScreenshot.md)
10. **Close All Applications** (invoke) -> [CloseAllApplications](uipath_ReFrameWork_Framework_CloseAllApplications.md)
11. **Kill All Processes** (invoke) -> [KillAllProcesses](uipath_ReFrameWork_Framework_KillAllProcesses.md)

Branches:

- `If_2` -> `node_3` when `in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))`
- `If_3` -> `SetTransactionStatus_2` when `in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))`
- `If_4` -> `SetTransactionStatus_3` when `in_TransactionItem isNot Nothing AndAlso (in_TransactionItem.GetType is GetType(Uipath.Core.QueueItem))`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_Config": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "description": "Dictionary structure to store configuration data.",
        "x-direction": "in"
      },
      "in_SystemError": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(s:Exception)",
        "description": "Exception variable that is used during transitions between states.",
        "x-direction": "in"
      },
      "in_BusinessRuleException": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(ui:BusinessRuleException)",
        "description": "Exception variable that is used during transitions between states.",
        "x-direction": "in"
      },
      "in_TransactionItem": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(ui:QueueItem)",
        "description": "Transaction item to be processed.",
        "x-default-expression": "[Nothing]",
        "x-direction": "in"
      },
      "io_RetryNumber": {
        "type": "integer",
        "x-clr-type": "InOutArgument(x:Int32)",
        "description": "This variable controls the number of attempts of retrying the process in case of System Error.",
        "x-direction": "inout"
      },
      "io_TransactionNumber": {
        "type": "integer",
        "x-clr-type": "InOutArgument(x:Int32)",
        "description": "Sequential counter of transaction items.",
        "x-direction": "inout"
      },
      "in_TransactionField1": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Allow the optional addition of information about the transaction item.",
        "x-direction": "in"
      },
      "in_TransactionField2": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Allow the optional addition of information about the transaction item.",
        "x-direction": "in"
      },
      "in_TransactionID": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Transaction ID used for information and logging purposes.",
        "x-direction": "in"
      }
    },
    "required": [
      "in_Config",
      "in_SystemError",
      "in_BusinessRuleException",
      "io_RetryNumber",
      "io_TransactionNumber",
      "in_TransactionField1",
      "in_TransactionField2",
      "in_TransactionID"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
