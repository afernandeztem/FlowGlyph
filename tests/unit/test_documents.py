"""Requirements read from PDF, Word, Excel, CSV and text documents, and from folders of them."""

import sys
from pathlib import Path

import docx
import openpyxl
import pytest

from flowglyph.planner.documents import DocumentError, read_requirements, supported_suffixes


def pdf_with(lines: list[str]) -> bytes:
    """A one-page PDF whose only content is `lines`, each on its own text line."""
    shown = " ".join(f"({line}) Tj T*" for line in lines)
    content = f"BT /F1 12 Tf 72 720 Td 14 TL {shown} ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = "%PDF-1.4\n"
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def test_text_and_markdown_are_read_as_they_are(tmp_path: Path):
    requirements = tmp_path / "requirements.md"
    requirements.write_text("# Intake\n\nCheck the vendor.\n", encoding="utf-8")
    assert read_requirements(requirements) == "# Intake\n\nCheck the vendor."


def test_windows_encoded_text_is_still_read(tmp_path: Path):
    requirements = tmp_path / "steps.txt"
    requirements.write_bytes("Approve above 10.000 €\r\nThen book it.".encode("cp1252"))
    assert read_requirements(requirements) == "Approve above 10.000 €\nThen book it."


def test_pdf_pages_give_their_text(tmp_path: Path):
    document = tmp_path / "pdd.pdf"
    document.write_bytes(pdf_with(["Supplier invoice intake", "Check that the vendor exists."]))
    text = read_requirements(document)
    assert "Supplier invoice intake" in text
    assert "Check that the vendor exists." in text


def test_a_pdf_without_text_is_refused_with_a_hint(tmp_path: Path):
    document = tmp_path / "scan.pdf"
    document.write_bytes(pdf_with([]))
    with pytest.raises(DocumentError, match="no text found; a scanned PDF needs OCR"):
        read_requirements(document)


def test_word_headings_lists_and_tables_become_markdown(tmp_path: Path):
    source = docx.Document()
    source.add_heading("Supplier invoice intake", level=1)
    source.add_paragraph("When an invoice arrives, check that the vendor exists.")
    source.add_paragraph("Ask finance above 10,000 EUR", style="List Bullet")
    table = source.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Step", "System"
    table.rows[1].cells[0].text, table.rows[1].cells[1].text = "Create invoice", "SAP | FI"
    source.add_paragraph("")
    document = tmp_path / "pdd.docx"
    source.save(str(document))
    assert read_requirements(document) == (
        "# Supplier invoice intake\n\n"
        "When an invoice arrives, check that the vendor exists.\n\n"
        "- Ask finance above 10,000 EUR\n\n"
        "| Step | System |\n| --- | --- |\n| Create invoice | SAP \\| FI |"
    )


def test_excel_sheets_become_one_table_each(tmp_path: Path):
    workbook = openpyxl.Workbook()
    steps = workbook.active
    assert steps is not None
    steps.title = "Steps"
    steps.append(["Step", "Amount"])
    steps.append([None, None])
    steps.append(["Create invoice", 10000.0])
    rules = workbook.create_sheet("Rules")
    rules.append(["Threshold", 10000.5])
    workbook.create_sheet("Empty")
    document = tmp_path / "steps.xlsx"
    workbook.save(document)
    assert read_requirements(document) == (
        "## Steps\n\n| Step | Amount |\n| --- | --- |\n| Create invoice | 10000 |\n\n"
        "## Rules\n\n| Threshold | 10000.5 |\n| --- | --- |"
    )


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("steps.csv", "Step,System\nCreate invoice,SAP\n"),
        ("steps.csv", "Step;System\nCreate invoice;SAP\n"),
        ("steps.tsv", "Step\tSystem\nCreate invoice\tSAP\n"),
    ],
)
def test_separated_values_become_a_table(tmp_path: Path, name: str, content: str):
    document = tmp_path / name
    document.write_text(content, encoding="utf-8")
    expected = "| Step | System |\n| --- | --- |\n| Create invoice | SAP |"
    assert read_requirements(document) == expected


def test_a_folder_reads_every_supported_file_under_its_name(tmp_path: Path):
    (tmp_path / "b-steps.csv").write_text("Step\nCreate invoice\n", encoding="utf-8")
    (tmp_path / "a-process.md").write_text("Book invoices.", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    (tmp_path / "sub").mkdir()
    assert read_requirements(tmp_path) == (
        "# a-process.md\n\nBook invoices.\n\n# b-steps.csv\n\n| Step |\n| --- |\n| Create invoice |"
    )


def test_a_folder_without_documents_is_an_error(tmp_path: Path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    with pytest.raises(DocumentError, match="no document FlowGlyph can read"):
        read_requirements(tmp_path)


def test_an_unsupported_format_names_the_supported_ones(tmp_path: Path):
    document = tmp_path / "process.pptx"
    document.write_bytes(b"PK")
    with pytest.raises(DocumentError, match=r"\.pptx is not supported; .*\.docx.*\.pdf"):
        read_requirements(document)


def test_a_missing_path_is_an_os_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match=r"nope\.pdf"):
        read_requirements(tmp_path / "nope.pdf")


def test_a_missing_library_says_which_extra_installs_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    document = tmp_path / "pdd.pdf"
    document.write_bytes(pdf_with(["anything"]))
    monkeypatch.setitem(sys.modules, "pypdf", None)
    with pytest.raises(DocumentError, match=r"reading \.pdf needs pypdf: pip install"):
        read_requirements(document)


def test_supported_suffixes_are_the_documented_ones():
    assert supported_suffixes() == (
        ".csv", ".docx", ".markdown", ".md", ".pdf", ".tsv", ".txt", ".xlsm", ".xlsx"
    )  # fmt: skip
