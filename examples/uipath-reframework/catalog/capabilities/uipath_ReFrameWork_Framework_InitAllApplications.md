---
id: "uipath/ReFrameWork/Framework/InitAllApplications"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: true
---

# Initialize Applications

Open applications used in the process and do necessary initialization procedures (e.g., login).

- **Source:** `Framework/InitAllApplications.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Framework/InitAllApplications.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Config` | object or null | yes | Dictionary structure to store configuration data. This structure can be used to store, for example, an URL for a system that needs to be initialized.  It is not recommended to use it to store credentials; instead, store them on Orchestrator and just pass the name of the credential asset as a setting in this dictionary. Then use the GetAppCredentials workflow to retrieve the credentials securely. |

## Outputs

None.

## Steps


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
        "description": "Dictionary structure to store configuration data. This structure can be used to store, for example, an URL for a system that needs to be initialized. \nIt is not recommended to use it to store credentials; instead, store them on Orchestrator and just pass the name of the credential asset as a setting in this dictionary. Then use the GetAppCredentials workflow to retrieve the credentials securely.",
        "x-direction": "in"
      }
    },
    "required": [
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
