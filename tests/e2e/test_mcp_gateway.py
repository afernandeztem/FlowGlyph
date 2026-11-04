import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

import flowglyph
from flowglyph.gateway import Gateway
from flowglyph.gateway.server import build_server, tool_name

INVOICE = {"vendor": "ACME", "amount": 120.5, "currency": "EUR", "reference": "INV-118"}


@pytest.fixture
def catalog_dir(synthetic: Path, tmp_path: Path) -> Path:
    uipath = flowglyph.extract(synthetic / "invoices")
    openapi = flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml")
    return uipath.merge(openapi).save(tmp_path / "catalog")


def structured(result: Any) -> dict[str, Any]:
    assert result.structured_content is not None
    return result.structured_content


async def test_agent_workflow_discover_choose_run(catalog_dir: Path):
    async with Client(build_server(Gateway(catalog_dir))) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert {"catalog_search", "catalog_card", "run_capability"} <= set(tools)
        create = tools["openapi_Payments_API_createInvoice"]
        assert create.annotations is not None
        assert create.annotations.read_only_hint is False
        assert create.annotations.destructive_hint is False
        assert "_idempotency_key" in create.input_schema["properties"]
        listing = tools["openapi_Payments_API_listInvoices"]
        assert listing.annotations is not None
        assert listing.annotations.read_only_hint is True

        found = structured(await client.call_tool("catalog_search", {"query": "create invoice"}))
        assert found["results"][0]["id"] == "openapi/Payments_API/createInvoice"

        card = await client.call_tool("catalog_card", {"capability": "createInvoice"})
        assert "## Inputs" in card.content[0].text  # pyright: ignore[reportAttributeAccessIssue]

        arguments = {"Idempotency-Key": "inv-118", "body": INVOICE}
        first = structured(await client.call_tool(create.name, arguments))
        again = structured(
            await client.call_tool(
                "run_capability",
                {"capability": "createInvoice", "arguments": arguments},
            )
        )
        assert (first["status"], again["status"]) == ("done", "replayed")

        status = structured(
            await client.call_tool("run_status", {"idempotency_key": first["idempotency_key"]})
        )
        assert status["status"] == "done"


async def test_errors_are_reported_to_the_agent(catalog_dir: Path):
    async with Client(build_server(Gateway(catalog_dir))) as client:
        invalid = await client.call_tool("openapi_Payments_API_createInvoice", {"body": {}})
        assert invalid.is_error
        assert "'Idempotency-Key' is a required property" in structured(invalid)["errors"]
        unknown = await client.call_tool("catalog_card", {"capability": "nope"})
        assert unknown.is_error
        held = structured(
            await client.call_tool("openapi_Payments_API_deleteInvoice", {"invoiceId": "1"})
        )
        assert held["status"] == "approval_required"


async def test_meta_exposure_keeps_the_tool_list_small(catalog_dir: Path):
    async with Client(build_server(Gateway(catalog_dir), expose="meta")) as client:
        names = [tool.name for tool in (await client.list_tools()).tools]
        assert names == [
            "catalog_search",
            "catalog_card",
            "catalog_contract",
            "run_capability",
            "run_status",
        ]


async def test_resources_serve_the_index_and_cards(catalog_dir: Path):
    async with Client(build_server(Gateway(catalog_dir))) as client:
        resources = (await client.list_resources()).resources
        uris = {str(resource.uri) for resource in resources}
        assert "flowglyph://index" in uris
        index = await client.read_resource("flowglyph://index")
        assert index.contents[0].text.startswith("# Catalog")  # pyright: ignore[reportAttributeAccessIssue]
        card = await client.read_resource("flowglyph://cards/uipath_Invoices_Main")
        assert "# Main" in card.contents[0].text  # pyright: ignore[reportAttributeAccessIssue]


def test_tool_names_are_valid_for_long_ids(catalog_dir: Path):
    capability = flowglyph.load_catalog(catalog_dir).get("createInvoice")
    long = capability.model_copy(update={"id": "x/" * 60 + "op"})
    name = tool_name(long)
    assert len(name) <= 64
    assert name == tool_name(long), "stable"


async def test_the_real_command_speaks_mcp_over_stdio(catalog_dir: Path):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "flowglyph", "serve", str(catalog_dir)]
    )
    async with Client(params) as client:
        found = structured(await client.call_tool("catalog_search", {"query": "approval"}))
        assert found["results"][0]["id"] == "uipath/Invoices/Steps/RequestApproval"
