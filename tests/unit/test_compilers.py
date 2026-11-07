"""Compiled documents open in their tools and read back into the same workflow."""

import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

import flowglyph
from flowglyph._internal.xml import parse_xml
from flowglyph.compilers import compile_workflow, load_planned
from flowglyph.ir import Edge, Workflow

FIXTURES = Path(__file__).parents[1] / "fixtures"
EXAMPLES = Path(__file__).parents[2] / "examples"
BPMN = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
ACTIVITIES = "{http://schemas.microsoft.com/netfx/2009/xaml/activities}"
UI = "{http://schemas.uipath.com/workflow/activities}"
X = "{http://schemas.microsoft.com/winfx/2006/xaml}"


@pytest.fixture(scope="module")
def processes() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES / "bpmn", adapter="bpmn")


@pytest.fixture(scope="module")
def robots() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES / "synthetic" / "invoices")


def _parse(text: str) -> ET.Element:
    return parse_xml(text.encode(), "compiled")


def _edges(workflow: Workflow) -> set[tuple[str, str, str | None]]:
    return {(edge.source, edge.target, edge.condition) for edge in workflow.edges}


def test_bpmn_round_trips_through_the_bpmn_adapter(processes: flowglyph.Catalog, tmp_path: Path):
    original = processes.workflow("bpmn/invoice_approval")
    compiled = compile_workflow(
        original, processes.get("bpmn/invoice_approval"), to="bpmn", catalog=processes
    )
    (tmp_path / "compiled.bpmn").write_text(compiled.text, encoding="utf-8")
    shutil.copy(FIXTURES / "bpmn" / "invoices" / "document-archiving.bpmn", tmp_path)
    again = flowglyph.extract(tmp_path, adapter="bpmn").workflow("bpmn/invoice_approval")
    assert _edges(again) == _edges(original)
    assert again.calls == original.calls
    assert {n.id: n.join for n in again.nodes} == {n.id: n.join for n in original.nodes}
    root = _parse(compiled.text)
    call = root.find(f".//{BPMN}callActivity")
    assert call is not None
    assert call.get("calledElement") == "document_archiving"


def test_a_uipath_workflow_becomes_a_deployable_camunda_8_process(
    robots: flowglyph.Catalog, tmp_path: Path
):
    main = robots.workflow("uipath/Invoices/Main")
    compiled = compile_workflow(
        main, robots.get("uipath/Invoices/Main"), to="bpmn", catalog=robots, engine="camunda8"
    )
    assert "conditions are copied as written" in compiled.warnings[0]
    (tmp_path / "main.bpmn").write_text(compiled.text, encoding="utf-8")
    catalog = flowglyph.extract(tmp_path, adapter="bpmn")
    assert not [d for d in catalog.diagnostics if "no implementation" in d.message]
    again = catalog.workflow("bpmn/uipath_Invoices_Main")
    edges = _edges(again)
    assert ("If_1", "Invoke_2", "amount > in_Threshold") in edges
    assert ("If_1", "Invoke_3", "otherwise") in edges
    labels = {node.id: node.label for node in again.nodes}
    assert labels["Invoke_1"] == "Validate vendor (job uipath/Invoices/Steps/ValidateVendor)"
    assert labels["Invoke_4"] == "Archive (job archive)"


def test_camunda_7_uses_external_task_topics(robots: flowglyph.Catalog):
    main = robots.workflow("uipath/Invoices/Main")
    compiled = compile_workflow(
        main, robots.get("uipath/Invoices/Main"), to="bpmn", catalog=robots, engine="camunda7"
    )
    root = _parse(compiled.text)
    topics = {
        task.get("{http://camunda.org/schema/1.0/bpmn}topic")
        for task in root.iter(f"{BPMN}serviceTask")
    }
    assert "uipath/Invoices/Steps/BookInvoice" in topics


def test_steps_that_wait_for_all_get_a_parallel_join(robots: flowglyph.Catalog):
    capability = robots.get("uipath/Invoices/Main")
    graph = robots.workflow("uipath/Invoices/Main")
    waiting = Workflow(
        id=graph.id,
        capability=graph.capability,
        nodes=tuple(
            n.model_copy(update={"join": "all"}) if n.id == "Invoke_3" else n for n in graph.nodes
        ),
        edges=graph.edges,
    )
    root = _parse(compile_workflow(waiting, capability, to="bpmn").text)
    join = root.find(f".//{BPMN}parallelGateway")
    assert join is not None
    flows = [(f.get("sourceRef"), f.get("targetRef")) for f in root.iter(f"{BPMN}sequenceFlow")]
    assert (join.get("id"), "Invoke_3") in flows


def test_compiled_bpmn_has_a_diagram_for_every_element(processes: flowglyph.Catalog):
    compiled = compile_workflow(
        processes.workflow("bpmn/Order_Process"), processes.get("bpmn/Order_Process"), to="bpmn"
    )
    root = _parse(compiled.text)
    process = root.find(f"{BPMN}process")
    assert process is not None
    flow_nodes = [child.get("id") for child in process if child.tag != f"{BPMN}documentation"]
    shapes = {
        shape.get("bpmnElement")
        for shape in root.iter("{http://www.omg.org/spec/BPMN/20100524/DI}BPMNShape")
    }
    edges = {
        edge.get("bpmnElement")
        for edge in root.iter("{http://www.omg.org/spec/BPMN/20100524/DI}BPMNEdge")
    }
    assert set(flow_nodes) == shapes | edges


