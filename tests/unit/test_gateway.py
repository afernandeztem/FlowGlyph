import json
import shutil
from pathlib import Path
from typing import ClassVar

import pytest

import flowglyph
from flowglyph.errors import ExecutionError, FlowGlyphError
from flowglyph.gateway import Gateway, Policy, Rule
from flowglyph.ir import Capability

CREATE = "openapi/Payments_API/createInvoice"
DELETE = "openapi/Payments_API/deleteInvoice"
LIST = "openapi/Payments_API/listInvoices"
BOOK = "uipath/Invoices/Steps/BookInvoice"
INVOICE = {"vendor": "ACME", "amount": 120.5, "currency": "EUR", "reference": "INV-118"}


@pytest.fixture
def catalog_dir(synthetic: Path, tmp_path: Path) -> Path:
    uipath = flowglyph.extract(synthetic / "invoices")
    openapi = flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml")
    return uipath.merge(openapi).save(tmp_path / "catalog")


@pytest.fixture
def gateway(catalog_dir: Path) -> Gateway:
    return Gateway(catalog_dir)


def audit(gateway: Gateway) -> list[dict[str, object]]:
    return [json.loads(line) for line in gateway.audit.path.read_text().splitlines()]


def test_search_returns_l0_cards(gateway: Gateway):
    cards = gateway.search("create invoice", limit=3)
    assert cards[0]["id"] == CREATE
    assert set(cards[0]) == {"id", "d", "in", "out", "e", "i"}
    assert "# createInvoice" in gateway.describe(CREATE)
    assert gateway.contract(CREATE)["idempotency"]["mode"] == "key"


def test_pure_capabilities_run_without_the_ledger(gateway: Gateway):
    result = gateway.run(LIST, {"limit": 10})
    assert result.status == "done"
    assert result.enforcement == "none"
    assert result.result["dry_run"] is True


def test_side_effects_run_once_per_key(gateway: Gateway):
    arguments = {"Idempotency-Key": "inv-118", "body": INVOICE}
    first = gateway.run(CREATE, arguments)
    second = gateway.run(CREATE, arguments)
    assert (first.status, second.status) == ("done", "replayed")
    assert first.idempotency_key == f'{CREATE}#"inv-118"'
    assert second.result == first.result
    assert second.enforcement == "ledger"


def test_reusing_a_key_with_other_arguments_is_a_conflict(gateway: Gateway):
    gateway.run(CREATE, {"Idempotency-Key": "inv-118", "body": INVOICE})
    changed = {"Idempotency-Key": "inv-118", "body": {**INVOICE, "amount": 999}}
    assert gateway.run(CREATE, changed).status == "conflict"


def test_without_a_key_identical_calls_are_deduplicated(gateway: Gateway):
    arguments = {"in_Invoice": {"id": 1}}
    assert gateway.run(BOOK, arguments).status == "done"
    assert gateway.run(BOOK, arguments).status == "replayed"
    assert gateway.run(BOOK, arguments, idempotency_key="batch-2").status == "done"


def test_invalid_arguments_are_explained(gateway: Gateway):
    result = gateway.run(CREATE, {"body": {"vendor": 3}})
    assert result.status == "invalid"
    assert "'Idempotency-Key' is a required property" in result.errors
    assert any(error.startswith("body/vendor:") for error in result.errors)


def test_documentation_only_capabilities_cannot_run(gateway: Gateway):
    result = gateway.run("uipath/activity/SendMail", {})
    assert result.status == "invalid"
    assert gateway.run("does-not-exist", {}).status == "invalid"


def test_destructive_steps_wait_for_a_person(gateway: Gateway):
    arguments = {"invoiceId": "INV-118"}
    held = gateway.run(DELETE, arguments, idempotency_key="cleanup-118")
    assert held.status == "approval_required"
    assert held.reason is not None
    assert "flowglyph approve" in held.reason
    assert (
        gateway.run(DELETE, arguments, idempotency_key="cleanup-118").status == "approval_required"
    )
    assert held.idempotency_key is not None
    assert gateway.ledger.approve(held.idempotency_key)
    assert gateway.run(DELETE, arguments, idempotency_key="cleanup-118").status == "done"
    assert gateway.run(DELETE, arguments, idempotency_key="cleanup-118").status == "replayed"


