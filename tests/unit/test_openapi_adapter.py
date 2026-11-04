from pathlib import Path

import pytest

import flowglyph
from flowglyph.adapters import detect_adapter
from flowglyph.adapters.openapi import OpenAPIAdapter
from flowglyph.adapters.openapi.refs import RefResolver
from flowglyph.ir import Capability, Tri


@pytest.fixture
def openapi(synthetic: Path) -> Path:
    return synthetic.parent / "openapi"


@pytest.fixture
def payments(openapi: Path) -> dict[str, Capability]:
    extraction = OpenAPIAdapter().extract(openapi / "payments.yaml")
    return {capability.title: capability for capability in extraction.capabilities}


def test_detection(openapi: Path, reframework: Path):
    assert OpenAPIAdapter().detect(openapi / "payments.yaml")
    assert OpenAPIAdapter().detect(openapi / "inventory.json")
    assert not OpenAPIAdapter().detect(openapi / "notes.yaml")
    assert not OpenAPIAdapter().detect(reframework)
    assert detect_adapter(openapi / "payments.yaml").name == "openapi"


@pytest.mark.parametrize(
    ("operation", "mode", "effects"),
    [
        ("listInvoices", "natural", "RX"),
        ("getInvoice", "natural", "RX"),
        ("replaceInvoice", "natural", "rWdX"),
        ("deleteInvoice", "natural", "WDX"),
        ("createInvoice", "key", "rWX"),
        ("executePayment", "none", "rWX"),
    ],
)
def test_http_semantics(payments: dict[str, Capability], operation: str, mode: str, effects: str):
    capability = payments[operation]
    assert capability.idempotency.mode == mode
    assert capability.effects.code() == effects


def test_idempotency_key_header_is_the_key_field(payments: dict[str, Capability]):
    create = payments["createInvoice"]
    assert create.idempotency.key_fields == ("Idempotency-Key",)
    assert create.input_schema["properties"]["Idempotency-Key"]["x-in"] == "header"


def test_inputs_merge_parameters_and_body(payments: dict[str, Capability]):
    create = payments["createInvoice"]
    assert {p.name: p.required for p in create.inputs} == {"Idempotency-Key": True, "body": True}
    body = create.input_schema["properties"]["body"]
    assert body["required"] == ["vendor", "amount", "currency", "reference"]
    get = payments["getInvoice"]
    invoice_id = get.input_schema["properties"]["invoiceId"]
    assert invoice_id["x-in"] == "path"
    assert invoice_id["description"] == "Identifier of the invoice."
    assert get.inputs[0].required, "path parameters are always required"


def test_recursive_schemas_are_cut(payments: dict[str, Capability]):
    body = payments["getInvoice"].output_schema["properties"]["body"]
    replaces = body["allOf"][1]["properties"]["replaces"]
    assert replaces == {"type": "object", "x-recursive-ref": "#/components/schemas/Invoice"}


def test_security_errors_and_tags(payments: dict[str, Capability]):
    assert payments["listInvoices"].security.scopes == ("invoices:read",), "global security"
    assert payments["deleteInvoice"].security.scopes == ("invoices:delete",)
    assert payments["createInvoice"].errors == (
        "400: The request is invalid.",
        "409: An invoice with this reference already exists.",
    )
    assert "deprecated" in payments["executePayment"].tags
    assert payments["executePayment"].category == "payments"


def test_metadata_and_traceability(payments: dict[str, Capability]):
    create = payments["createInvoice"]
    assert create.id == "openapi/Payments_API/createInvoice"
    assert create.kind == "operation"
    assert create.description.startswith("Create a supplier invoice\n\nBooks the invoice")
    assert create.source.location == "payments.yaml#/paths/~1invoices/post"
    assert create.source.artifact_version == "2.3.0"


def test_problems_become_diagnostics(openapi: Path):
    extraction = OpenAPIAdapter().extract(openapi)
    messages = [d.message for d in extraction.diagnostics]
    assert (
        "PATCH /invoices/{invoiceId} has no operationId, using patch_invoices_invoiceId" in messages
    )
    assert "could not resolve customers.yaml#/components/schemas/Customer" in messages
    assert set(extraction.artifacts) == {"inventory.json", "payments.yaml"}


def test_broken_documents_are_reported(tmp_path: Path):
    broken = tmp_path / "broken.yaml"
    broken.write_text("openapi: 3.1.0\npaths: [unclosed\n")
    extraction = OpenAPIAdapter().extract(broken)
    assert extraction.diagnostics[0].level == "error"


def test_resolver_follows_reference_chains():
    document = {"a": {"$ref": "#/b"}, "b": {"$ref": "#/c"}, "c": {"value": 1}}
    assert RefResolver(document).resolve({"$ref": "#/a"}) == {"value": 1}


def test_one_catalog_for_every_source(openapi: Path, reframework: Path):
    catalog = flowglyph.extract(reframework).merge(flowglyph.extract(openapi))
    assert set(catalog.lock.adapters) == {"uipath", "openapi"}
    hits = catalog.search("create invoice", invocable=True, limit=3)
    assert hits[0].id == "openapi/Payments_API/createInvoice"
    pure = [c for c in catalog if c.invocable and not c.effects.has_side_effects]
    assert {c.source.provider for c in pure} == {"uipath", "openapi"}
    assert catalog.get("deleteInvoice").effects.destructive is Tri.YES


def test_documents_with_the_same_title_stay_apart(openapi: Path, tmp_path: Path):
    for name in ("eu.yaml", "us.yaml"):
        (tmp_path / name).write_text((openapi / "payments.yaml").read_text())
    ids = {c.id for c in OpenAPIAdapter().extract(tmp_path).capabilities}
    assert {"openapi/Payments_API.eu/createInvoice", "openapi/Payments_API.us/createInvoice"} <= ids
