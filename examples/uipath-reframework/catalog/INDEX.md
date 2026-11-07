# Catalog

13 invocable capabilities, 38 activity types.

## Invocable

| Capability | Description | Inputs | Effects | Idempotency | Version |
|---|---|---|---|---|---|
| [CloseAllApplications](capabilities/uipath_ReFrameWork_Framework_CloseAllApplications.md) | Do necessary procedures for ending the process (e.g., logout) and close the applications used in th… | none | none | natural | 1.0.0 |
| [GetCredentials](capabilities/uipath_ReFrameWork_Framework_GetAppCredentials.md) | Securely fetch or create and use a set of credentials. | `in_Credential` | RWX | natural | 1.1.0 |
| [GetTransactionData](capabilities/uipath_ReFrameWork_Framework_GetTransactionData.md) | Get a transaction item from a specified source (e.g., spreadsheets, databases, email, web API or Or… | `in_TransactionNumber`, `in_Config`, `io_TransactionData` | RWX | none | 1.1.0 |
| [Initialize Applications](capabilities/uipath_ReFrameWork_Framework_InitAllApplications.md) | Open applications used in the process and do necessary initialization procedures (e.g., login). | `in_Config` | none | natural | 1.0.0 |
| [InitiAllSettings](capabilities/uipath_ReFrameWork_Framework_InitAllSettings.md) | Initialize, populate and output a configuration Dictionary to be used throughout the project. | `in_ConfigFile`, `in_ConfigSheets` | RX | natural | 1.0.0 |
| [KillAllProcesses](capabilities/uipath_ReFrameWork_Framework_KillAllProcesses.md) | Use the Kill Process activity to force the termination of the Windows processes representing applic… | none | none | natural | 1.0.0 |
| [SetTransactionStatus](capabilities/uipath_ReFrameWork_Framework_SetTransactionStatus.md) | Set and log the transaction's status along with extra log fields. | `in_Config`, `in_SystemError`, `in_BusinessRuleException`, `in_TransactionItem`, `io_RetryNumber`, `io_TransactionNumber`, `in_TransactionField1`, `in_TransactionField2`, `in_TransactionID` | RWdX | key | 1.1.0 |
| [TakeScreenshot](capabilities/uipath_ReFrameWork_Framework_TakeScreenshot.md) | Capture a screenshot, log its name and location and save it with the PNG extension. | `in_Folder`, `io_FilePath` | RWdX | none | 1.0.0 |
| [Main](capabilities/uipath_ReFrameWork_Main.md) | Process supplier invoices from the AP_Invoices queue: take each item, book it in the ERP and set it… | `in_OrchestratorQueueName` | RWdX | natural | 1.1.0 |
| [Process](capabilities/uipath_ReFrameWork_Process.md) | Invoke major steps of the business process, which are usually implemented by different workflows. | `in_TransactionItem`, `in_Config` | none | natural | 1.0.0 |
| [RunAllTests](capabilities/uipath_ReFrameWork_Tests_RunAllTests.md) | Run all tests defined in _Tests.xlsx and log their results. | `in_TestLogFile`, `in_OutputExcel` | RWdX | none | 1.0.0 |
| [RunAllTests_Logging](capabilities/uipath_ReFrameWork_Tests_RunAllTests_Logging.md) | Log the result of running the test, based on the type of test and its outcome. | `in_TestCounter`, `io_FailedTestsCounter`, `in_TestLogFile`, `out_Status`, `io_PassedTestsCounter`, `in_ExpectedOutcome`, `in_WorkflowFilename`, `in_Exception`, `in_ActualOutcome` | none | natural | 1.0.0 |
| [TestWorkflowTemplate](capabilities/uipath_ReFrameWork_Tests_TestWorkflowTemplate.md) | Template workflow used to create tests for workflows in the process. | none | RX | natural | 1.0.0 |

## Activity types

### control

- [Assign](capabilities/uipath_activity_Assign.md)
- [FlowDecision](capabilities/uipath_activity_FlowDecision.md)
- [Flowchart](capabilities/uipath_activity_Flowchart.md)
- [ForEach](capabilities/uipath_activity_ForEach.md)
- [ForEachRow](capabilities/uipath_activity_ForEachRow.md)
- [If](capabilities/uipath_activity_If.md)
- [InvokeMethod](capabilities/uipath_activity_InvokeMethod.md)
- [InvokeWorkflowFile](capabilities/uipath_activity_InvokeWorkflowFile.md)
- [Sequence](capabilities/uipath_activity_Sequence.md)
- [ShouldStop](capabilities/uipath_activity_ShouldStop.md)
- [State](capabilities/uipath_activity_State.md)
- [StateMachine](capabilities/uipath_activity_StateMachine.md)
- [Switch](capabilities/uipath_activity_Switch.md)
- [Throw](capabilities/uipath_activity_Throw.md)
- [Transition](capabilities/uipath_activity_Transition.md)
- [TryCatch](capabilities/uipath_activity_TryCatch.md)

### data

- [AddDataColumn](capabilities/uipath_activity_AddDataColumn.md)
- [AppendLine](capabilities/uipath_activity_AppendLine.md)

### filesystem

- [CreateDirectory](capabilities/uipath_activity_CreateDirectory.md) (side effects)
- [CreateFile](capabilities/uipath_activity_CreateFile.md) (side effects)
- [SaveImage](capabilities/uipath_activity_SaveImage.md) (side effects)

### integration.excel

- [ExcelApplicationScope](capabilities/uipath_activity_ExcelApplicationScope.md) (side effects) (unknown)
- [ExcelReadRange](capabilities/uipath_activity_ExcelReadRange.md)
- [ExcelWriteRange](capabilities/uipath_activity_ExcelWriteRange.md) (side effects)
- [ReadRange](capabilities/uipath_activity_ReadRange.md)

### logging

- [AddLogFields](capabilities/uipath_activity_AddLogFields.md)
- [Comment](capabilities/uipath_activity_Comment.md)
- [LogMessage](capabilities/uipath_activity_LogMessage.md)
- [RemoveLogFields](capabilities/uipath_activity_RemoveLogFields.md)

### orchestrator

- [AddCredential](capabilities/uipath_activity_AddCredential.md) (side effects)
- [GetQueueItem](capabilities/uipath_activity_GetQueueItem.md) (side effects)
- [GetRobotAsset](capabilities/uipath_activity_GetRobotAsset.md)
- [GetRobotCredential](capabilities/uipath_activity_GetRobotCredential.md)
- [GetSecureCredential](capabilities/uipath_activity_GetSecureCredential.md)
- [RequestCredential](capabilities/uipath_activity_RequestCredential.md)
- [SetTransactionStatus](capabilities/uipath_activity_SetTransactionStatus.md) (side effects)

### system

- [OpenApplication](capabilities/uipath_activity_OpenApplication.md) (side effects)

### ui

- [TakeScreenshot](capabilities/uipath_activity_TakeScreenshot.md)

Effects codes: R reads, W mutates state, D destructive, X external. Upper case means yes, lower case means unknown.
