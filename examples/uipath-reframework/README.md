# Example: a UiPath process built on the ReFrameWork

The [Robotic Enterprise Framework](https://github.com/UiPath/ReFrameWork) is the template most
UiPath processes start from: a state machine that reads a configuration, takes items from an
Orchestrator queue one by one, processes each and sets its status. This example takes a copy of
it through every stage of FlowGlyph, with the real output of each command.

```
sources/ReFrameWork/       the template as published by UiPath (MIT, see its LICENSE)
overrides.yaml             what the team that owns the process knows, used in step 5
add-kill-process.patch     a change a developer makes in Studio, used in step 6
policy.yaml                what an agent may run, used in step 8
demo_gateway.py            an agent's calls through the gateway, used in step 8
catalog/                   what steps 1 to 5 produce, committed
```

Run every command from this directory with `flowglyph[cli]` installed
(`pip install "flowglyph[cli]"`, or `uv run` in a checkout).

## 1. Extract the project

```console
$ flowglyph extract sources -o catalog
Extracted 13 invocable capabilities and 38 that cannot be run on their own into catalog
  warning ReFrameWork/Tests/RunAllTests.xaml: invokes a workflow chosen at runtime by the expression [Row("WorkflowFile").ToString]
  warning ReFrameWork/Tests/RunAllTests_Logging.xaml: argument out_Status is named like out_ but is in
```

Every `.xaml` workflow becomes a capability typed from its arguments: 13 you can invoke. Every
activity type the project uses (`GetQueueItem`, `ExcelReadRange`, `LogMessage`...) becomes one
of the 38 documentation-only capabilities, which record where they are used and what they do to
the world. Both warnings are real: the test runner reads which workflow to invoke from a
spreadsheet at runtime, and one argument is named like an output but declared as an input.

`flowglyph extract https://github.com/UiPath/ReFrameWork -o catalog` reads the latest version
straight from GitHub instead.

## 2. The call tree

```console
$ flowglyph inspect catalog
Main RWdX none
├── InitiAllSettings RX natural
├── KillAllProcesses pure natural
├── Initialize Applications pure natural
├── GetTransactionData RWX none
├── Process pure natural
├── SetTransactionStatus RWdX none
│   ├── TakeScreenshot RWdX none
│   ├── CloseAllApplications pure natural
│   └── KillAllProcesses pure natural
└── CloseAllApplications pure natural
```

Each line shows a workflow, its effects and its idempotency. The effects code reads `R`ead,
`W`rite, `D`estroy, e`X`ternal: upper case for yes, lower case for unknown, absent for no. Effects
travel up the tree, so `Main` reads, writes and calls other systems because the workflows it
invokes do.

`KillAllProcesses`, `CloseAllApplications`, `InitAllApplications` and `Process` are **pure**
because in the template they are empty placeholders that only log a message. They stop being
pure the moment you fill them in; step 6 shows what happens then.

## 3. What every workflow does to the world

```console
$ flowglyph idempotency catalog --kind workflow
 Capability                                         Kind      Effects  Idempotency  Status
 uipath/ReFrameWork/Framework/CloseAllApplications  workflow  none     natural      safe
 uipath/ReFrameWork/Framework/GetAppCredentials     workflow  RWX      none         review
 uipath/ReFrameWork/Framework/GetTransactionData    workflow  RWX      none         review
 uipath/ReFrameWork/Framework/InitAllApplications   workflow  none     natural      safe
 uipath/ReFrameWork/Framework/InitAllSettings       workflow  RX       natural      safe
 uipath/ReFrameWork/Framework/KillAllProcesses      workflow  none     natural      safe
 uipath/ReFrameWork/Framework/SetTransactionStatus  workflow  RWdX     none         review
 uipath/ReFrameWork/Framework/TakeScreenshot        workflow  RWdX     none         review
 uipath/ReFrameWork/Main                            workflow  RWdX     none         review
 uipath/ReFrameWork/Process                         workflow  none     natural      safe
 uipath/ReFrameWork/Tests/RunAllTests               workflow  RWdX     none         review
 uipath/ReFrameWork/Tests/RunAllTests_Logging       workflow  none     natural      safe
 uipath/ReFrameWork/Tests/TestWorkflowTemplate      workflow  RX       natural      safe
13 capabilities, 6 to review.
```

The effects come from the activities each workflow uses, classified in FlowGlyph's UiPath
taxonomy. Some answers are worth a second look:

- `GetTransactionData` **writes**: its *Get Transaction Item* marks the queue item In Progress,
  so calling it twice takes two different items. A retry is not a repeat.
- `InitAllSettings` only **reads**: it loads `Config.xlsx` and Orchestrator assets, so it is safe
  to run again.
- `GetAppCredentials` writes because it creates the credential when it does not exist yet.

The activity types behind those answers:

```console
$ flowglyph idempotency catalog --kind activity --side-effects
 Capability                             Kind      Effects  Idempotency  Status
 uipath/activity/AddCredential          activity  W        none         n/a
 uipath/activity/CreateDirectory        activity  WX       none         n/a
 uipath/activity/CreateFile             activity  WX       none         n/a
 uipath/activity/ExcelApplicationScope  activity  RwX      none         n/a
 uipath/activity/ExcelWriteRange        activity  WdX      none         n/a
 uipath/activity/GetQueueItem           activity  RWX      none         n/a
 uipath/activity/OpenApplication        activity  WX       none         n/a
 uipath/activity/SaveImage              activity  WdX      none         n/a
 uipath/activity/SetTransactionStatus   activity  WX       none         n/a
9 capabilities, 0 to review.
```

Activity types are `n/a`: they never run on their own, so whether to retry is decided by the
workflows that use them.

## 4. Find and read a workflow

```console
$ flowglyph search catalog "read the configuration from excel" -n 3 --invocable
 Capability                                      Kind      Effects  Idempotency  Description
 uipath/ReFrameWork/Framework/InitAllSettings    workflow  RX       natural      Initialize, populate and output a configuration Dictionary to be used
 uipath/ReFrameWork/Tests/RunAllTests            workflow  RWdX     none         Run all tests defined in _Tests.xlsx and log their results.
 uipath/ReFrameWork/Framework/GetAppCredentials  workflow  RWX      none         Securely fetch or create and use a set of credentials.
```

`flowglyph inspect catalog Framework/SetTransactionStatus` prints the full card: description,
effects, steps and every argument with its type. .NET reference types can be `Nothing`, so they
accept `null`:

```console
 Name                      Type            Required  Description
 in_Config                 object or null  yes       Dictionary structure to store configuration data.
 in_SystemError            object or null  yes       Exception variable that is used during transitions between states.
 in_BusinessRuleException  object or null  yes       Exception variable that is used during transitions between states.
 in_TransactionItem        object or null  no        Transaction item to be processed.
 io_RetryNumber            integer         yes       This variable controls the number of attempts of retrying the process in case of System Error.
 io_TransactionNumber      integer         yes       Sequential counter of transaction items.
 ...
```

The same cards, as Markdown, are in [`catalog/capabilities/`](catalog/capabilities/).

## 5. Settle what the XAML cannot say

[`overrides.yaml`](overrides.yaml) records what the team that owns the process knows:

- `Main` takes items from a queue, and an item already processed is never taken again, so
  running the whole process twice is safe. Starting it still needs a person. The template's
  placeholder description (`[Process title] [Process description]`) is replaced by a real one.
- `GetTransactionData` is deliberately not idempotent, and now says so.
- `SetTransactionStatus` sets one final status per queue item, so its transaction ID is a key.
- `GetAppCredentials` creates the credential once and reads it after that.

FlowGlyph reads overrides from `flowglyph.overrides.yaml` next to the sources:

```console
$ cp overrides.yaml sources/flowglyph.overrides.yaml
$ flowglyph extract sources -o catalog
Extracted 13 invocable capabilities and 38 that cannot be run on their own into catalog
Capability                                         Change   Bump   Version
uipath/ReFrameWork/Framework/GetAppCredentials     changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Framework/GetTransactionData    changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Framework/SetTransactionStatus  changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Main                            changed  minor  1.0.0 -> 1.1.0

$ flowglyph idempotency catalog --review
 Capability                                   Kind      Effects  Idempotency  Status
 uipath/ReFrameWork/Framework/TakeScreenshot  workflow  RWdX     none         review
 uipath/ReFrameWork/Tests/RunAllTests         workflow  RWdX     none         review
2 capabilities, 2 to review.
```

Declared answers are marked `declared` from now on, and changing what callers may assume is a
minor version. Two workflows are left to decide; repeat until the list is empty.

## 6. A developer changes a workflow

The template asks you to kill the applications your process uses in `KillAllProcesses`.
[`add-kill-process.patch`](add-kill-process.patch) is that change, as Studio would save it: one
*Kill Process* activity for Excel. Apply it to a copy and extract against a copy of the catalog:

```console
$ cp -R sources my-process && cp -R catalog my-catalog
$ patch -d my-process/ReFrameWork -p1 < add-kill-process.patch
patching file 'Framework/KillAllProcesses.xaml'
$ flowglyph extract my-process -o my-catalog
Extracted 13 invocable capabilities and 39 that cannot be run on their own into my-catalog
Capability                                         Change   Bump   Version
uipath/ReFrameWork/Framework/KillAllProcesses      changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Framework/SetTransactionStatus  changed  minor  1.1.0 -> 1.2.0
uipath/ReFrameWork/Main                            changed  minor  1.1.0 -> 1.2.0
uipath/activity/KillProcess                        added    minor  - -> 1.0.0
```

One activity changed three workflows: `KillAllProcesses` now destroys state (killing a process
can lose unsaved work), and so do `SetTransactionStatus` and `Main`, which invoke it. Each gets a
minor version, because callers keep working but should know.

In a pull request, the same comparison is a check that fails only on changes that break a
caller, such as a removed or newly required argument:

```console
$ flowglyph diff catalog my-catalog --fail-on major
Capability                                         Change   Bump   Version
uipath/ReFrameWork/Framework/KillAllProcesses      changed  minor  1.0.0 -> 1.1.0
uipath/ReFrameWork/Framework/SetTransactionStatus  changed  minor  1.1.0 -> 1.2.0
uipath/ReFrameWork/Main                            changed  minor  1.1.0 -> 1.2.0
uipath/activity/KillProcess                        added    minor  - -> 1.0.0
$ echo $?
0
```

## 7. A wiki for the team

```console
$ flowglyph wiki build catalog -o wiki
Wiki 64 pages in wiki
$ flowglyph wiki lint wiki
 Level    Page                                                            Issue
 info     capabilities/uipath_ReFrameWork_Framework_GetAppCredentials.md  nothing invokes it and it is not an entry point
 warning  capabilities/uipath_ReFrameWork_Framework_TakeScreenshot.md    has side effects and no retry guarantee: declare its idempotency
 warning  capabilities/uipath_ReFrameWork_Tests_RunAllTests.md           has side effects and no retry guarantee: declare its idempotency
 info     capabilities/uipath_ReFrameWork_Tests_RunAllTests.md           nothing invokes it and it is not an entry point
 info     capabilities/uipath_ReFrameWork_Tests_RunAllTests_Logging.md   argument out_Status is named like out_ but is in
 info     capabilities/uipath_ReFrameWork_Tests_TestWorkflowTemplate.md  nothing invokes it and it is not an entry point
 warning  capabilities/uipath_ReFrameWork_Tests_RunAllTests.md           invokes something that is not in the sources: [Row("WorkflowFile").ToString]
```

Every workflow, activity type, category and project gets a page with its contract, effects,
call tree and backlinks. Below the `<!-- flowglyph:notes -->` line of each page, people or an
LLM add what the XAML cannot say (who owns it, which queue it reads, what failed last month),
and rebuilding keeps it. `wiki/AGENTS.md` tells an LLM how to maintain the pages. The lint lists
what is still open: `GetAppCredentials` is not invoked by anything yet, because the template
leaves calling it to you.

## 8. Let an agent run it, safely

[`policy.yaml`](policy.yaml) denies the test workflows and holds `Main` for a person to approve.
[`demo_gateway.py`](demo_gateway.py) makes the calls an agent would, through the gateway, with
the dry-run executor:

```console
$ python demo_gateway.py
take an item: done, retried: replayed
set its status: done, again: replayed, key uipath/ReFrameWork/Framework/SetTransactionStatus#"INV-2291"
run the tests: denied, test workflows run in Studio, not on behalf of an agent
start the process: approval_required, starting the whole process works through the live queue
  a person must run `flowglyph approve …/catalog 'uipath/ReFrameWork/Main#auto:…' --state …`
an activity type: invalid, uipath/activity/TakeScreenshot is documentation only and cannot be run on its own
```

- The agent retried `GetTransactionData` with the same idempotency key, and the ledger returned
  the first result instead of taking a second queue item.
- `SetTransactionStatus` was deduplicated on its transaction ID, the key declared in step 5,
  without the agent passing a key at all.
- The tests were denied by the policy, and `Main` waits until a person runs the approval
  command; the agent's next attempt then goes through.

The same gateway serves agents over MCP:

```console
$ flowglyph serve catalog --policy policy.yaml
```

Running workflows for real, through Orchestrator, is on the [roadmap](../../README.md#roadmap);
until then every run is a dry run that reports what would have been started.