def test_deny_rules_stop_execution(catalog_dir: Path):
    policy = Policy(
        rules=(Rule(capabilities="openapi/*/executePayment", action="deny", reason="manual"),)
    )
    gateway = Gateway(catalog_dir, policy=policy)
    result = gateway.run(
        "executePayment", {"X-Tenant": "es", "body": {"invoiceId": "1", "amount": 10}}
    )
    assert (result.status, result.reason) == ("denied", "manual")
    assert gateway.run("executePayment", {}).status == "denied"


def test_failures_are_recorded_and_retryable(catalog_dir: Path):
    class Flaky:
        name: ClassVar[str] = "flaky"
        calls = 0

        def execute(
            self, capability: Capability, arguments: dict[str, object]
        ) -> dict[str, object]:
            Flaky.calls += 1
            if Flaky.calls == 1:
                raise FlowGlyphError("ERP timed out")
            return {"ok": True}

    gateway = Gateway(catalog_dir, executor=Flaky())
    arguments = {"Idempotency-Key": "inv-7", "body": INVOICE}
    failed = gateway.run(CREATE, arguments)
    assert (failed.status, failed.errors) == ("failed", ["ERP timed out"])
    assert gateway.run(CREATE, arguments).status == "done"


class Broken:
    """An executor with a bug: it raises something that is not a FlowGlyphError."""

    name: ClassVar[str] = "broken"

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def execute(self, capability: Capability, arguments: dict[str, object]) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            raise self.error
        return {"ok": True}


def test_executor_bugs_become_failed_runs_that_can_be_retried(catalog_dir: Path):
    gateway = Gateway(catalog_dir, executor=Broken(KeyError("Id")))
    arguments = {"Idempotency-Key": "inv-9", "body": INVOICE}
    failed = gateway.run(CREATE, arguments)
    assert (failed.status, failed.errors) == ("failed", ["KeyError: 'Id'"])
    assert failed.idempotency_key is not None
    stored = gateway.ledger.get(failed.idempotency_key)
    assert stored is not None
    assert stored.status == "failed"
    assert gateway.run(CREATE, arguments).status == "done"
    events = [(entry["event"], entry.get("status")) for entry in audit(gateway)]
    assert events == [("start", None), ("run", "failed"), ("start", None), ("run", "done")]


def test_read_only_runs_report_execution_errors(catalog_dir: Path):
    gateway = Gateway(catalog_dir, executor=Broken(ExecutionError("API answered 503")))
    result = gateway.run(LIST, {"limit": 10})
    assert (result.status, result.errors) == ("failed", ["API answered 503"])
    assert result.enforcement == "none"
    assert audit(gateway)[-1]["status"] == "failed"


def test_approvals_show_the_arguments_and_name_the_approver(gateway: Gateway):
    arguments = {"invoiceId": "INV-118"}
    held = gateway.run(DELETE, arguments, idempotency_key="cleanup-118")
    assert held.idempotency_key is not None
    waiting = gateway.ledger.pending_approvals()
    assert [run.arguments for run in waiting] == [arguments]
    assert gateway.approve("nothing-here", actor="angel") is None
    approved = gateway.approve(held.idempotency_key, actor="angel")
    assert approved is not None
    assert approved.status == "approved"
    entry = audit(gateway)[-1]
    assert (entry["event"], entry["actor"], entry["capability"]) == ("approve", "angel", DELETE)
    assert entry["idempotency_key"] == held.idempotency_key
    assert "INV-118" not in gateway.audit.path.read_text()


def test_audit_log_never_contains_argument_values(gateway: Gateway):
    result = gateway.run(CREATE, {"Idempotency-Key": "secret-key", "body": INVOICE})
    entries = audit(gateway)
    assert entries[-1]["argument_names"] == ["Idempotency-Key", "body"]
    assert all(entry["actor"] is None for entry in entries)
    raw = gateway.audit.path.read_text()
    assert "ACME" not in raw
    assert "INV-118" not in raw
    assert result.idempotency_key is not None
    stored = gateway.ledger.get(result.idempotency_key)
    assert stored is not None
    assert stored.arguments == {"Idempotency-Key": "secret-key", "body": INVOICE}


def test_catalog_changes_are_picked_up_without_restart(
    gateway: Gateway, synthetic: Path, tmp_path: Path
):
    assert gateway.search("payment", limit=1)
    project = tmp_path / "project"
    shutil.copytree(synthetic / "invoices", project)
    (project / "Steps" / "RequestApproval.xaml").unlink()
    flowglyph.extract(project).save(gateway.catalog_dir)
    with pytest.raises(FlowGlyphError):
        gateway.catalog.get("Steps/RequestApproval")