def _references(root: ET.Element) -> dict[str, ET.Element]:
    return {
        element.get(f"{X}Name", ""): element for element in root.iter() if element.get(f"{X}Name")
    }


def _target(element: ET.Element, slot: str) -> str:
    reference = element.find(f"{ACTIVITIES}{slot}/{X}Reference")
    assert reference is not None
    return reference.text or ""


def test_a_branching_workflow_becomes_a_flowchart(robots: flowglyph.Catalog):
    main = robots.workflow("uipath/Invoices/Main")
    compiled = compile_workflow(main, robots.get("uipath/Invoices/Main"), to="xaml", catalog=robots)
    root = _parse(compiled.text)
    nodes = _references(root)
    chart = root.find(f"{ACTIVITIES}Flowchart")
    assert chart is not None
    start = nodes[_target(chart, "Flowchart.StartNode")]
    invoke = start.find(f"{UI}InvokeWorkflowFile")
    assert invoke is not None
    assert invoke.get("WorkflowFileName") == "Steps\\ValidateVendor.xaml"
    decision = nodes[_target(start, "FlowStep.Next")]
    assert decision.get("Condition") == "[amount > in_Threshold]"
    approval = nodes[_target(decision, "FlowDecision.True")]
    booking = nodes[_target(decision, "FlowDecision.False")]
    assert _target(approval, "FlowStep.Next") == booking.get(f"{X}Name")
    arguments = booking.find(f".//{ACTIVITIES}InArgument")
    assert arguments is not None
    assert arguments.get(f"{X}Key") == "in_Invoice"
    members = [p.get("Type") for p in root.iter(f"{X}Property")]
    assert members == ["InArgument(x:String)", "InArgument(x:Decimal)", "OutArgument(x:String)"]
    assert root.get(f"{X}Class") == "Main"


def test_compiled_xaml_reads_back_with_the_same_calls(robots: flowglyph.Catalog, tmp_path: Path):
    project = shutil.copytree(FIXTURES / "synthetic" / "invoices", tmp_path / "invoices")
    main = robots.workflow("uipath/Invoices/Main")
    compiled = compile_workflow(main, robots.get("uipath/Invoices/Main"), to="xaml", catalog=robots)
    (project / "Compiled.xaml").write_text(compiled.text, encoding="utf-8")
    catalog = flowglyph.extract(project)
    again = catalog.workflow("uipath/Invoices/Compiled")
    assert again.calls == tuple(call for call in main.calls)
    assert not [d for d in catalog.diagnostics if d.level == "error"]


def test_a_straight_line_becomes_a_sequence(robots: flowglyph.Catalog, tmp_path: Path):
    main = robots.workflow("uipath/Invoices/Main")
    line = Workflow(
        id="plan/x",
        capability="plan/x",
        nodes=tuple(n for n in main.nodes if n.id in {"Invoke_1", "Invoke_3"}),
        edges=(Edge(source="Invoke_1", target="Invoke_3"),),
    )
    compiled = compile_workflow(line, robots.get("uipath/Invoices/Main"), to="xaml", catalog=robots)
    root = _parse(compiled.text)
    sequence = root.find(f"{ACTIVITIES}Sequence")
    assert sequence is not None
    names = [child.get("WorkflowFileName") for child in sequence]
    assert names == ["Steps\\ValidateVendor.xaml", "Steps\\BookInvoice.xaml"]
    assert compiled.warnings == ()


def test_planned_workflows_compile_with_their_inputs():
    capability, workflow = load_planned(
        EXAMPLES / "invoice-processing" / "out" / "workflow.ir.yaml"
    )
    catalog = flowglyph.load_catalog(EXAMPLES / "invoice-processing" / "catalog")
    xaml = compile_workflow(workflow, capability, to="xaml", catalog=catalog)
    root = _parse(xaml.text)
    members = {p.get("Name") for p in root.iter(f"{X}Property")}
    assert {"vendor_id", "amount", "invoice_reference"} <= members
    comments = [c.get("Text", "") for c in root.iter(f"{UI}Comment")]
    assert any("call openapi/Payments_API/createInvoice" in text for text in comments)
    bpmn = compile_workflow(workflow, capability, to="bpmn", catalog=catalog, engine="camunda8")
    assert _parse(bpmn.text).find(f"{BPMN}process") is not None


def test_compiling_is_deterministic(processes: flowglyph.Catalog):
    graph = processes.workflow("bpmn/invoice_approval")
    capability = processes.get("bpmn/invoice_approval")
    first = compile_workflow(graph, capability, to="bpmn", catalog=processes)
    assert compile_workflow(graph, capability, to="bpmn", catalog=processes) == first
