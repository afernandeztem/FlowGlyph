---
id: "uipath/activity/GetQueueItem"
kind: "activity"
category: "orchestrator"
version: "1.0.0"
effects: "RWX"
idempotency: "none"
invocable: false
---

# GetQueueItem

Get a transaction item from the specified Orchestrator queue.
If queues are not used in this process, replace this activity with the appropriated logic to retrieve transaction items.
For example, if transactions are rows from a DataTable, the row corresponding to the current transaction is retrieved at this point.

- **Source:** `Framework/GetTransactionData.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `ContinueOnError` | any | yes |  |
| `QueueType` | any | yes |  |
| `TimeoutMS` | any | yes |  |
| `TransactionItem` | any | yes |  |

## Used in

- `Framework/GetTransactionData.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "ContinueOnError": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "QueueType": {
        "x-seen": "1/1",
        "examples": [
          "[in_Config(\"OrchestratorQueueName\").ToString]"
        ]
      },
      "TimeoutMS": {
        "x-seen": "1/1",
        "examples": [
          "{x:Null}"
        ]
      },
      "TransactionItem": {
        "x-seen": "1/1",
        "examples": [
          "[out_TransactionItem]"
        ]
      }
    },
    "required": [
      "ContinueOnError",
      "QueueType",
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
