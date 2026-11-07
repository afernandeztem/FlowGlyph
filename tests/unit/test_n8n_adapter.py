import json
from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters.n8n import N8nAdapter
from flowglyph.adapters.n8n.nodes import node_effects
from flowglyph.ir import Tri

FIXTURES = Path(__file__).parents[1] / "fixtures" / "n8n"


@pytest.fixture(scope="module")
def catalog() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES, adapter="n8n")


def test_every_workflow_in_every_export_is_read(catalog: flowglyph.Catalog):
    assert sorted(catalog.capabilities) == [
        "n8n/Invoice_intake",
        "n8n/Nightly_overdue_report",
        "n8n/Notify_customer",
    ]


def test_webhooks_are_callable_and_typed_by_method(catalog: flowglyph.Catalog):
    intake = catalog.get("n8n/Invoice_intake")
    assert intake.invocable
    assert intake.trigger is not None
    assert intake.trigger.address == "POST /webhook/invoice-intake"
    assert list(intake.input_schema["properties"]) == ["body", "query"]
    assert intake.tags == ("finance",)
    assert intake.description.startswith("Receives supplier invoices")


def test_sub_workflows_declare_inputs_and_are_called_by_id(catalog: flowglyph.Catalog):
    notify = catalog.get("n8n/Notify_customer")
    assert not notify.invocable
    assert notify.input_schema["properties"] == {
        "email": {},
        "invoiceNumber": {"type": "string"},
        "amount": {"type": "number"},
    }
    graph = catalog.workflow("n8n/Invoice_intake")
    assert graph.calls == ("n8n/Notify_customer",)
    edges = {(edge.source, edge.target): edge.condition for edge in graph.edges}
    assert edges[("Above 10k?", "Ask for approval")] == "true"
    assert edges[("Above 10k?", "Book in ERP")] == "false"
    assert edges[("Book in ERP", "Notify customer")] is None


def test_effects_come_from_operations_and_methods(catalog: flowglyph.Catalog):
    report = catalog.get("n8n/Nightly_overdue_report")
    assert report.trigger is not None
    assert (report.trigger.kind, report.trigger.address) == ("schedule", "0 2 * * *")
    assert report.effects.destructive is Tri.YES
    assert report.effects.reads is Tri.YES
    intake = catalog.get("n8n/Invoice_intake")
    assert intake.effects.mutates_state is Tri.YES
    assert intake.idempotency.mode == "none"


def test_credentials_are_named_never_valued(catalog: flowglyph.Catalog):
    assert catalog.get("n8n/Invoice_intake").configuration == (
        "httpHeaderAuth: ERP API key",
        "slackApi: Slack finance bot",
    )


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        ({"type": "n8n-nodes-base.set"}, None),
        ({"type": "n8n-nodes-base.httpRequest", "parameters": {}}, "read"),
        ({"type": "n8n-nodes-base.httpRequest", "parameters": {"method": "DELETE"}}, "delete"),
        ({"type": "n8n-nodes-base.airtable", "parameters": {"operation": "upsert"}}, "write"),
        ({"type": "n8n-nodes-base.postgres", "parameters": {"operation": "executeQuery"}}, "write"),
        ({"type": "n8n-nodes-base.code"}, "unknown"),
        ({"type": "n8n-nodes-base.slack", "disabled": True}, None),
        ({"type": "n8n-nodes-base.gmailTrigger"}, None),
    ],
)
def test_node_rules(node: dict[str, object], expected: str | None):
    effects = node_effects(node)
    if expected is None:
        assert effects is None
        return
    assert effects is not None
    observed = (
        "delete"
        if effects.destructive is Tri.YES
        else "write"
        if effects.mutates_state is Tri.YES
        else "read"
        if effects.reads is Tri.YES
        else "unknown"
    )
    assert observed == expected


def test_only_n8n_exports_are_claimed(tmp_path: Path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "x", "dependencies": {}}))
    (tmp_path / "openapi.json").write_text(json.dumps({"openapi": "3.1.0", "paths": {}}))
    assert N8nAdapter().discover(tmp_path) == []
