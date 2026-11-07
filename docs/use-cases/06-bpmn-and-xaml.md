# 6. The same workflow in BPMN or Studio

**For:** process owners who think in BPMN, developers who finish in UiPath Studio.
**Takes:** one command. **Needs:** `pip install "flowglyph[cli]"`.

## The situation

A planned workflow is YAML. The process owner wants to see it in the modeler they use, the
developer wants to start from a Studio file rather than a description, and the existing robots
would be easier to discuss as a diagram than as a folder of XAML.

## What you do

```bash
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to xaml -o Main.xaml
flowglyph compile plan/workflow.ir.yaml --catalog catalog --to bpmn -o invoice.bpmn
flowglyph compile catalog uipath/Invoices/Main --to bpmn --engine camunda8 -o main.bpmn   # an existing robot
```

## What you see

```text
  warning conditions are copied as written; rewrite them as Visual Basic expressions in Studio
Compiled plan/book-emailed-supplier-invoices-without-creating-duplicates-then-archive-the-pdf into Main.xaml
```

`Main.xaml` is a Flowchart, because the plan branches: the workflow's inputs as typed
arguments, each resolved step as an `InvokeWorkflowFile` with its arguments ready to bind, a
`FlowDecision` per condition, and a `Comment` where each missing step goes:

```xml
<x:Property Name="invoice_reference" Type="InArgument(x:String)" />
<x:Property Name="amount_eur" Type="InArgument(x:Double)" />
...
<ui:InvokeWorkflowFile DisplayName="Check that the vendor on the invoice exists in our records."
                       WorkflowFileName="Steps\ValidateVendor.xaml">
...
<ui:Comment DisplayName="Notify purchasing that the vendor is unknown and stop processing the invoice."
            Text="...: no capability does this yet" />
```

`invoice.bpmn` is BPMN 2.0 with a diagram, one `serviceTask` per resolved step, a plain `task`
per missing one, the conditions on the sequence flows, and with `--engine camunda7` or
`camunda8` what that engine needs to run it.
Both commands print what they could not carry over exactly: a condition written for another
tool's expression language is copied as written and flagged.

## What changes

One design, three readings: the IR for the tooling, BPMN for the people who own the process,
XAML for the people who build it. A coding agent with the project's activity cards
([use case 3](03-coding-agent-context.md)) fills in the missing steps from there.

## Telling it

- **Hook:** the plan from the client's document, open in Studio two commands later, with a
  comment where every missing step goes.
- **Three points:** IR to XAML and BPMN, and existing robots to BPMN; nothing silently
  approximated, every gap printed; the diagram and the Studio file come from the same checked
  workflow.
- **Demo:** compile the ReFrameWork's `Main` to BPMN and open it in a modeler; then the planned
  invoice workflow to XAML and open it in Studio.
- **Where:** the UiPath Community Forum, BPMN and Camunda communities, LinkedIn for process
  owners.
