---
id: "uipath/ReFrameWork/Framework/TakeScreenshot"
kind: "workflow"
category: "workflow"
version: "1.0.0"
effects: "RWdX"
idempotency: "none"
invocable: true
---

# TakeScreenshot

Capture a screenshot, log its name and location and save it with the PNG extension.
If no specific filepath is passed as argument, it'll save the image in the folder specified by in_Folder.

- **Source:** `Framework/TakeScreenshot.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: unknown, external: yes
- **Idempotency:** none, not idempotent: run through the gateway with an idempotency key (inferred, confidence 0.7)
- **Started by:** a call through Invoke Workflow File at `Framework/TakeScreenshot.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Folder` | string or null | yes | Path to the folder where the screenshot should be saved. |
| `io_FilePath` | string or null | yes | Optional argument that specifies the path and the name of the screenshot to be taken. |

## Outputs

None.

## Steps

1. **Take screenshot** (activity) -> [TakeScreenshot](uipath_activity_TakeScreenshot.md)
   The whole screen is captured.
2. **If String.IsNullOrEmpty(io_FilePath)** (decision)
3. **If Not Directory.Exists(ScreenshotFileInfo.DirectoryName)** (decision)
4. **Create directory** (activity) -> [CreateDirectory](uipath_activity_CreateDirectory.md)
5. **Save screenshot** (activity, runs if any predecessor ran) -> [SaveImage](uipath_activity_SaveImage.md)

Branches:

- `If_2` -> `CreateDirectory_1` when `Not Directory.Exists(ScreenshotFileInfo.DirectoryName)`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_Folder": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Path to the folder where the screenshot should be saved.",
        "x-direction": "in"
      },
      "io_FilePath": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InOutArgument(x:String)",
        "description": "Optional argument that specifies the path and the name of the screenshot to be taken.",
        "x-direction": "inout"
      }
    },
    "required": [
      "in_Folder",
      "io_FilePath"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
