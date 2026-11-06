"""The examples work as their READMEs say, and their committed catalogs are current."""

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
BUILD: dict[str, Any] = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"))


def _files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and ".flowglyph" not in path.parts
    }


@pytest.mark.parametrize("name", ["invoice-processing", "sap-integration"])
def test_committed_catalogs_are_current(name: str, tmp_path: Path):
    build: Callable[[Path], object] = BUILD[f"build_{name.replace('-', '_')}"]
    build(tmp_path / "catalog")
    committed = ROOT / "examples" / name / "catalog"
    assert _files(tmp_path / "catalog") == _files(committed), "run `make examples`"


def test_sap_overrides_version_what_they_settle(tmp_path: Path):
    catalog = BUILD["build_sap_integration"](tmp_path / "catalog")
    assert [(change.capability, change.new_version) for change in catalog.changes] == [
        ("sap-cpi/Notify_Customer", "1.1.0"),
        ("sap/ZSUPPLIER_INVOICE_SRV/Release", "1.1.0"),
        ("sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/create", "1.1.0"),
    ]


def test_sap_gateway_demo(capsys: pytest.CaptureFixture[str]):
    runpy.run_path(str(ROOT / "examples" / "sap-integration" / "demo_gateway.py"))
    output = capsys.readouterr().out
    assert "create: done, then replayed (enforced by the ledger)" in output
    assert "block: denied, blocking a business partner" in output
    assert "release: approval_required, releasing an invoice lets it be paid" in output
