---
id: "uipath/activity/Flowchart"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Flowchart

Set and log the transaction's status along with extra log fields. 
There can be three possible statuses: Success, Business Rule Exception and System Error (Application Exception).

Business Rule Exception characterizes an irregular situation according to the process's rules and prevents the transaction to be processed. The transaction is not retried in this case, since the result will be the same until the problem that causes the exception is solved.
For example, it can be considered a BusinessRuleException if a process expects to read an email's attachment, but the sender didn't attach any file. In this case, immediate retries of the transaction will not yield a different result.

On the other hand, system errors are characterized by exceptions whose types are different than BusinessRuleException. When this kind of exception happens, the transaction item can be retried after closing and reopening the applications involved in the process. The rationale behind this is that the exception was caused by a problem in the applications, which might be solved by restarting them.

If Orchestrator queues are the source of transactions, the Set Transaction Status activity is used to update the status. In addition, the retry mechanism is also implemented by Orchestrator.

If Orchestrator queues are not used, the status can be set, for example, by writing to a specific column in a spreadsheet. In such cases, the retry mechanism is covered by the framework and the number of retries is defined in the configuration file.

At the end, io_TransactionNumber is incremented, which makes the framework get the next transaction to be processed.

- **Source:** `Framework/SetTransactionStatus.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `StartNode` | any | yes |  |

## Used in

- `Framework/SetTransactionStatus.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "StartNode": {
        "x-seen": "2/2",
        "x-clr-types": [
          "x:Int32",
          "x:String, InArgument"
        ]
      }
    },
    "required": [
      "StartNode"
    ]
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
