from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
import yaml

import flowglyph
from flowglyph.catalog import Catalog
from flowglyph.planner import (
    Plan,
    PlannedArgument,
    PlannedInput,
    PlannedStep,
    PlannerError,
    candidates_for,
    plan,
)
from flowglyph.planner.claude import ClaudePlanModel

MAIN = "uipath/Invoices/Main"
VALIDATE = "uipath/Invoices/Steps/ValidateVendor"
APPROVAL = "uipath/Invoices/Steps/RequestApproval"
CREATE = "openapi/Payments_API/createInvoice"
REQUIREMENTS = (
    "When an invoice arrives, check that the vendor exists. "
    "If the amount is above 10000 EUR, ask for approval. Then create the invoice."
)


@pytest.fixture
def catalog(synthetic: Path) -> Catalog:
    uipath = flowglyph.extract(synthetic / "invoices")
    return uipath.merge(flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml"))


def step(
    step_id: str,
    capability: str | None,
    *arguments: PlannedArgument,
    after: Sequence[str] = (),
    condition: str | None = None,
) -> PlannedStep:
    return PlannedStep(
        id=step_id,
        intent=f"do {step_id}",
        capability=capability,
        arguments=list(arguments),
        after=list(after),
        condition=condition,
    )


def from_input(name: str, value: str) -> PlannedArgument:
    return PlannedArgument(name=name, source="workflow_input", value=value)


def literal(name: str, value: str) -> PlannedArgument:
    return PlannedArgument(name=name, source="literal", value=value)


def good_plan() -> Plan:
    return Plan(
        goal="Process supplier invoice",
        inputs=[
            PlannedInput(name="vendor_id", type="string", description="Vendor"),
            PlannedInput(name="invoice", type="object", description="Invoice"),
            PlannedInput(name="request_id", type="string", description="Business id"),
        ],
        steps=[
            step("check_vendor", VALIDATE, from_input("in_VendorId", "vendor_id")),
            step(
                "approve",
                APPROVAL,
                PlannedArgument(name="in_Approver", source="literal", value='"finance@acme.test"'),
                condition="invoice.amount > 10000",
            ),
            step(
                "create",
                CREATE,
                from_input("Idempotency-Key", "request_id"),
                from_input("body", "invoice"),
                after=["approve"],
            ),
        ],
        assumptions=["amounts are in EUR"],
    )


class FakeModel:
    def __init__(self, proposal: Plan) -> None:
        self.proposal = proposal
        self.candidates: list[dict[str, Any]] = []

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        self.candidates = list(candidates)
        return self.proposal


def test_a_valid_plan_becomes_workflow_ir(catalog: Catalog):
    model = FakeModel(good_plan())
    report = plan(REQUIREMENTS, catalog, model)
    assert report.ok, report.problems
    workflow = report.workflow
    assert workflow.id == "plan/process-supplier-invoice"
    assert [node.capability for node in workflow.nodes] == [VALIDATE, APPROVAL, CREATE]
    edges = {(edge.source, edge.target): edge.condition for edge in workflow.edges}
    assert edges == {
        ("check_vendor", "approve"): "invoice.amount > 10000",
        ("approve", "create"): None,
    }
    assert report.capability.effects.has_side_effects
    assert report.capability.input_schema["required"] == ["vendor_id", "invoice", "request_id"]
    assert report.warnings == [
        "approve has side effects: run it with an idempotency key so retries are safe"
    ]


def test_the_model_only_sees_relevant_candidates(catalog: Catalog):
    model = FakeModel(good_plan())
    plan(REQUIREMENTS, catalog, model)
    ids = [card["id"] for card in model.candidates]
    assert {VALIDATE, APPROVAL, CREATE} <= set(ids)
    assert all(not card["id"].startswith("uipath/activity/") for card in model.candidates)
    assert set(model.candidates[0]) == {
        "id",
        "description",
        "inputs",
        "outputs",
        "effects",
        "idempotency",
    }


def test_invented_capabilities_are_rejected(catalog: Catalog):
    proposal = good_plan()
    proposal.steps[2] = step("create", "sap/invoice/create", after=["approve"])
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert not report.ok
    assert "create uses sap/invoice/create, which is not in the catalog" in report.problems
    node = report.workflow.nodes[2]
    assert (node.kind, node.capability) == ("opaque", None)


def test_missing_capabilities_stay_visible(catalog: Catalog):
    proposal = good_plan()
    proposal.steps.append(step("archive", None))
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert report.unresolved == ["archive"]
    assert not report.problems
    assert report.workflow.unresolved_calls == ("do archive",)
    assert ("create", "archive") in {(e.source, e.target) for e in report.workflow.edges}


@pytest.mark.parametrize(
    ("broken", "problem"),
    [
        (
            step("check_vendor", VALIDATE, from_input("in_Vendor", "vendor_id")),
            f"check_vendor: {VALIDATE} has no input in_Vendor",
        ),
        (step("check_vendor", VALIDATE), "check_vendor: missing required inputs in_VendorId"),
        (
            step("check_vendor", VALIDATE, from_input("in_VendorId", "supplier")),
            "check_vendor.in_VendorId: unknown input supplier",
        ),
        (
            step(
                "check_vendor",
                VALIDATE,
                PlannedArgument(name="in_VendorId", source="literal", value="ACME"),
            ),
            "check_vendor.in_VendorId: literal 'ACME' is not valid JSON",
        ),
        (
            step(
                "check_vendor",
                VALIDATE,
                PlannedArgument(name="in_VendorId", source="step_output", value="create.out_Id"),
            ),
            "check_vendor.in_VendorId: create is not an earlier step",
        ),
    ],
)
def test_broken_steps_are_explained(catalog: Catalog, broken: PlannedStep, problem: str):
    proposal = good_plan()
    proposal.steps[0] = broken
    assert problem in plan(REQUIREMENTS, catalog, FakeModel(proposal)).problems


@pytest.mark.parametrize(
    ("argument", "problem"),
    [
        (
            from_input("in_Threshold", "vendor_id"),
            f"main.in_Threshold: {MAIN} expects number, but input vendor_id is string",
        ),
        (
            PlannedArgument(
                name="in_InvoicePath", source="step_output", value="check_vendor.out_Exists"
            ),
            (
                f"main.in_InvoicePath: {MAIN} expects string or null, "
                "but check_vendor.out_Exists is boolean"
            ),
        ),
        (
            literal("in_Threshold", '"10000"'),
            f"main.in_Threshold: {MAIN} expects number, but literal '\"10000\"' is string",
        ),
        (
            literal("in_Threshold", "null"),
            f"main.in_Threshold: {MAIN} expects number, but literal 'null' is null",
        ),
    ],
)
def test_arguments_of_the_wrong_type_are_rejected(
    catalog: Catalog, argument: PlannedArgument, problem: str
):
    proposal = good_plan()
    proposal.steps.append(step("main", MAIN, literal("in_InvoicePath", '"in/a.pdf"'), argument))
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert report.problems == [problem]
    assert not report.ok


@pytest.mark.parametrize(
    "arguments",
    [
        (literal("in_InvoicePath", '"in/a.pdf"'), from_input("in_Threshold", "amount")),
        (literal("in_InvoicePath", '"in/a.pdf"'), literal("in_Threshold", "10000")),
        (literal("in_InvoicePath", '"in/a.pdf"'), literal("in_Threshold", "10000.5")),
        (literal("in_InvoicePath", "null"),),
        (PlannedArgument(name="in_InvoicePath", source="step_output", value="create.body"),),
    ],
    ids=["same type", "integer fits number", "number", "null fits nullable", "any fits"],
)
def test_arguments_of_a_compatible_type_pass(
    catalog: Catalog, arguments: tuple[PlannedArgument, ...]
):
    proposal = good_plan()
    proposal.inputs.append(PlannedInput(name="amount", type="number", description="Amount"))
    proposal.steps.append(step("main", MAIN, *arguments))
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert report.problems == []


def test_outputs_must_exist(catalog: Catalog):
    proposal = good_plan()
    proposal.steps[1] = step(
        "approve",
        APPROVAL,
        PlannedArgument(name="in_Approver", source="step_output", value="check_vendor.out_Nope"),
    )
    problems = plan(REQUIREMENTS, catalog, FakeModel(proposal)).problems
    assert f"approve.in_Approver: {VALIDATE} has no output out_Nope" in problems


def test_dependencies_must_point_backwards(catalog: Catalog):
    proposal = good_plan()
    proposal.steps[0] = step(
        "check_vendor", VALIDATE, from_input("in_VendorId", "vendor_id"), after=["create"]
    )
    problems = plan(REQUIREMENTS, catalog, FakeModel(proposal)).problems
    assert "check_vendor runs after create, which is not an earlier step" in problems


def test_reports_are_saved_as_yaml(catalog: Catalog, tmp_path: Path):
    report = plan(REQUIREMENTS, catalog, FakeModel(good_plan()))
    proposal, result = report.save(tmp_path)
    assert yaml.safe_load(proposal.read_text())["goal"] == "Process supplier invoice"
    document = yaml.safe_load(result.read_text())
    assert document["status"] == "ok"
    assert document["workflow"]["nodes"][0]["capability"] == VALIDATE


def test_sentence_level_retrieval_keeps_rare_steps(catalog: Catalog):
    text = (
        "Book the invoice. " + "Validate the supplier record carefully. " * 3 + "Request approval."
    )
    ids = [capability.id for capability in candidates_for(text, catalog, limit=2)]
    assert APPROVAL in ids


class FakeMessages:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def parse(self, **request: Any) -> object:
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def claude_with(outcome: object) -> tuple[ClaudePlanModel, FakeMessages]:
    messages = FakeMessages(outcome)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudePlanModel(client=client), messages  # pyright: ignore[reportArgumentType]


def test_claude_request_shape():
    model, messages = claude_with(
        SimpleNamespace(stop_reason="end_turn", parsed_output=good_plan())
    )
    assert model.propose("Do things.", [{"id": "x"}]) == good_plan()
    request = messages.calls[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["output_format"] is Plan
    assert request["output_config"] == {"effort": "high"}
    assert request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert '{"id": "x"}' in request["messages"][0]["content"]


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        (SimpleNamespace(stop_reason="refusal", parsed_output=None), "declined"),
        (SimpleNamespace(stop_reason="max_tokens", parsed_output=None), "complete plan"),
        (
            anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.test")),
            "could not reach",
        ),
    ],
)
def test_claude_failures_become_planner_errors(outcome: object, message: str):
    model, _ = claude_with(outcome)
    with pytest.raises(PlannerError, match=message):
        model.propose("Do things.", [])


