import shutil
from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters import detect_adapter
from flowglyph.adapters.sap import SapODataAdapter
from flowglyph.ir import Capability, Tri
from flowglyph.views import effects_code

V2 = "sap/ZSUPPLIER_INVOICE_SRV"
V4 = "sap/zbusinesspartner"


@pytest.fixture
def sap(synthetic: Path) -> Path:
    return synthetic.parent / "sap"


@pytest.fixture
def capabilities(sap: Path) -> dict[str, Capability]:
    return {c.id: c for c in SapODataAdapter().extract(sap).capabilities}


def test_only_operations_the_service_allows_are_generated(capabilities: dict[str, Capability]):
    invoice = {i.rsplit("/", 1)[-1] for i in capabilities if i.startswith(f"{V2}/SupplierInvoice/")}
    assert invoice == {"query", "read", "create", "update"}, "sap:deletable=false"
    supplier = {i.rsplit("/", 1)[-1] for i in capabilities if i.startswith(f"{V2}/Supplier/")}
    assert supplier == {"query", "read"}, "read-only entity set"
    partner = {i.rsplit("/", 1)[-1] for i in capabilities if i.startswith(f"{V4}/BusinessPartner/")}
    assert "delete" not in partner, "V4 DeleteRestrictions"
    assert "block" in partner


@pytest.mark.parametrize(
    ("name", "mode", "effects"),
    [
        (f"{V2}/SupplierInvoice/query", "natural", "RX"),
        (f"{V2}/SupplierInvoice/read", "natural", "RX"),
        (f"{V2}/SupplierInvoice/create", "none", "WX"),
        (f"{V2}/SupplierInvoice/update", "natural", "WdX"),
        (f"{V2}/GetDuplicateCandidates", "natural", "RX"),
        (f"{V2}/Release", "none", "rwdX"),
        (f"{V4}/checkDuplicates", "natural", "RX"),
        (f"{V4}/BusinessPartner/block", "none", "rwdX"),
    ],
)
def test_odata_semantics(capabilities: dict[str, Capability], name: str, mode: str, effects: str):
    assert capabilities[name].idempotency.mode == mode
    assert effects_code(capabilities[name].effects) == effects


def test_keys_types_and_labels(capabilities: dict[str, Capability]):
    read = capabilities[f"{V2}/SupplierInvoice/read"]
    assert [(p.name, p.required) for p in read.inputs] == [
        ("SupplierInvoice", True),
        ("FiscalYear", True),
    ]
    assert read.input_schema["properties"]["SupplierInvoice"]["maxLength"] == 10
    output = read.output_schema["properties"]
    assert output["InvoiceGrossAmount"]["type"] == "number"
    assert output["PostingDate"]["format"] == "date-time"
    assert output["InvoicingParty"]["description"] == "Supplier"
    supplier = capabilities[f"{V2}/Supplier/read"].output_schema["properties"]
    assert supplier["SupplierID"]["format"] == "uuid"


def test_create_bodies_leave_out_generated_fields(capabilities: dict[str, Capability]):
    create = capabilities[f"{V2}/SupplierInvoice/create"]
    body = create.input_schema["properties"]["body"]
    assert "SupplierInvoice" not in body["properties"], "sap:creatable=false"
    assert "IsBlocked" not in body["properties"]
    assert body["required"] == ["CompanyCode", "InvoicingParty"]
    assert create.notes and "idempotency key" in create.notes[0]


def test_bound_actions_take_the_entity_key(capabilities: dict[str, Capability]):
    block = capabilities[f"{V4}/BusinessPartner/block"]
    assert [(p.name, p.required) for p in block.inputs] == [
        ("BusinessPartner", True),
        ("Reason", True),
    ]
    assert "action" in block.tags
    returns = capabilities[f"{V4}/checkDuplicates"].output_schema["properties"]["value"]
    assert returns["type"] == "array"


def test_metadata_and_traceability(capabilities: dict[str, Capability]):
    create = capabilities[f"{V2}/SupplierInvoice/create"]
    assert create.source.provider == "sap"
    assert create.source.location == "ZSUPPLIER_INVOICE_SRV.edmx#SupplierInvoice/create"
    assert create.source.artifact == "POST SupplierInvoice"
    assert create.category == "ZSUPPLIER_INVOICE_SRV"
    assert create.trigger is not None
    assert create.trigger.channel == "OData V2"
    assert create.trigger.address == "POST SupplierInvoice"
    assert capabilities[f"{V4}/checkDuplicates"].effects.destructive is Tri.NO


