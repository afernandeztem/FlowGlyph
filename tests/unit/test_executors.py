"""Executors send what each system expects, read what it answers, and fail clearly."""

import json
import re
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

import flowglyph
from flowglyph.errors import ExecutionError
from flowglyph.gateway import Gateway
from flowglyph.gateway.executors import (
    ConnectedExecutor,
    Connections,
    HttpExecutor,
    ODataExecutor,
    OrchestratorExecutor,
)
from flowglyph.gateway.executors.auth import BasicAuth, BearerAuth, ClientCredentialsAuth, NoAuth
from flowglyph.ir import Capability, Source, Trigger

FIXTURES = Path(__file__).parents[1] / "fixtures"
MAIN = "uipath/reframework/Main"


@dataclass
class Call:
    """One request the fake server received."""

    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: Any

    def with_headers(self, **headers: str) -> "Call":
        lowered = {name.lower(): value for name, value in headers.items()}
        return Call(self.method, self.path, self.query, {**self.headers, **lowered}, self.body)


@dataclass
class Reply:
    """What the fake server answers to a request."""

    status: int = 200
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict[str, str])


type Script = Callable[[Call], Reply]


def answer(status: int, body: Any = None, headers: dict[str, str] | None = None) -> Script:
    """A script that always answers the same thing."""

    def script(call: Call) -> Reply:
        del call
        return Reply(status, body, headers or {})

    return script


@dataclass
class FakeSystem:
    """An HTTP server that answers by script and records every call."""

    url: str
    calls: list[Call]
    script: Script


class _Handler(BaseHTTPRequestHandler):
    system: FakeSystem

    def serve(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        is_json = self.headers.get("Content-Type", "").startswith("application/json")
        parts = urlsplit(self.path)
        body = json.loads(raw) if raw and is_json else raw.decode()
        # urllib writes header names its own way, so the fake keeps them lower case.
        headers = {name.lower(): value for name, value in self.headers.items()}
        call = Call(self.command, parts.path, dict(parse_qsl(parts.query)), headers, body)
        self.system.calls.append(call)
        reply = self.system.script(call)
        payload = b"" if reply.body is None else json.dumps(reply.body).encode()
        self.send_response(reply.status)
        for name, value in reply.headers.items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


for _method in ("GET", "POST", "PATCH", "PUT", "DELETE"):
    setattr(_Handler, f"do_{_method}", _Handler.serve)


@pytest.fixture
def system() -> Iterator[FakeSystem]:
    state = FakeSystem("", [], lambda call: Reply(404, {"error": f"unexpected {call.path}"}))

    class Handler(_Handler):
        system = state

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    state.url = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield state
    httpd.shutdown()


@pytest.fixture
def payments(synthetic: Path) -> flowglyph.Catalog:
    return flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml")


@pytest.fixture
def sap() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES / "sap")


@pytest.fixture
def robots() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES / "reframework")


def test_secrets_come_from_the_environment(system: FakeSystem, payments: flowglyph.Catalog):
    executor = HttpExecutor(system.url + "/v1", BearerAuth(type="bearer", token_env="PAY_TOKEN"))
    with pytest.raises(ExecutionError, match="PAY_TOKEN is not set"):
        executor.execute(payments.get("createInvoice"), {})
    assert system.calls == []


