---
id: "uipath/ReFrameWork/Framework/InitAllSettings"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "RX"
idempotency: "natural"
invocable: true
---

# InitiAllSettings

Initialize, populate and output a configuration Dictionary to be used throughout the project. 
Settings and constants are read from the local configuration file, and assets are fetched from Orchestrator. 
Asset values will overwrite settings and constant values if they are defined with the same name.

- **Source:** `Framework/InitAllSettings.xaml` (uipath)
- **Effects:** reads: yes, mutates state: no, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)
- **Started by:** a call through Invoke Workflow File at `Framework/InitAllSettings.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_ConfigFile` | string or null | no | Path to the configuration file that defines settings, constants and assets. |
| `in_ConfigSheets` | array or null | no | Names of the sheets corresponding to settings and constants in the configuration file. |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_Config` | object or null | Dictionary that holds values of settings, constants and assets. |

## Steps

1. **Read range (Settings and Constants sheets)** (activity) -> [ReadRange](uipath_activity_ReadRange.md)
2. **If Not String.IsNullOrEmpty(row("Name").ToString.Trim)** (decision)
   Read non-empty rows in the sheet.
3. **Read range (Assets sheet)** (activity) -> [ReadRange](uipath_activity_ReadRange.md)
4. **Get Asset** (activity) -> [GetRobotAsset](uipath_activity_GetRobotAsset.md)
5. **If Not String.IsNullOrEmpty(Row("Name").ToString.Trim)** (decision)
   Logs a warn message in case the asset is specified in the Config file, but it could not be loaded from Orchestrator.

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_ConfigFile": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Path to the configuration file that defines settings, constants and assets.",
        "x-default-expression": "Data\\Config.xlsx",
        "x-direction": "in"
      },
      "in_ConfigSheets": {
        "type": [
          "array",
          "null"
        ],
        "x-clr-type": "InArgument(s:String[])",
        "description": "Names of the sheets corresponding to settings and constants in the configuration file.",
        "x-default-expression": "[{\"Settings\",\"Constants\"}]",
        "x-direction": "in"
      }
    },
    "required": [],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_Config": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "OutArgument(scg:Dictionary(x:String, x:Object))",
        "description": "Dictionary that holds values of settings, constants and assets."
      }
    }
  }
}
```