def test_detection(sap: Path, synthetic: Path):
    assert SapODataAdapter().detect(sap / "ZSUPPLIER_INVOICE_SRV.edmx")
    assert detect_adapter(sap / "zbusinesspartner_v4.xml").name == "sap"
    assert not SapODataAdapter().detect(synthetic / "invoices")


def test_metadata_saved_from_a_browser_is_found(sap: Path, tmp_path: Path):
    shutil.copy(sap / "ZSUPPLIER_INVOICE_SRV.edmx", tmp_path / "$metadata")
    extraction = SapODataAdapter().extract(tmp_path)
    assert f"{V2}/Supplier/read" in {c.id for c in extraction.capabilities}


def test_the_same_service_in_v2_and_v4_stays_apart(sap: Path, tmp_path: Path):
    v2 = (sap / "ZSUPPLIER_INVOICE_SRV.edmx").read_text()
    v4 = (
        (sap / "zbusinesspartner_v4.xml")
        .read_text()
        .replace('Namespace="zbusinesspartner"', 'Namespace="ZSUPPLIER_INVOICE_SRV"')
    )
    (tmp_path / "v2.edmx").write_text(v2)
    (tmp_path / "v4.xml").write_text(v4)
    ids = {c.id for c in SapODataAdapter().extract(tmp_path).capabilities}
    assert f"{V2}.v2/SupplierInvoice/create" in ids
    assert f"{V2}.v4/BusinessPartner/read" in ids


def test_undeclared_sap_namespaces_are_tolerated(sap: Path, tmp_path: Path):
    text = (sap / "ZSUPPLIER_INVOICE_SRV.edmx").read_text()
    text = text.replace(' xmlns:sap="http://www.sap.com/Protocols/SAPData"', "", 1)
    (tmp_path / "sloppy.edmx").write_text(text)
    extraction = SapODataAdapter().extract(tmp_path)
    assert f"{V2}/Supplier/read" in {c.id for c in extraction.capabilities}
    assert [d.level for d in extraction.diagnostics] == ["info"]
    assert not {c.id for c in extraction.capabilities} & {f"{V2}/Supplier/create"}, (
        "sap:creatable is still honoured"
    )


def test_sap_sits_next_to_other_sources(sap: Path, synthetic: Path, tmp_path: Path):
    shutil.copytree(sap, tmp_path / "sap")
    shutil.copytree(synthetic / "invoices", tmp_path / "rpa" / "invoices")
    catalog = flowglyph.extract(tmp_path)
    assert {c.source.provider for c in catalog} == {"sap", "uipath"}
    only_sap = flowglyph.extract(tmp_path, adapter="sap")
    assert {c.source.provider for c in only_sap} == {"sap"}
    assert (
        only_sap.search("supplier invoice duplicates", limit=1)[0].id
        == f"{V2}/GetDuplicateCandidates"
    )


def test_actions_bind_to_their_own_set_and_to_whole_sets(sap: Path, tmp_path: Path):
    metadata = (sap / "zbusinesspartner_v4.xml").read_text()
    extra = """
      <EntityType Name="PreferredBusinessPartnerType">
        <Key><PropertyRef Name="Rank"/></Key>
        <Property Name="Rank" Type="Edm.Int32" Nullable="false"/>
      </EntityType>
      <Action Name="recount" IsBound="true">
        <Parameter Name="it" Type="Collection(zbusinesspartner.BusinessPartnerType)"/>
      </Action>
"""
    metadata = metadata.replace("<EntityContainer", extra + "<EntityContainer", 1)
    metadata = metadata.replace(
        "<EntitySet ",
        '<EntitySet Name="Preferred" EntityType="zbusinesspartner.PreferredBusinessPartnerType"/>'
        "\n<EntitySet ",
        1,
    )
    (tmp_path / "service.xml").write_text(metadata)
    found = {c.id.split("/", 2)[-1]: c for c in SapODataAdapter().extract(tmp_path).capabilities}
    assert "BusinessPartner/block" in found
    assert "Preferred/block" not in found
    assert [p.name for p in found["BusinessPartner/recount"].inputs] == []
