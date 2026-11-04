"""Planner quality against a real model. Run with `pytest -m llm`; every run is billed."""

from dataclasses import dataclass
from pathlib import Path

import pytest

import flowglyph
from flowglyph.catalog import Catalog
from flowglyph.planner import plan

pytestmark = pytest.mark.llm


@dataclass(frozen=True)
class Case:
    requirements: str
    expected: frozenset[str]
    expect_unresolved: bool = False


CASES = [
    Case(
        "When an invoice arrives check the vendor exists, ask for approval above 10000 EUR, "
        "then create the invoice.",
        frozenset({"ValidateVendor", "RequestApproval", "createInvoice"}),
    ),
    Case("List the invoices that are still drafts.", frozenset({"listInvoices"})),
    Case("Fetch invoice INV-7 and show its status.", frozenset({"getInvoice"})),
    Case("Delete the duplicated invoice INV-9.", frozenset({"deleteInvoice"})),
    Case(
        "Pay invoice INV-3 for 250 EUR on behalf of tenant es.",
        frozenset({"executePayment"}),
    ),
    Case(
        "Replace invoice INV-5 with the corrected data we received.",
        frozenset({"replaceInvoice"}),
    ),
    Case("Book the incoming invoice in the queue.", frozenset({"BookInvoice"})),
    Case(
        "Read the robot configuration and initialise the applications.",
        frozenset({"InitAllSettings", "InitAllApplications"}),
    ),
    Case(
        "Create the invoice and then send the vendor a WhatsApp message.",
        frozenset({"createInvoice"}),
        expect_unresolved=True,
    ),
    Case(
        "Get the next transaction from the queue, process it and record its status.",
        frozenset({"GetTransactionData", "Process", "SetTransactionStatus"}),
    ),
]


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    fixtures = Path(__file__).parents[1] / "fixtures"
    sources = [
        fixtures / "synthetic" / "invoices",
        fixtures / "openapi" / "payments.yaml",
        fixtures / "reframework",
    ]
    merged = flowglyph.extract(sources[0])
    for source in sources[1:]:
        merged = merged.merge(flowglyph.extract(source))
    return merged


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.requirements[:40])
def test_planner_case(case: Case, catalog: Catalog):
    report = plan(case.requirements, catalog)
    chosen = {c.rsplit("/", 1)[-1] for c in report.workflow.calls}
    assert not [p for p in report.problems if "not in the catalog" in p], "invented a capability"
    assert case.expected <= chosen, f"chose {sorted(chosen)}"
    assert bool(report.unresolved) is case.expect_unresolved
