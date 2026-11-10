import shutil
from pathlib import Path

import pytest

import flowglyph
from flowglyph import wiki

MAIN = "capabilities/uipath_Invoices_Main.md"
BOOK = "capabilities/uipath_Invoices_Steps_BookInvoice.md"


@pytest.fixture
def project(synthetic: Path, tmp_path: Path) -> Path:
    target = tmp_path / "sources"
    shutil.copytree(synthetic / "invoices", target / "invoices")
    shutil.copytree(synthetic.parent / "sap", target / "sap")
    return target


def build(project: Path, root: Path) -> wiki.BuildResult:
    previous = root / wiki.DATA_DIRECTORY / "flowglyph.lock"
    catalog = flowglyph.extract(project, previous=previous if previous.is_file() else None)
    return wiki.build_wiki(catalog, root, subject="sources")


def test_the_wiki_has_the_llm_wiki_layers(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    result = build(project, root)
    for name in ("AGENTS.md", "index.md", "log.md", "overview.md", MAIN):
        assert (root / name).is_file(), name
    assert (root / wiki.DATA_DIRECTORY / "catalog.jsonl").is_file()
    assert (root / "sources" / "sap_ZSUPPLIER_INVOICE_SRV.md").is_file()
    assert result.log_entry.startswith("## [")
    assert "ingest | sources" in result.log_entry
    page = (root / MAIN).read_text()
    assert "## Steps" in page
    assert "](../categories/workflow.md)" in page
    assert wiki.NOTES_MARKER in page
    used_by = (root / BOOK).read_text()
    assert "## Used by" in used_by
    assert "[Main](uipath_Invoices_Main.md)" in used_by
    index = (root / "index.md").read_text()
    assert "(capabilities/sap_ZSUPPLIER_INVOICE_SRV_SupplierInvoice_create.md)" in index


def test_rebuilding_keeps_notes_and_the_schema(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    page = root / MAIN
    page.write_text(page.read_text() + "\nOwned by Accounts Payable. Runs at 07:00.\n")
    (root / "AGENTS.md").write_text("# Our own rules\n")
    build(project, root)
    assert "Owned by Accounts Payable. Runs at 07:00." in page.read_text()
    assert (root / "AGENTS.md").read_text() == "# Our own rules\n"


def test_the_log_is_append_only_and_records_changes(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    main = project / "invoices" / "Main.xaml"
    main.write_text(
        main.read_text().replace("Path of the invoice PDF.", "Absolute path of the PDF.")
    )
    build(project, root)
    log = (root / "log.md").read_text()
    assert log.count("] ingest | sources") == 2
    assert "patch change: [uipath/Invoices/Main]" in log
    assert "1.0.0 -> 1.0.1" in log


def test_retired_pages_go_unless_they_have_notes(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    noted = root / BOOK
    noted.write_text(noted.read_text() + "\nReplaced by the ERP integration in 2027.\n")
    (project / "invoices" / "Steps" / "BookInvoice.xaml").unlink()
    (project / "invoices" / "Steps" / "RequestApproval.xaml").unlink()
    result = build(project, root)
    assert not (root / "capabilities" / "uipath_Invoices_Steps_RequestApproval.md").exists()
    kept = noted.read_text()
    assert "Removed from the sources" in kept
    assert "Replaced by the ERP integration in 2027." in kept
    assert BOOK in result.removed


def test_lint_reports_what_needs_attention(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    (root / "overview.md").write_text((root / "overview.md").read_text() + "\n[gone](nope.md)\n")
    issues = wiki.lint_wiki(root)
    messages = {(issue.page, issue.message) for issue in issues}
    assert (MAIN, "has side effects and no retry guarantee: declare its idempotency") in messages
    assert (MAIN, "invokes something that is not in the sources: Steps/Missing.xaml") in messages
    assert ("overview.md", "broken link to nope.md") in messages
    assert not [i for i in issues if i.page == "AGENTS.md"], "links inside code are examples"
    assert "] lint | " in (root / "log.md").read_text()


def test_every_generated_link_resolves(project: Path, reframework: Path, tmp_path: Path):
    shutil.copytree(reframework, project / "reframework")
    root = tmp_path / "wiki"
    build(project, root)
    assert not [issue for issue in wiki.lint_wiki(root) if issue.level == "error"]


def test_pages_people_wrote_themselves_are_left_alone(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    runbook = root / "capabilities" / "my-runbook.md"
    runbook.write_text("# Month-end runbook\n\nWritten by hand.\n")
    result = build(project, root)
    assert runbook.read_text() == "# Month-end runbook\n\nWritten by hand.\n"
    assert result.removed == ()


def test_a_page_kept_for_its_notes_is_retired_once(project: Path, tmp_path: Path):
    root = tmp_path / "wiki"
    build(project, root)
    noted = root / BOOK
    noted.write_text(noted.read_text() + "\nReplaced by the ERP integration in 2027.\n")
    (project / "invoices" / "Steps" / "BookInvoice.xaml").unlink()
    assert BOOK in build(project, root).removed
    kept = noted.read_text()
    assert BOOK not in build(project, root).removed
    assert noted.read_text() == kept
