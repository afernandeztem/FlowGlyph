import csv
import io
import json
import shutil
from pathlib import Path

import flowglyph
from flowglyph import report


def test_rows_classify_what_still_needs_a_person(synthetic: Path):
    catalog = flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml")
    statuses = {row.id.rsplit("/", 1)[-1]: row.status for row in report.rows(catalog)}
    assert statuses["listInvoices"] == "safe"
    assert statuses["createInvoice"] == "keyed"
    assert statuses["executePayment"] == "review"


def test_what_cannot_run_on_its_own_has_nothing_to_review(reframework: Path):
    rows = report.rows(flowglyph.extract(reframework), kinds=["activity"])
    create_file = next(row for row in rows if row.id == "uipath/activity/CreateFile")
    assert create_file.side_effects
    assert {row.status for row in rows} == {"n/a"}


def test_filters(synthetic: Path, reframework: Path):
    catalog = flowglyph.extract(synthetic / "invoices").merge(flowglyph.extract(reframework))
    workflows = report.rows(catalog, kinds=["workflow"])
    assert workflows
    assert all(row.kind == "workflow" for row in workflows)
    assert all(row.side_effects for row in report.rows(catalog, side_effects_only=True))
    assert all(row.status == "review" for row in report.rows(catalog, statuses=["review"]))
    assert not report.rows(catalog, providers=["sap"])


def test_formats(synthetic: Path):
    catalog = flowglyph.extract(synthetic.parent / "openapi" / "payments.yaml")
    selected = report.rows(catalog)
    assert json.loads(report.render(selected, "json"))[0]["id"] == selected[0].id
    parsed = list(csv.DictReader(io.StringIO(report.render(selected, "csv"))))
    assert len(parsed) == len(selected)
    markdown = report.render(selected, "markdown")
    assert markdown.startswith("# Idempotency report")
    assert "| `openapi/Payments_API/createInvoice` |" in markdown


def test_declaring_an_override_settles_the_review(synthetic: Path, tmp_path: Path):
    project = tmp_path / "invoices"
    shutil.copytree(synthetic / "invoices", project)
    main = "uipath/Invoices/Main"
    before = {row.id: row.status for row in report.rows(flowglyph.extract(project))}
    assert before[main] == "review"
    (project / "flowglyph.overrides.yaml").write_text(
        f"capabilities:\n  {main}:\n    idempotency: {{mode: key, key_fields: [in_InvoicePath]}}\n"
    )
    after = {row.id: row.status for row in report.rows(flowglyph.extract(project))}
    assert after[main] == "declared"
