---
id: "uipath/ReFrameWork/Framework/GetAppCredentials"
kind: "workflow"
category: "workflow"
version: "1.1.0"
effects: "RWX"
idempotency: "natural"
invocable: true
---

# GetCredentials

Securely fetch or create and use a set of credentials.

First, there is an attempt to fetch credentials from Orchestrator using the name received as argument. 
If it is not possible to retrieve those credentials from Orchestrator, there is an attempt to fetch them from the Windows Credential Manager (WCM). 
If the credentials are not defined in the WCM, the user is prompted to create the credentials that will be added to the WCM and returned for use during the process execution.

The Private property is used to prevent the generation of logs that might contain information about the credentials.

- **Source:** `Framework/GetAppCredentials.xaml` (uipath)
- **Effects:** reads: yes, mutates state: yes, destructive: no, external: yes
- **Idempotency:** natural, safe to retry (declared, confidence 1.0)
- **Started by:** a call through Invoke Workflow File at `Framework/GetAppCredentials.xaml`

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| `in_Credential` | string or null | yes | Name of the credential to be retrieved. |

## Outputs

| Name | Type | Description |
|---|---|---|
| `out_Username` | string or null | Username associated with the specified credential. |
| `out_Password` | object or null | Password associated with the specified credential. |

## Steps

1. **Get credentials** (activity) -> [GetRobotCredential](uipath_activity_GetRobotCredential.md)
   Attempt to retrieve credentials from Orchestrator.
2. **If out_Username Is Nothing Or out_Password Is Nothing** (decision)
   The Private property is used to prevent the generation of logs that might contain information about the credentials.
3. **If Not CredentialsFound** (decision)
4. **Request credentials** (activity) -> [RequestCredential](uipath_activity_RequestCredential.md)
   Request credentials from user.
5. **If Not CredentialsFound** (decision)
   Throw exception in case of no credentials, or add provided credentials to Windows Credential Manager.
6. **Add Credential** (activity) -> [AddCredential](uipath_activity_AddCredential.md)
   Add provided credentials to the Windows Credential Manager to avoid requesting them in later executions of the process.

Branches:

- `If_5` -> `AddCredential_2` when `not (Not CredentialsFound)`
- `If_3` -> `RequestCredential_2` when `Not CredentialsFound`
- `If_4` -> `If_3` when `out_Username Is Nothing Or out_Password Is Nothing`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {
      "in_Credential": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "InArgument(x:String)",
        "description": "Name of the credential to be retrieved.",
        "x-direction": "in"
      }
    },
    "required": [
      "in_Credential"
    ],
    "additionalProperties": false
  },
  "output": {
    "type": "object",
    "properties": {
      "out_Username": {
        "type": [
          "string",
          "null"
        ],
        "x-clr-type": "OutArgument(x:String)",
        "description": "Username associated with the specified credential."
      },
      "out_Password": {
        "type": [
          "object",
          "null"
        ],
        "x-clr-type": "OutArgument(ss:SecureString)",
        "description": "Password associated with the specified credential."
      }
    }
  }
}
```