def test_http_executor_sends_headers_body_path_and_query(
    system: FakeSystem, payments: flowglyph.Catalog, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PAY_TOKEN", "t0k3n")
    system.script = lambda call: Reply(200, {"items": [], "seen": call.path})
    executor = HttpExecutor(system.url + "/v1/", BearerAuth(type="bearer", token_env="PAY_TOKEN"))
    invoice = {"vendor": "ACME", "amount": 1, "currency": "EUR", "reference": "R1"}
    created = executor.execute(
        payments.get("createInvoice"), {"Idempotency-Key": "k-1", "body": invoice}
    )
    call = system.calls[-1]
    assert (call.method, call.path) == ("POST", "/v1/invoices")
    assert call.headers["authorization"] == "Bearer t0k3n"
    assert call.headers["idempotency-key"] == "k-1"
    assert call.body == invoice
    assert created == {"status": 200, "body": {"items": [], "seen": "/v1/invoices"}}

    executor.execute(payments.get("getInvoice"), {"invoiceId": "INV 7/a"})
    assert system.calls[-1].path == "/v1/invoices/INV%207%2Fa"

    executor.execute(payments.get("listInvoices"), {"status": "open", "limit": 5})
    assert system.calls[-1].query == {"status": "open", "limit": "5"}


def test_http_executor_reports_error_answers(system: FakeSystem, payments: flowglyph.Catalog):
    system.script = answer(422, {"message": "amount must be positive"})
    executor = HttpExecutor(system.url, NoAuth())
    with pytest.raises(ExecutionError, match="answered 422") as failure:
        executor.execute(payments.get("listInvoices"), {})
    assert "amount must be positive" in str(failure.value)


def test_http_executor_never_follows_redirects(system: FakeSystem, payments: flowglyph.Catalog):
    elsewhere = "https://elsewhere.example/v1"
    system.script = answer(302, None, {"Location": elsewhere})
    executor = HttpExecutor(system.url, NoAuth())
    with pytest.raises(ExecutionError, match=re.escape(f"redirected to {elsewhere}")):
        executor.execute(payments.get("listInvoices"), {})


def test_only_http_urls_are_called(payments: flowglyph.Catalog):
    executor = HttpExecutor("file:///etc", NoAuth())
    with pytest.raises(ExecutionError, match="only http and https"):
        executor.execute(payments.get("listInvoices"), {})


def _sap_script(state: dict[str, Any]) -> Script:
    """An SAP Gateway that hands out CSRF tokens and rejects stale ones."""

    def script(call: Call) -> Reply:
        if call.headers.get("x-csrf-token") == "Fetch":
            state["fetches"] = state.get("fetches", 0) + 1
            return Reply(200, {}, {"X-CSRF-Token": f"csrf-{state['fetches']}"})
        current = f"csrf-{state.get('fetches', 0)}"
        if call.method != "GET" and call.headers.get("x-csrf-token") != current:
            message = {"error": {"message": {"value": "CSRF token validation failed"}}}
            return Reply(403, message, {"X-CSRF-Token": "Required"})
        reply: Script = state["reply"]
        return reply(call)

    return script


def test_odata_v2_reads_and_unwraps(
    system: FakeSystem, sap: flowglyph.Catalog, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SAP_USER", "agent")
    monkeypatch.setenv("SAP_PASSWORD", "pw")
    rows = [{"__metadata": {"uri": "x"}, "SupplierInvoice": "5100000123", "FiscalYear": "2026"}]
    state: dict[str, Any] = {"reply": answer(200, {"d": {"results": rows}})}
    system.script = _sap_script(state)
    auth = BasicAuth(type="basic", user_env="SAP_USER", password_env="SAP_PASSWORD")
    executor = ODataExecutor(system.url + "/sap/opu/odata/sap/ZSUPPLIER_INVOICE_SRV", auth)

    listed = executor.execute(
        sap.get("SupplierInvoice/query"), {"$filter": "FiscalYear eq '2026'", "$top": 10}
    )
    call = system.calls[-1]
    assert call.path.endswith("/ZSUPPLIER_INVOICE_SRV/SupplierInvoice")
    assert call.query == {"$filter": "FiscalYear eq '2026'", "$top": "10", "$format": "json"}
    assert call.headers["authorization"].startswith("Basic ")
    assert listed == {"value": [{"SupplierInvoice": "5100000123", "FiscalYear": "2026"}]}

    state["reply"] = answer(200, {"d": rows[0]})
    key = {"SupplierInvoice": "5100000123", "FiscalYear": "2026"}
    one = executor.execute(sap.get("SupplierInvoice/read"), key)
    predicate = "/SupplierInvoice(SupplierInvoice='5100000123',FiscalYear='2026')"
    assert system.calls[-1].path.endswith(predicate)
    assert one == {"SupplierInvoice": "5100000123", "FiscalYear": "2026"}


def test_odata_v2_changes_fetch_a_csrf_token_and_retry_once(
    system: FakeSystem, sap: flowglyph.Catalog
):
    created_row = {"d": {"__metadata": {}, "SupplierInvoice": "5100000124"}}
    state: dict[str, Any] = {"reply": answer(201, created_row)}
    system.script = _sap_script(state)
    executor = ODataExecutor(system.url + "/svc", NoAuth())
    body = {"CompanyCode": "1010", "InvoicingParty": "17300001"}
    created = executor.execute(sap.get("SupplierInvoice/create"), {"body": body})
    assert created == {"SupplierInvoice": "5100000124"}
    assert [(c.method, c.headers.get("x-csrf-token")) for c in system.calls] == [
        ("GET", "Fetch"),
        ("POST", "csrf-1"),
    ]
    assert system.calls[-1].body == body

    state["fetches"] = 5  # the server rotated its token behind our back
    key = {"SupplierInvoice": "5100000124", "FiscalYear": "2026", "body": {"IsBlocked": False}}
    executor.execute(sap.get("SupplierInvoice/update"), key)
    tail = system.calls[-3:]
    assert [c.method for c in tail] == ["POST", "GET", "POST"]
    assert tail[0].headers["x-csrf-token"] == "csrf-1"
    assert tail[-1].headers["x-csrf-token"] == "csrf-6"
    assert tail[-1].headers["x-http-method"] == "MERGE"
    assert tail[-1].headers["if-match"] == "*"


def test_odata_v2_function_import_passes_literals_in_the_query(
    system: FakeSystem, sap: flowglyph.Catalog
):
    state: dict[str, Any] = {"reply": answer(200, {"d": {"results": []}})}
    system.script = _sap_script(state)
    executor = ODataExecutor(system.url + "/svc", NoAuth())
    arguments = {"InvoicingParty": "17300001", "InvoiceGrossAmount": 99.5}
    result = executor.execute(sap.get("GetDuplicateCandidates"), arguments)
    call = system.calls[-1]
    assert call.path.endswith("/svc/GetDuplicateCandidates")
    assert call.query == {
        "InvoicingParty": "'17300001'",
        "InvoiceGrossAmount": "99.5M",
        "$format": "json",
    }
    assert result == {"value": []}


def test_odata_v4_bound_action_and_function(system: FakeSystem, sap: flowglyph.Catalog):
    payload = {"@odata.context": "$metadata#x", "value": True}
    state: dict[str, Any] = {"reply": answer(200, payload)}
    system.script = _sap_script(state)
    executor = ODataExecutor(system.url + "/svc", NoAuth())
    arguments = {"BusinessPartner": "17300001", "Reason": "fraud"}
    blocked = executor.execute(sap.get("BusinessPartner/block"), arguments)
    call = system.calls[-1]
    assert call.method == "POST"
    assert call.path.endswith("/svc/BusinessPartner('17300001')/zbusinesspartner.block")
    assert call.body == {"Reason": "fraud"}
    assert "$format" not in call.query
    assert blocked == {"value": True}

    found = {"@odata.context": "x", "value": [{"BusinessPartner": "1"}]}
    state["reply"] = answer(200, found)
    executor.execute(sap.get("checkDuplicates"), {"FullName": "O'Neil"})
    assert system.calls[-1].path.endswith("/svc/checkDuplicates(FullName='O''Neil')")
    assert system.calls[-1].method == "GET"


def test_odata_errors_quote_the_server_message(system: FakeSystem, sap: flowglyph.Catalog):
    error = {"error": {"code": "X", "message": {"lang": "en", "value": "Invoice is blocked"}}}
    state: dict[str, Any] = {"reply": answer(400, error)}
    system.script = _sap_script(state)
    executor = ODataExecutor(system.url + "/svc", NoAuth())
    with pytest.raises(ExecutionError, match="answered 400: Invoice is blocked"):
        executor.execute(sap.get("SupplierInvoice/query"), {})


def _orchestrator_script(state: dict[str, Any]) -> Script:
    """An Orchestrator with one folder, one process and one job that `state["job"]` plays."""

    def identity(call: Call) -> Reply | None:
        if call.path.endswith("/connect/token"):
            state["tokens"] = state.get("tokens", 0) + 1
            return Reply(200, {"access_token": f"jwt-{state['tokens']}", "expires_in": 3600})
        if call.headers.get("authorization") != f"Bearer jwt-{state.get('tokens', 0)}":
            return Reply(401, {"message": "unauthorized"})
        if call.path.endswith("/odata/Folders"):
            return Reply(200, {"value": [{"Id": 77, "FullyQualifiedName": "Finance"}]})
        if call.headers.get("x-uipath-organizationunitid") != "77":
            return Reply(400, {"message": "folder missing"})
        return None

    def folder(call: Call) -> Reply:
        if call.path.endswith("/odata/Releases"):
            published = "'reframework'" in call.query["$filter"]
            return Reply(200, {"value": [{"Key": "rel-1"}] if published else []})
        if call.path.endswith("StartJobs"):
            state["start"] = call.body
            return Reply(201, {"value": [{"Id": 4242, "State": "Pending"}]})
        if call.path.endswith("/odata/Jobs(4242)"):
            state["polls"] = state.get("polls", 0) + 1
            job: Callable[[int], dict[str, Any]] = state["job"]
            return Reply(200, job(state["polls"]))
        return Reply(404, {"message": f"unexpected {call.path}"})

    return lambda call: identity(call) or folder(call)


def _signed_in(script: Script) -> Script:
    """The same Orchestrator, for executors that bring no credentials of their own."""
    return lambda call: script(call.with_headers(Authorization="Bearer jwt-0"))


def _running_then_done(polls: int) -> dict[str, Any]:
    if polls < 3:
        return {"State": "Running"}
    return {"State": "Successful", "OutputArguments": json.dumps({"out_Count": 12})}


def _faulted(polls: int) -> dict[str, Any]:
    del polls
    return {"State": "Faulted", "Info": "Excel not found"}


def _forever(polls: int) -> dict[str, Any]:
    del polls
    return {"State": "Running"}


def test_orchestrator_starts_a_job_and_waits(
    system: FakeSystem, robots: flowglyph.Catalog, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("UIPATH_CLIENT_ID", "app")
    monkeypatch.setenv("UIPATH_CLIENT_SECRET", "s3cret")
    state: dict[str, Any] = {"job": _running_then_done}
    system.script = _orchestrator_script(state)
    auth = ClientCredentialsAuth(
        type="client_credentials",
        token_url=system.url + "/identity_/connect/token",
        client_id_env="UIPATH_CLIENT_ID",
        client_secret_env="UIPATH_CLIENT_SECRET",
        scope="OR.Jobs OR.Execution",
    )
    executor = OrchestratorExecutor(
        system.url + "/acme/finance/orchestrator_", auth, folder="Finance", poll_seconds=0.01
    )
    result = executor.execute(robots.get(MAIN), {"in_OrchestratorQueueName": "AP_Invoices"})
    assert result == {"job_id": "4242", "state": "Successful", "outputs": {"out_Count": 12}}
    assert state["tokens"] == 1
    token_call = next(c for c in system.calls if c.path.endswith("/connect/token"))
    assert dict(parse_qsl(token_call.body)) == {
        "grant_type": "client_credentials",
        "client_id": "app",
        "client_secret": "s3cret",
        "scope": "OR.Jobs OR.Execution",
    }
    start = state["start"]["startInfo"]
    assert json.loads(start["InputArguments"]) == {"in_OrchestratorQueueName": "AP_Invoices"}
    assert start["ReleaseKey"] == "rel-1"
    assert state["polls"] == 3


def test_orchestrator_reports_faulted_jobs_and_missing_processes(
    system: FakeSystem, robots: flowglyph.Catalog
):
    system.script = _signed_in(_orchestrator_script({"job": _faulted}))
    executor = OrchestratorExecutor(system.url, NoAuth(), folder="Finance", poll_seconds=0.01)
    with pytest.raises(ExecutionError, match="ended Faulted: Excel not found"):
        executor.execute(robots.get(MAIN), {"in_OrchestratorQueueName": "Q"})
    renamed = OrchestratorExecutor(
        system.url, NoAuth(), folder="Finance", processes={"reframework": "Invoices_PROD"}
    )
    with pytest.raises(ExecutionError, match="no process named 'Invoices_PROD'"):
        renamed.execute(robots.get(MAIN), {"in_OrchestratorQueueName": "Q"})
    with pytest.raises(ExecutionError, match="not a published process"):
        executor.execute(robots.get("Framework/InitAllSettings"), {})


def test_orchestrator_gives_up_after_the_timeout(system: FakeSystem, robots: flowglyph.Catalog):
    system.script = _signed_in(_orchestrator_script({"job": _forever}))
    executor = OrchestratorExecutor(
        system.url, NoAuth(), folder="Finance", timeout_seconds=0.05, poll_seconds=0.01
    )
    with pytest.raises(ExecutionError, match="still Running after 0s"):
        executor.execute(robots.get(MAIN), {"in_OrchestratorQueueName": "Q"})


CONNECTIONS = """
connections:
  payments:
    type: http
    base_url: {url}/v1
    auth: {{type: header, header: X-Api-Key, value_env: PAY_KEY}}
    capabilities: ["openapi/Payments_API/*"]
  erp:
    type: odata
    service_url: {url}/svc
    capabilities: ["sap/*"]
"""


def test_connections_route_by_capability_pattern(
    system: FakeSystem,
    payments: flowglyph.Catalog,
    sap: flowglyph.Catalog,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PAY_KEY", "key-1")
    file = tmp_path / "flowglyph.connections.yaml"
    file.write_text(CONNECTIONS.format(url=system.url), encoding="utf-8")
    connections = Connections.load(file)
    assert connections.variables() == {"payments": ["PAY_KEY"], "erp": []}
    system.script = lambda call: Reply(200, {"ok": call.path})
    executor = ConnectedExecutor(connections)
    listed = executor.execute(payments.get("listInvoices"), {})
    assert listed == {"connection": "payments", "status": 200, "body": {"ok": "/v1/invoices"}}
    assert system.calls[-1].headers["x-api-key"] == "key-1"
    assert executor.execute(sap.get("Supplier/query"), {}) == {"connection": "erp", "value": []}
    with pytest.raises(ExecutionError, match="no connection runs uipath/x"):
        executor.execute(_capability("uipath/x"), {})


def test_connections_files_are_checked(tmp_path: Path):
    bad = tmp_path / "flowglyph.connections.yaml"
    bad.write_text(
        "connections:\n  erp: {type: odata, capabilities: ['sap/*']}\n", encoding="utf-8"
    )
    with pytest.raises(ExecutionError, match="service_url"):
        Connections.load(bad)
    with pytest.raises(ExecutionError, match="does not exist"):
        Connections.load(tmp_path / "missing.yaml")
    secrets = tmp_path / "leak.yaml"
    secrets.write_text(
        "connections:\n"
        "  a:\n"
        "    type: http\n"
        "    base_url: x\n"
        "    capabilities: ['*']\n"
        "    auth: {type: bearer, token: abc}\n",
        encoding="utf-8",
    )
    with pytest.raises(ExecutionError, match="token"):
        Connections.load(secrets)


def test_the_gateway_runs_through_connections(
    system: FakeSystem, synthetic: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PAY_KEY", "key-1")
    spec = synthetic.parent / "openapi" / "payments.yaml"
    catalog_dir = flowglyph.extract(spec).save(tmp_path / "catalog")
    file = tmp_path / "flowglyph.connections.yaml"
    file.write_text(CONNECTIONS.format(url=system.url), encoding="utf-8")
    system.script = answer(201, {"id": "INV-1"})
    gateway = Gateway(catalog_dir, executor=ConnectedExecutor(Connections.load(file)))
    invoice = {"vendor": "ACME", "amount": 1, "currency": "EUR", "reference": "R"}
    arguments = {"Idempotency-Key": "k", "body": invoice}
    first = gateway.run("createInvoice", arguments)
    assert first.status == "done"
    assert first.result["body"] == {"id": "INV-1"}
    assert gateway.run("createInvoice", arguments).status == "replayed"
    assert len([c for c in system.calls if c.method == "POST"]) == 1
    system.script = answer(500, {"message": "boom"})
    failed = gateway.run("createInvoice", {**arguments, "Idempotency-Key": "k2"})
    assert failed.status == "failed"
    assert "answered 500" in failed.errors[0]


def _capability(capability_id: str) -> Capability:
    return Capability(
        id=capability_id,
        kind="workflow",
        title="x",
        trigger=Trigger(channel="HTTP", address="GET /x"),
        source=Source(provider="uipath", artifact="x", location="x", source_hash="sha256:0"),
    )
