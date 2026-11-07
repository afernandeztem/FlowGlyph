from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters.bpmn import BpmnAdapter
from flowglyph.ir import Tri

FIXTURES = Path(__file__).parents[1] / "fixtures" / "bpmn"


@pytest.fixture(scope="module")
def catalog() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES, adapter="bpmn")


def test_processes_are_found_across_files(catalog: flowglyph.Catalog):
    assert sorted(catalog.capabilities) == [
        "bpmn/Order_Process",
        "bpmn/document_archiving",
        "bpmn/invoice_approval",
    ]
    assert BpmnAdapter().discover(FIXTURES) == [FIXTURES]


def test_start_forms_become_typed_inputs(catalog: flowglyph.Catalog):
    invoice = catalog.get("bpmn/invoice_approval")
    properties = invoice.input_schema["properties"]
    assert properties["amount"]["type"] == "integer"
    assert properties["dueDate"] == {"type": "string", "format": "date", "description": "Due date"}
    assert invoice.input_schema["required"] == ["invoiceNumber", "amount", "dueDate"]
    assert invoice.description == "Approve a supplier invoice and post it to the ERP."
    assert invoice.category == "Camunda 7"


def test_triggers_follow_the_start_event(catalog: flowglyph.Catalog):
    invoice = catalog.get("bpmn/invoice_approval")
    assert invoice.trigger is not None
    assert (invoice.trigger.kind, invoice.trigger.channel) == ("call", "Camunda 7")
    archive = catalog.get("bpmn/document_archiving")
    assert archive.trigger is not None
    assert (archive.trigger.kind, archive.trigger.address) == ("event", "ArchiveRequested")
    assert archive.category == "Camunda 8"
    order = catalog.get("bpmn/Order_Process")
    assert order.trigger is not None
    assert order.trigger.kind == "schedule"
    assert not order.invocable


def test_starting_a_process_is_never_naturally_idempotent(catalog: flowglyph.Catalog):
    for capability in catalog:
        assert capability.effects.mutates_state is Tri.YES
        assert capability.idempotency.mode == "none"


def test_the_graph_keeps_conditions_defaults_boundaries_and_calls(catalog: flowglyph.Catalog):
    graph = catalog.workflow("bpmn/invoice_approval")
    edges = {(edge.source, edge.target): edge.condition for edge in graph.edges}
    assert edges[("needs_approval", "approve")] == "${amount > 10000}"
    assert edges[("needs_approval", "post_invoice")] == "otherwise"
    assert edges[("post_invoice", "notify_requester")] == "on error: Posting failed"
    assert graph.calls == ("bpmn/document_archiving",)
    nodes = {node.id: node for node in graph.nodes}
    assert nodes["post_invoice"].join == "any"
    assert "external task erp-post-invoice" in nodes["post_invoice"].label
    assert nodes["archive"].capability == "bpmn/document_archiving"


def test_effects_travel_along_call_activities(catalog: flowglyph.Catalog):
    archive = catalog.get("bpmn/document_archiving")
    invoice = catalog.get("bpmn/invoice_approval")
    assert archive.effects.external is Tri.YES
    assert invoice.effects.reads is Tri.YES
    assert invoice.effects.destructive is Tri.UNKNOWN


def test_design_problems_are_reported(catalog: flowglyph.Catalog):
    messages = [d.message for d in catalog.diagnostics]
    assert any("'Notify requester' has no implementation" in m for m in messages)
    order = catalog.workflow("bpmn/Order_Process")
    assert [edge.condition for edge in order.edges] == ["on conditional: Archive invoice?"]


def test_unknown_called_processes_are_unresolved(tmp_path: Path):
    source = (FIXTURES / "invoices" / "invoice-approval.bpmn").read_text(encoding="utf-8")
    (tmp_path / "only.bpmn").write_text(source, encoding="utf-8")
    catalog = flowglyph.extract(tmp_path, adapter="bpmn")
    assert catalog.workflow("bpmn/invoice_approval").unresolved_calls == ("document_archiving",)
    assert any("not in the sources" in d.message for d in catalog.diagnostics)
