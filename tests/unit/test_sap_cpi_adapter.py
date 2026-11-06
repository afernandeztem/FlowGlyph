import shutil
import zipfile
from itertools import pairwise
from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters import detect_adapter
from flowglyph.adapters.sap_cpi import SapCpiAdapter
from flowglyph.adapters.sap_cpi.bundle import read_zip
from flowglyph.catalog import Catalog
from flowglyph.errors import AdapterError
from flowglyph.ir import Tri

ORDERS = "sap-cpi/Orders_Inbound"
NOTIFY = "sap-cpi/Notify_Customer"
REPORT = "sap-cpi/Nightly_Stock_Report"


@pytest.fixture
def cpi(synthetic: Path) -> Path:
    return synthetic.parent / "sap-cpi"


@pytest.fixture
def own(cpi: Path, tmp_path: Path) -> Path:
    root = tmp_path / "landscape"
    for name in ("orders", "notify", "nightly-report"):
        shutil.copytree(cpi / name, root / name)
    return root


@pytest.fixture
def catalog(own: Path) -> Catalog:
    return flowglyph.extract(own, adapter="sap-cpi")


def zip_folder(folder: Path, target: Path) -> Path:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(folder).as_posix())
    return target


def test_each_endpoint_is_a_capability(catalog: Catalog):
    orders = catalog.get(ORDERS)
    assert orders.invocable
    assert orders.title == "Orders Inbound"
    assert orders.source.artifact_version == "1.2.0"
    assert orders.input_schema["properties"]["body"]["x-endpoint"] == "/orders"
    assert orders.security.scopes == ("ESBMessaging.send",)
    assert orders.trigger is not None
    assert (orders.trigger.kind, orders.trigger.channel, orders.trigger.address) == (
        "call",
        "HTTPS",
        "/orders",
    )
    report = catalog.get(REPORT)
    assert not report.invocable, "a timer cannot be called on demand"
    assert report.trigger is not None
    assert report.trigger.kind == "schedule"


def test_idempotency_declared_by_the_iflow_wins(catalog: Catalog):
    orders = catalog.get(ORDERS).idempotency
    assert (orders.mode, orders.provenance, orders.key_fields) == (
        "key",
        "declared",
        ("${header.OrderNumber}",),
    )
    notify = catalog.get(NOTIFY)
    assert notify.idempotency.mode == "conditional"
    assert "Data Store" in notify.notes[0]
    assert catalog.get(REPORT).idempotency.mode == "natural"


def test_effects_come_from_receivers_steps_and_called_iflows(catalog: Catalog):
    report = catalog.get(REPORT).effects
    assert (report.reads, report.mutates_state) == (Tri.YES, Tri.NO), "a GET only reads"
    notify = catalog.get(NOTIFY).effects
    assert notify.mutates_state is Tri.YES, "sending mail and writing the Data Store"
    assert catalog.workflow(ORDERS).calls == (NOTIFY,), "ProcessDirect from a message end event"
    assert catalog.get(ORDERS).effects.mutates_state is Tri.YES


def test_the_graph_keeps_decisions_and_calls(catalog: Catalog):
    workflow = catalog.workflow(ORDERS)
    labels = {node.id: node.label for node in workflow.nodes}
    assert "CallActivity_Keep" not in labels, "message shaping steps are folded away"
    assert labels["ServiceTask_Book"] == "Book in ERP (HTTP POST {{ERP_URL}}/orders)"
    conditions = {(e.source, e.target): e.condition for e in workflow.edges}
    assert (
        conditions[("ExclusiveGateway_Type", "ServiceTask_Book")] == "${header.OrderType} = 'STD'"
    )
    book = next(node for node in workflow.nodes if node.id == "ServiceTask_Book")
    assert book.join == "any", "both branches lead to the booking"
    ran = workflow.simulate(lambda condition: condition.endswith("'STD'"))
    assert "ServiceTask_Book" in ran
    assert "ServiceTask_Stock" not in ran