@pytest.mark.usefixtures("no_anthropic_credentials")
def test_missing_credentials_are_reported_before_any_request(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(PlannerError, match=r"set ANTHROPIC_API_KEY .* --via claude-code"):
        ClaudePlanModel()
    monkeypatch.setenv("ANTHROPIC_PROFILE", "nope")
    with pytest.raises(PlannerError, match="could not be read"):
        ClaudePlanModel()
    monkeypatch.delenv("ANTHROPIC_PROFILE")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert ClaudePlanModel().client.api_key == "sk-test"


def test_steps_that_depend_on_an_optional_step_are_flagged(catalog: Catalog):
    proposal = good_plan()
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert (
        "create is skipped whenever approve is skipped; set join to any if it should run either way"
        not in report.warnings
    ), "create only depends on approve"
    proposal.steps[2] = step(
        "create",
        CREATE,
        from_input("Idempotency-Key", "request_id"),
        from_input("body", "invoice"),
        after=["check_vendor", "approve"],
    )
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert (
        "create is skipped whenever approve is skipped; set join to any if it should run either way"
        in report.warnings
    )
    proposal.steps[2] = proposal.steps[2].model_copy(update={"join": "any"})
    report = plan(REQUIREMENTS, catalog, FakeModel(proposal))
    assert not any("is skipped whenever" in warning for warning in report.warnings)
    assert report.workflow.nodes[2].join == "any"
    assert report.workflow.simulate(lambda condition: False) == ["check_vendor", "create"]
