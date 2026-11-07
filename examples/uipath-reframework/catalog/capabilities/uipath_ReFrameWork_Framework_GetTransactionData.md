---
id: "uipath/ReFrameWork/Framework/GetTransactionData"
kind: "workflow"
category: "workflow"
version: "1.1.0"
effects: "RWX"
idempotency: "none"
invocable: true
---

# GetTransactionData

Get a transaction item from a specified source (e.g., spreadsheets, databases, email, web API or Orchestrator). 

If there are no transaction items remaining, out_TransactionItem is set to Nothing, which leads to the End Process state. 

For cases in which there is only a single transaction (i.e., a linear process), check whether the argument in_TransactionNumber has the value 1 (meaning it's the first and only transaction) and assign the transaction item to out_TransactionItem. For any other value of in_TransactionNumber, out_TransactionItem should be set to Nothing.

If there are multiple transactions, use the argument in_TransactionNumber as an index to retrieve the correct transaction to be processed. If there are no more transactions left, it is necessary to set out_TransactionItem to Nothing, thus ending the process.

- **Source:** `Framework/GetTransactionData.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: no, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (declared, confidence 1.0)
- **Started by:** a call through Invoke Workflow File at `Framework/GetTransactionData.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_TransactionNumber` | integer | yes | Sequential counter of transaction items. |
| `in_Config` | object or null | yes | Dictionary structure to store configuration data. |
| `io_TransactionData` | object or null | yes | This variable can be used in case transactions are stored in a DataTable (for example, after being retrieved from a spreadsheet). |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_TransactionItem` | object or null | Transaction item to be processed. |
| `out_TransactionField1` | string or null | Allow the optional addition of information about the transaction item. |
| `out_TransactionField2` | string or null | Allow the optional addition of information about the transaction item. |
| `out_TransactionID` | string or null | Transaction ID used for information and logging purposes. Ideally, the ID should be unique for each transaction. |

## Steps

1. **Get transaction item** (activity) -> [GetQueueItem](uipath_activity_GetQueueItem.md)
   Get a transaction item from the specified Orchestrator queue.

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_TransactionNumber": {
        "type": "integer",
        "x-clr-type": "InArgument(x:Int32)",
        "description": "Sequential counter of transaction items.",
        "x-direction": "in"
      },
      "in_Config": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(scg:Dictionary(x:String, x:Object))",
        "description": "Dictionary structure to store configuration data.",
        "x-direction": "in"
      },
      "io_TransactionData": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InOutArgument(sd:DataTable)",
        "description": "This variable can be used in case transactions are stored in a DataTable (for example, after being retrieved from a spreadsheet).",
        "x-direction": "inout"
      }
    },
    "required": [
      "in_TransactionNumber",
      "in_Config",
      "io_TransactionData"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_TransactionItem": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "OutArgument(ui:QueueItem)",
        "description": "Transaction item to be processed."
      },
      "out_TransactionField1": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)",
        "description": "Allow the optional addition of information about the transaction item."
      },
      "out_TransactionField2": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)",
        "description": "Allow the optional addition of information about the transaction item."
      },
      "out_TransactionID": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)",
        "description": "Transaction ID used for information and logging purposes. Ideally, the ID should be unique for each transaction."
      }
    }
  }
}
```
