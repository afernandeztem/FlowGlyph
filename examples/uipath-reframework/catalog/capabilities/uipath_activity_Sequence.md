---
id: "uipath/activity/Sequence"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Sequence

Do necessary procedures for ending the process (e.g., logout) and close the applications used in the process.

- **Source:** `Framework/CloseAllApplications.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `Variables` | any | no |  |

## Used in

- `Framework/CloseAllApplications.xaml`
- `Framework/GetAppCredentials.xaml`
- `Framework/GetTransactionData.xaml`
- `Framework/InitAllApplications.xaml`
- `Framework/InitAllSettings.xaml`
- `Framework/KillAllProcesses.xaml`
- `Framework/SetTransactionStatus.xaml`
- `Framework/TakeScreenshot.xaml`
- `Main.xaml`
- `Process.xaml`
- `Tests/RunAllTests.xaml`
- `Tests/RunAllTests_Logging.xaml`
- `Tests/TestWorkflowTemplate.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "Variables": {
        "x-seen": "10/37",
        "x-clr-types": [
          "scg:Dictionary(x:String, x:Object)",
          "sd:DataTable",
          "ui:GenericValue",
          "ui:Image",
          "x:Boolean",
          "x:String"
        ]
      }
    },
    "required": [],
    "x-xaml-template": {
      "xml": "<Sequence DisplayName=\"Take and Save Screenshot\">\n  <Sequence.Variables>\n    <Variable x:TypeArguments=\"ui:Image\" Name=\"Screenshot\" />\n    <Variable x:TypeArguments=\"si:FileInfo\" Name=\"ScreenshotFileInfo\" />\n  </Sequence.Variables>\n  <!-- activities -->\n  <sads:DebugSymbol.Symbol>[symbol]</sads:DebugSymbol.Symbol>\n</Sequence>",
      "namespaces": {
        "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
        "sads": "http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger",
        "si": "clr-namespace:System.IO;assembly=mscorlib",
        "ui": "http://schemas.uipath.com/workflow/activities",
        "x": "http://schemas.microsoft.com/winfx/2006/xaml"
      },
      "from": "Framework/TakeScreenshot.xaml"
    }
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
