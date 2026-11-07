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
    ],
    "x-xaml-template": {
      "xml": "<Flowchart DisplayName=\"Set Transaction Status\">\n  <Flowchart.StartNode>\n    <!-- activities -->\n  </Flowchart.StartNode>\n  <sads:DebugSymbol.Symbol>[symbol]</sads:DebugSymbol.Symbol>\n</Flowchart>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "sads": "http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger"
      },
      "from": "Framework/SetTransactionStatus.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
