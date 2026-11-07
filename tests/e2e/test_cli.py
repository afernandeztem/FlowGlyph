import getpass
import json
import shlex
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

import flowglyph
from flowglyph.cli.main import app
from flowglyph.gateway import Gateway

runner = CliRunner()


@pytest.fixture
def project(synthetic: Path, tmp_path: Path) -> Path:
    target = tmp_path / "invoices"
    shutil.copytree(synthetic / "invoices", target)
    return target


def invoke(*args: str | Path) -> tuple[int, str]:
    result = runner.invoke(app, [str(arg) for arg in args], terminal_width=200)
    return result.exit_code, result.output


def test_version():
    code, output = invoke("--version")
    assert code == 0
    assert output.startswith("flowglyph ")


def test_extract_validate_inspect_search(project: Path, tmp_path: Path):
    out = tmp_path / "out"
    code, output = invoke("extract", project, "-o", out)
    assert code == 0, output
    assert "Extracted 4 invocable capabilities" in output
    assert "Steps/Missing.xaml" in output

    code, output = invoke("validate", out)
    assert code == 0, output

    code, output = invoke("inspect", out)
    assert code == 0
    assert "Main" in output
    assert "ValidateVendor" in output
    assert "? Steps/Missing.xaml" in output

    code, output = invoke("inspect", out, "Steps/BookInvoice")
    assert code == 0
    assert "BookInvoice" in output
    assert "in_Invoice" in output

    code, output = invoke("search", out, "approval", "--invocable")
    assert code == 0
    assert "uipath/Invoices/Steps/RequestApproval" in output


def test_second_extract_reports_versions(project: Path, tmp_path: Path):
    out = tmp_path / "out"
    invoke("extract", project, "-o", out)
    before = tmp_path / "before.lock"
    shutil.copy(out / "flowglyph.lock", before)
    main = project / "Main.xaml"
    main.write_text(
        main.read_text().replace(
            '<x:Property Name="in_Threshold"',
            '<x:Property Name="in_Vendor" Type="InArgument(x:String)" />'
            '<x:Property Name="in_Threshold"',
        )
    )
    code, output = invoke("extract", project, "-o", out)
    assert code == 0
    assert "1.0.0 -> 2.0.0" in output

    code, output = invoke("diff", before, out, "--fail-on", "major")
    assert code == 1
    assert "major" in output
    code, _ = invoke("diff", before, out)
    assert code == 0


def test_validate_reports_broken_catalogs(project: Path, tmp_path: Path):
    out = tmp_path / "out"
    invoke("extract", project, "-o", out)
    catalog = out / "catalog.jsonl"
    lines = [line for line in catalog.read_text().splitlines() if '"ValidateVendor"' not in line]
    catalog.write_text("\n".join(lines) + "\n")
    code, output = invoke("validate", out)
    assert code == 1
    assert "references unknown uipath/Invoices/Steps/ValidateVendor" in output


def test_errors_are_reported_without_tracebacks(tmp_path: Path):
    code, output = invoke("extract", tmp_path / "missing")
    assert code == 2
    assert "does not exist" in output
    assert "Traceback" not in output


def test_strict_fails_on_parse_errors(synthetic: Path, tmp_path: Path):
    source = tmp_path / "broken"
    source.mkdir()
    shutil.copy(synthetic / "doctype.xaml", source)
    code, _ = invoke("extract", source, "-o", tmp_path / "out", "--strict")
    assert code == 1


def test_people_approve_held_runs_from_the_command_line(synthetic: Path, tmp_path: Path):
    from flowglyph.gateway import Gateway  # noqa: PLC0415

    out = tmp_path / "out"
    invoke("extract", synthetic.parent / "openapi" / "payments.yaml", "-o", out)
    gateway = Gateway(out)
    held = gateway.run("deleteInvoice", {"invoiceId": "7"}, idempotency_key="cleanup-7")
    assert held.idempotency_key is not None

    code, output = invoke("approvals", out)
    assert code == 0
    assert held.idempotency_key in output
    assert 'invoiceId="7"' in output, "a person sees what they approve"

    code, output = invoke("approve", out, held.idempotency_key)
    assert code == 0, output
    assert gateway.run("deleteInvoice", {"invoiceId": "7"}, idempotency_key="cleanup-7").ok
    entries = [json.loads(line) for line in gateway.audit.path.read_text().splitlines()]
    approval = next(entry for entry in entries if entry["event"] == "approve")
    assert approval["actor"] == getpass.getuser()

    code, output = invoke("approve", out, held.idempotency_key)
    assert code == 1
    assert "no run is waiting" in output