def test_design_findings(own: Path):
    extraction = SapCpiAdapter().extract(own)
    found = {(d.artifact.split("/")[0], d.level, d.message) for d in extraction.diagnostics}
    expected = {
        ("orders", "warning", "HTTP receiver uses plain HTTP: http://legacy.example.com/stock"),
        (
            "orders",
            "warning",
            "HTTP receiver http://legacy.example.com/stock has no request timeout",
        ),
        ("orders", "warning", "router 'Order type' has no default route"),
        (
            "orders",
            "warning",
            "'Keep original order' copies the whole body into a property, doubling memory",
        ),
        ("orders", "info", "CSRF protection is off on endpoint /orders"),
        (
            "orders",
            "info",
            "HTTP receiver address is hard-coded; externalize http://legacy.example.com/stock",
        ),
        (
            "notify",
            "warning",
            "the main process has no exception subprocess: a failure ends unhandled",
        ),
    }
    assert found == expected


def test_parameter_values_never_leave_the_bundle(catalog: Catalog, tmp_path: Path):
    orders = catalog.get(ORDERS)
    assert {"ERP_URL", "ERP_Credential"} <= set(orders.configuration)
    catalog.save(tmp_path / "out")
    for file in (tmp_path / "out").rglob("*"):
        if file.is_file():
            assert "TOP_SECRET" not in file.read_text(encoding="utf-8"), file


def test_exported_zips_are_read_without_extracting(cpi: Path, tmp_path: Path):
    zip_folder(cpi / "notify", tmp_path / "Notify_Customer.zip")
    capabilities = {c.id for c in SapCpiAdapter().extract(tmp_path).capabilities}
    assert capabilities == {NOTIFY}
    assert detect_adapter(tmp_path / "Notify_Customer.zip").name == "sap-cpi"


def test_hostile_archives_are_refused(tmp_path: Path):
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF", "SAP-BundleType: IntegrationFlow\n")
        archive.writestr("src/flow.iflw", "<a>" + " " * 30_000_000 + "</a>")
    with pytest.raises(AdapterError, match="too large"):
        read_zip(bomb, "bomb.zip")


def test_other_artifacts_are_skipped(tmp_path: Path):
    with zipfile.ZipFile(tmp_path / "Mapping.zip", "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "SAP-BundleType: MessageMapping\n")
    extraction = SapCpiAdapter().extract(tmp_path)
    assert not extraction.capabilities
    assert extraction.diagnostics[0].message == "MessageMapping, not an integration flow"


def test_real_sap_iflows(cpi: Path):
    catalog = flowglyph.extract(cpi / "btp-spend-analysis", adapter="sap-cpi")
    chain = [f"sap-cpi/AribaProcure_Step{i}" for i in range(6)]
    assert sorted(c.id for c in catalog) == chain
    calls = {w.id: set(w.calls) for w in catalog.workflows.values()}
    for caller, callee in pairwise(chain):
        assert callee in calls[caller], f"{caller} hands over to {callee}"
    assert not catalog.get(chain[0]).invocable, "the chain starts on a timer"
    flagged = {
        d.artifact.rsplit("/", 1)[-1]
        for d in catalog.diagnostics
        if "exception subprocess" in d.message
    }
    assert "AribaProcure_Step1.zip" not in flagged
    assert len(flagged) == 5


def test_cpi_sits_next_to_every_other_source(own: Path, synthetic: Path):
    shutil.copytree(synthetic / "invoices", own / "rpa")
    shutil.copytree(synthetic.parent / "sap", own / "odata")
    catalog = flowglyph.extract(own)
    assert {c.source.provider for c in catalog} == {"sap-cpi", "uipath", "sap"}


def test_design_findings_reach_the_wiki(catalog: Catalog, tmp_path: Path):
    from flowglyph import wiki  # noqa: PLC0415

    assert "warning: router 'Order type' has no default route" in catalog.get(ORDERS).notes
    wiki.build_wiki(catalog, tmp_path / "wiki")
    messages = {(i.level, i.message) for i in wiki.lint_wiki(tmp_path / "wiki")}
    assert ("warning", "router 'Order type' has no default route") in messages
    assert ("info", "CSRF protection is off on endpoint /orders") in messages
