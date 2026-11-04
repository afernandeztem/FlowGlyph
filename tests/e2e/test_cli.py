import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flowglyph.cli.main import app

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
