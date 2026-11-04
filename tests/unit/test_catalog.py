import shutil
from pathlib import Path

import pytest

import flowglyph
from flowglyph.catalog import Bump, diff_locks
from flowglyph.errors import CatalogError

MAIN = "uipath/Invoices/Main"


@pytest.fixture
def project(synthetic: Path, tmp_path: Path) -> Path:
    target = tmp_path / "invoices"
    shutil.copytree(synthetic / "invoices", target)
    return target


def edit(project: Path, old: str, new: str) -> None:
    main = project / "Main.xaml"
    text = main.read_text(encoding="utf-8")
    assert old in text
    main.write_text(text.replace(old, new, 1), encoding="utf-8")


def reextract(project: Path, before: flowglyph.Catalog) -> flowglyph.Catalog:
    return flowglyph.extract(project, previous=before.lock)


def test_unchanged_sources_keep_their_version(project: Path):
    first = flowglyph.extract(project)
    second = reextract(project, first)
    assert second.changes == ()
    assert second.lock == first.lock


def test_layout_changes_do_not_bump(project: Path):
    first = flowglyph.extract(project)
    edit(project, 'IdRef="LogMessage_1"', 'IdRef="LogMessage_9"')
    assert reextract(project, first).changes == ()


def test_documentation_change_is_a_patch(project: Path):
    first = flowglyph.extract(project)
    edit(project, "Path of the invoice PDF.", "Absolute path of the invoice PDF.")
    second = reextract(project, first)
    assert [(c.capability, c.bump) for c in second.changes] == [(MAIN, Bump.PATCH)]
    assert second.get(MAIN).version == "1.0.1"


def test_new_optional_input_is_minor(project: Path):
    first = flowglyph.extract(project)
    edit(
        project,
        '<x:Property Name="in_Threshold"',
        '<x:Property Name="in_Currency" Type="InArgument(x:String)" />'
        '<x:Property Name="in_Threshold"',
    )
    edit(
        project,
        'this:Main.in_Threshold="10000"',
        'this:Main.in_Threshold="10000" this:Main.in_Currency="EUR"',
    )
    assert reextract(project, first).get(MAIN).version == "1.1.0"


def test_new_required_input_is_major(project: Path):
    first = flowglyph.extract(project)
    edit(
        project,
        '<x:Property Name="in_Threshold"',
        '<x:Property Name="in_Vendor" Type="InArgument(x:String)" />'
        '<x:Property Name="in_Threshold"',
    )
    second = reextract(project, first)
    assert second.get(MAIN).version == "2.0.0"
    assert diff_locks(first.lock, second.lock)[0].bump is Bump.MAJOR


def test_removed_capabilities_are_reported(project: Path):
    first = flowglyph.extract(project)
    (project / "Steps" / "ValidateVendor.xaml").unlink()
    kinds = {c.capability: c.kind for c in reextract(project, first).changes}
    assert kinds["uipath/Invoices/Steps/ValidateVendor"] == "removed"


def test_overrides_declare_what_the_parser_can_only_guess(project: Path):
    (project / "flowglyph.overrides.yaml").write_text(
        f"""
capabilities:
  {MAIN}:
    description: Books a supplier invoice.
    idempotency: {{mode: key, key_fields: [in_InvoicePath], ttl_seconds: 86400}}
    security: {{approval_required: true}}
""",
        encoding="utf-8",
    )
    main = flowglyph.extract(project).get(MAIN)
    assert main.description == "Books a supplier invoice."
    assert main.idempotency.mode == "key"
    assert main.idempotency.key_fields == ("in_InvoicePath",)
    assert main.idempotency.provenance == "declared"
    assert main.idempotency.confidence == 1.0
    assert main.security.approval_required


def test_save_and_load_round_trip(project: Path, tmp_path: Path):
    catalog = flowglyph.extract(project)
    out = catalog.save(tmp_path / "out")
    loaded = flowglyph.load_catalog(out)
    assert loaded.capabilities == catalog.capabilities
    assert loaded.workflows == catalog.workflows
    assert loaded.lock == catalog.lock
    assert (out / "INDEX.md").is_file()
    assert (out / "capabilities" / "uipath_Invoices_Main.md").is_file()


def test_saving_twice_is_byte_identical(project: Path, tmp_path: Path):
    catalog = flowglyph.extract(project)
    first = catalog.save(tmp_path / "a")
    second = flowglyph.extract(project).save(tmp_path / "b")
    for path in sorted(first.rglob("*")):
        if path.is_file():
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes(), path


def test_stale_cards_are_removed_on_save(project: Path, tmp_path: Path):
    flowglyph.extract(project).save(tmp_path / "out")
    (project / "Steps" / "BookInvoice.xaml").unlink()
    flowglyph.extract(project).save(tmp_path / "out")
    assert not (tmp_path / "out" / "capabilities" / "uipath_Invoices_Steps_BookInvoice.md").exists()


def test_get_resolves_suffixes_and_reports_ambiguity(project: Path):
    catalog = flowglyph.extract(project)
    assert catalog.get("Steps/BookInvoice").id == "uipath/Invoices/Steps/BookInvoice"
    assert catalog.workflow("Main").capability == MAIN
    with pytest.raises(CatalogError, match="no capability"):
        catalog.get("Nope")


def test_search_filters(project: Path):
    catalog = flowglyph.extract(project)
    assert catalog.search("approval", limit=1)[0].id == "uipath/Invoices/Steps/RequestApproval"
    assert all(c.invocable for c in catalog.search("invoice", invocable=True))
    assert all(c.kind == "activity" for c in catalog.search("mail", kind="activity"))


def test_merge_combines_sources(project: Path, reframework: Path):
    merged = flowglyph.extract(project).merge(flowglyph.extract(reframework))
    assert merged.get(MAIN)
    assert merged.get("Framework/InitAllSettings")
    assert set(merged.lock.adapters) == {"uipath"}


def test_missing_paths_fail_clearly(tmp_path: Path):
    with pytest.raises(CatalogError, match="does not exist"):
        flowglyph.extract(tmp_path / "nope")
    with pytest.raises(CatalogError, match=r"catalog\.jsonl"):
        flowglyph.load_catalog(tmp_path)