def test_plan_writes_the_proposal_and_the_ir(
    project: Path, synthetic: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from flowglyph.planner import claude  # noqa: PLC0415
    from flowglyph.planner.model import (  # noqa: PLC0415
        Plan,
        PlannedArgument,
        PlannedInput,
        PlannedStep,
    )

    proposal = Plan(
        goal="Book invoice",
        inputs=[PlannedInput(name="invoice", type="object", description="Invoice")],
        steps=[
            PlannedStep(
                id="book",
                intent="Book the invoice",
                capability="uipath/Invoices/Steps/BookInvoice",
                arguments=[
                    PlannedArgument(name="in_Invoice", source="workflow_input", value="invoice")
                ],
                after=[],
                condition=None,
            ),
            PlannedStep(
                id="notify",
                intent="Tell the vendor",
                capability=None,
                arguments=[],
                after=["book"],
                condition=None,
            ),
        ],
        assumptions=[],
    )

    class Scripted:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def propose(self, *_args: object) -> Plan:
            return proposal

    monkeypatch.setattr(claude, "ClaudePlanModel", Scripted)
    requirements = tmp_path / "requirements.md"
    requirements.write_text("Book the invoice and tell the vendor.")
    out = tmp_path / "plan"
    code, output = invoke("plan", requirements, project, "-o", out)
    assert code == 0, output
    assert "missing" in output
    assert (out / "workflow.plan.yaml").is_file()
    assert "needs attention" in (out / "workflow.ir.yaml").read_text()


def test_missing_extras_name_the_exact_install_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    import importlib  # noqa: PLC0415

    real_import = importlib.import_module

    def without_mcp(name: str, package: str | None = None) -> object:
        if name.startswith("flowglyph.gateway"):
            raise ModuleNotFoundError("No module named 'mcp'", name="mcp")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", without_mcp)
    code, output = invoke("serve", tmp_path)
    assert code == 2
    assert "pip install 'flowglyph[mcp]'" in output


def test_adapters_are_listed():
    code, output = invoke("adapters")
    assert code == 0
    for name in ("uipath", "openapi", "sap"):
        assert name in output


def test_idempotency_report_on_its_own(synthetic: Path, tmp_path: Path):
    code, output = invoke("idempotency", synthetic.parent / "sap", "--review")
    assert code == 0
    assert "sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/create" in output
    assert "query" not in output

    target = tmp_path / "report.csv"
    code, _ = invoke("idempotency", synthetic, "-f", "csv", "-o", target, "--adapter", "uipath")
    assert code == 0
    assert target.read_text().startswith("id,kind,provider")


def test_wiki_commands(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    code, output = invoke("wiki", "build", project, "-o", root)
    assert code == 0, output
    assert "ingest |" in output
    code, output = invoke("wiki", "lint", root)
    assert code == 0
    assert "declare its idempotency" in output
    code, _ = invoke("wiki", "lint", root, "--strict")
    assert code == 1
    code, output = invoke("wiki", "lint", tmp_path)
    assert code == 2


def test_diagnostics_keep_bracketed_expressions(project: Path, tmp_path: Path):
    main = project / "Main.xaml"
    text = main.read_text(encoding="utf-8")
    main.write_text(
        text.replace(
            'WorkflowFileName="Steps\\BookInvoice.xaml"', 'WorkflowFileName="[in_target]"'
        ),
        encoding="utf-8",
    )
    code, output = invoke("extract", project, "-o", tmp_path / "out")
    assert code == 0, output
    assert "by the expression [in_target]" in output


def test_the_suggested_approval_command_approves_the_run(
    synthetic: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    catalog_dir = flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml").save(
        tmp_path / "my catalog"
    )
    gateway = Gateway(catalog_dir, state_dir=tmp_path / "state")
    delete = "openapi/Payments_API/deleteInvoice"
    held = gateway.run(delete, {"invoiceId": "INV-118"}, idempotency_key="it's-118")
    assert held.reason is not None
    command = shlex.split(held.reason.split("`")[1])
    assert command[:2] == ["flowglyph", "approve"]
    monkeypatch.chdir(tmp_path)
    code, output = invoke(*command[1:])
    assert code == 0, output
    assert gateway.run(delete, {"invoiceId": "INV-118"}, idempotency_key="it's-118").ok


def test_serve_checks_connection_credentials_before_starting(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("PAY_TOKEN", raising=False)
    catalog_dir = flowglyph.extract(project).save(tmp_path / "catalog")
    connections = tmp_path / "flowglyph.connections.yaml"
    connections.write_text(
        "connections:\n"
        "  payments:\n"
        "    type: http\n"
        "    base_url: https://api.example.com\n"
        "    auth: {type: bearer, token_env: PAY_TOKEN}\n"
        "    capabilities: ['openapi/*']\n",
        encoding="utf-8",
    )
    code, output = invoke("serve", catalog_dir, "--connections", connections)
    assert code == 2
    assert "set these environment variables before serving: PAY_TOKEN" in output
    code, output = invoke("serve", catalog_dir, "--connections", tmp_path / "nope.yaml")
    assert code == 2
    assert "does not exist" in output


def test_compile_prints_or_writes_and_reports_what_it_could_not_carry(
    project: Path, tmp_path: Path
):
    catalog_dir = flowglyph.extract(project).save(tmp_path / "catalog")
    code, output = invoke("compile", catalog_dir, "uipath/Invoices/Main", "--to", "bpmn")
    assert code == 0, output
    assert "<bpmn:definitions" in output
    assert "conditions are copied as written" in output
    out = tmp_path / "Main.xaml"
    code, output = invoke("compile", catalog_dir, "Main", "--to", "xaml", "-o", out)
    assert code == 0, output
    assert out.read_text(encoding="utf-8").startswith('<?xml version="1.0" encoding="utf-8"?>')
    code, output = invoke("compile", catalog_dir, "--to", "bpmn")
    assert code == 2
    assert "name the workflow to compile" in output
