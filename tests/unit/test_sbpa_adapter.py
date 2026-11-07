import io
import zipfile
from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters.sbpa import SapBuildProcessAutomationAdapter
from flowglyph.adapters.sbpa.package import read_mtar
from flowglyph.errors import AdapterError
from flowglyph.ir import Tri

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sbpa"
PROJECT = "sbpa/Invoice_Approval_Process_-_Sample_Copy_2"


@pytest.fixture(scope="module")
def catalog() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES, adapter="sbpa")


def test_processes_automations_and_decisions_are_read(catalog: flowglyph.Catalog):
    kinds = {capability.id.rsplit("/", 1)[-1]: capability.kind for capability in catalog}
    assert kinds == {
        "getInvoiceDetails": "workflow",
        "extractInvoiceData": "workflow",
        "determineApprover": "operation",
    }


def test_the_start_form_gives_the_process_its_inputs(catalog: flowglyph.Catalog):
    process = catalog.get(f"{PROJECT}/getInvoiceDetails")
    assert process.input_schema["required"] == ["employeeName", "filePath", "currentDate"]
    assert process.input_schema["properties"]["currentDate"] == {
        "description": "Current Date",
        "type": "string",
        "format": "date",
    }
    assert process.trigger is not None
    assert (process.trigger.channel, process.trigger.address) == (
        "SAP Build form",
        "Invoice Request Form",
    )
    assert not process.invocable
    assert process.effects.mutates_state is Tri.YES
    assert process.idempotency.mode == "none"


def test_the_graph_runs_automations_decisions_and_forms(catalog: flowglyph.Catalog):
    graph = catalog.workflow(f"{PROJECT}/getInvoiceDetails")
    assert graph.calls == (f"{PROJECT}/extractInvoiceData", f"{PROJECT}/determineApprover")
    labels = sorted(node.label for node in graph.nodes)
    assert "Invoice Approval Form (form)" in labels
    conditions = sorted(edge.condition for edge in graph.edges if edge.condition)
    assert conditions == [
        '${usertasks.form_invoiceApprovalForm_1.last.decision == "approve"}',
        '${usertasks.form_invoiceApprovalForm_1.last.decision == "reject"}',
    ]
    automation = catalog.get(f"{PROJECT}/extractInvoiceData")
    assert automation.used_in == ("Get Invoice Details",)
    assert automation.input_schema["properties"]["FilePath"]["type"] == "string"
    assert catalog.get(f"{PROJECT}/determineApprover").effects.has_side_effects is False


def test_non_project_archives_are_ignored(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("META-INF/mtad.yaml", "ID: some.cap.app\nmodules: []\n")
    (tmp_path / "app.mtar").write_bytes(buffer.getvalue())
    assert SapBuildProcessAutomationAdapter().discover(tmp_path) == []


def test_zip_bombs_are_refused(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/mtad.yaml", "type: com.sap.lobby.content\n")
        archive.writestr("x/content.zip", b"\0" * 30_000_000)
    bomb = tmp_path / "bomb.mtar"
    bomb.write_bytes(buffer.getvalue())
    with pytest.raises(AdapterError, match="too large"):
        read_mtar(bomb, "bomb.mtar")
