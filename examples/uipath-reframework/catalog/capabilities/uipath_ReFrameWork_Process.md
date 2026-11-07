---
id: "uipath/ReFrameWork/Process"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# Process

Invoke major steps of the business process, which are usually implemented by different workflows.

If a BusinessRuleException is thrown, the transaction will be skipped. 
If another kind of exception (ApplicationException) occurs, the current transaction can be retried.

- **Source:** `Process.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Process.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_TransactionItem` | object or null | yes | Transaction item to be processed. |
| `in_Config` | object or null | yes | Dictionary structure to store configuration data. |

## Outputs

None.

## Steps


## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_TransactionItem": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "InArgument(ui:QueueItem)",
        "description": "Transaction item to be processed.",
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
      }
    },
    "required": [
      "in_TransactionItem",
      "in_Config"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
