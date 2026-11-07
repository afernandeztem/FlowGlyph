"""The examples work as their READMEs say, and their committed catalogs are current."""

import runpy
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import flowglyph

ROOT = Path(__file__).parents[2]
BUILD: dict[str, Any] = runpy.run_path(str(ROOT / "scripts" / "build_examples.py"))


def _files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and ".flowglyph" not in path.parts
    }


@pytest.mark.parametrize("name", ["invoice-processing", "sap-integration", "uipath-reframework"])
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


def test_uipath_overrides_version_what_they_settle(tmp_path: Path):
    catalog = BUILD["build_uipath_reframework"](tmp_path / "catalog")
    assert [(change.capability, change.new_version) for change in catalog.changes] == [
        ("uipath/ReFrameWork/Framework/GetAppCredentials", "1.1.0"),
        ("uipath/ReFrameWork/Framework/GetTransactionData", "1.1.0"),
        ("uipath/ReFrameWork/Framework/SetTransactionStatus", "1.1.0"),
        ("uipath/ReFrameWork/Main", "1.1.0"),
    ]


def test_uipath_patch_changes_effects_without_breaking_callers(tmp_path: Path):
    example = ROOT / "examples" / "uipath-reframework"
    committed = flowglyph.load_catalog(example / "catalog")
    sources = shutil.copytree(example / "sources", tmp_path / "my-process")
    shutil.copy(example / "overrides.yaml", sources / "flowglyph.overrides.yaml")
    patch = (example / "add-kill-process.patch").read_text(encoding="utf-8")
    target = sources / "ReFrameWork" / "Framework" / "KillAllProcesses.xaml"
    added = next(line[1:] for line in patch.splitlines() if line.startswith("+    <ui:KillProcess"))
    anchor = 'Message="Killing processes..." />'
    target.write_text(
        target.read_text(encoding="utf-8").replace(anchor, anchor + "\n" + added, 1),
        encoding="utf-8",
    )
    changes = flowglyph.extract(sources, previous=committed.lock).changes
    assert {(c.capability, c.kind, c.bump.name) for c in changes} == {
        ("uipath/ReFrameWork/Framework/KillAllProcesses", "changed", "MINOR"),
        ("uipath/ReFrameWork/Framework/SetTransactionStatus", "changed", "MINOR"),
        ("uipath/ReFrameWork/Main", "changed", "MINOR"),
        ("uipath/activity/KillProcess", "added", "MINOR"),
    }


def test_uipath_gateway_demo(capsys: pytest.CaptureFixture[str]):
    runpy.run_path(str(ROOT / "examples" / "uipath-reframework" / "demo_gateway.py"))
    output = capsys.readouterr().out
    assert "take an item: done, retried: replayed" in output
    assert "set its status: done, again: replayed" in output
    assert "run the tests: denied" in output
    assert "start the process: approval_required" in output
