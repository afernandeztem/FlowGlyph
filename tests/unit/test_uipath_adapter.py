from pathlib import Path

from flowglyph.adapters.uipath import UiPathAdapter
from flowglyph.ir import Tri


def extract(path: Path):
    return UiPathAdapter().extract(path)


def test_arguments_become_typed_schemas(synthetic: Path):
    capability = next(
        c for c in extract(synthetic / "invoices").capabilities if c.id == "uipath/Invoices/Main"
    )
    inputs = {parameter.name: parameter for parameter in capability.inputs}
    assert inputs["in_InvoicePath"].type == "string"
    assert inputs["in_InvoicePath"].required
    assert inputs["in_InvoicePath"].description == "Path of the invoice PDF."
    assert inputs["in_Threshold"].type == "number"
    assert not inputs["in_Threshold"].required, "arguments with a default are optional"
    assert [parameter.name for parameter in capability.outputs] == ["out_InvoiceId"]
    assert capability.input_schema["additionalProperties"] is False
    assert "entry-point" in capability.tags


def test_graph_keeps_invocations_and_branches(synthetic: Path):
    extraction = extract(synthetic / "invoices")
    workflow = next(w for w in extraction.workflows if w.id == "uipath/Invoices/Main")
    labels = [node.label for node in workflow.nodes]
    assert labels == [
        "Validate vendor",
        "If amount > in_Threshold",
        "Request approval",
        "Book invoice",
        "Archive",
    ]
    assert "Start" not in labels, "pure logging is folded away"
    conditions = {(edge.source, edge.target): edge.condition for edge in workflow.edges}
    assert conditions[("If_1", "Invoke_2")] == "amount > in_Threshold"
    assert conditions[("If_1", "Invoke_3")] is None, "an empty Else falls through"
    assert conditions[("Invoke_2", "Invoke_3")] is None
    assert workflow.calls == (
        "uipath/Invoices/Steps/ValidateVendor",
        "uipath/Invoices/Steps/RequestApproval",
        "uipath/Invoices/Steps/BookInvoice",
    )
    assert workflow.unresolved_calls == ("Steps/Missing.xaml",)
    assert workflow.entry is not None
    assert workflow.entry.label == "Validate vendor"


def test_effects_propagate_through_invocations(synthetic: Path):
    capabilities = {c.id: c for c in extract(synthetic / "invoices").capabilities}
    validate = capabilities["uipath/Invoices/Steps/ValidateVendor"]
    main = capabilities["uipath/Invoices/Main"]
    assert not validate.effects.has_side_effects
    assert validate.idempotency.mode == "natural"
    assert main.effects.mutates_state is Tri.YES, "inherited from SendMail and AddQueueItem"
    assert main.idempotency.mode == "none"


def test_activity_types_document_observed_parameters(synthetic: Path):
    capabilities = {c.id: c for c in extract(synthetic / "invoices").capabilities}
    send_mail = capabilities["uipath/activity/SendMail"]
    assert send_mail.kind == "activity"
    assert not send_mail.invocable
    assert send_mail.category == "integration.mail"
    assert set(send_mail.input_schema["properties"]) == {"To", "Subject"}
    assert send_mail.input_schema["properties"]["To"]["examples"] == ["[in_Approver]"]


def test_problems_are_reported_not_raised(synthetic: Path, tmp_path: Path):
    for name in ("not-a-workflow.xaml", "doctype.xaml"):
        (tmp_path / name).write_bytes((synthetic / name).read_bytes())
    extraction = extract(tmp_path)
    levels = {d.artifact: d.level for d in extraction.diagnostics}
    assert levels == {"doctype.xaml": "error", "not-a-workflow.xaml": "info"}
    assert not extraction.capabilities


def test_unresolved_invocations_are_diagnosed(synthetic: Path):
    messages = [d.message for d in extract(synthetic / "invoices").diagnostics]
    assert "invoked workflow not found in the project: Steps/Missing.xaml" in messages


def test_dynamic_invocations_are_explained(reframework: Path):
    messages = [d.message for d in extract(reframework).diagnostics]
    assert any("chosen at runtime" in message for message in messages)
