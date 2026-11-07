"""Reading requirements from the documents a process arrives in.

A process definition rarely comes as Markdown. It is a PDF or a Word document from the client,
a spreadsheet of steps, a CSV exported from a ticketing tool, or a folder with all of them.
`read_requirements` turns any of these into the text the planner works from: paragraphs as they
are, tables as Markdown tables, one section per sheet or file.
"""

import csv
import errno
import os
from collections.abc import Callable, Iterable, Iterator, Sequence
from io import StringIO
from pathlib import Path
from typing import Any, cast

from flowglyph.errors import FlowGlyphError

EXTRA = "pip install 'flowglyph[documents]'"
_TEXT = frozenset({".md", ".markdown", ".txt", ""})
_SEPARATED = {".csv": None, ".tsv": "\t"}
_LIBRARIES = {".pdf": "pypdf", ".docx": "python-docx", ".xlsx": "openpyxl", ".xlsm": "openpyxl"}
_ENCODINGS = ("utf-8-sig", "cp1252")
_HEADING = "Heading "


class DocumentError(FlowGlyphError):
    """A requirements document cannot be read."""


def read_requirements(path: Path) -> str:
    """The requirements in `path`, a document or a folder of documents, as text.

    Text and Markdown are taken as they are. PDF and Word documents give their paragraphs and
    tables; Excel workbooks and CSV files give Markdown tables, one section per sheet. A folder
    contributes every supported file in it, by name, each under a heading.

    Raises:
        DocumentError: If the format is not supported, the library that reads it is not
            installed, or the document holds no text.
        OSError: If the path does not exist or cannot be read.
    """
    if not path.exists():
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
    if path.is_file():
        return _document(path)
    documents = sorted(
        child for child in path.iterdir() if child.is_file() and _reader(child) is not None
    )
    if not documents:
        raise DocumentError(f"{path}: no document FlowGlyph can read; supported: {_supported()}")
    return "\n\n".join(f"# {document.name}\n\n{_document(document)}" for document in documents)


def supported_suffixes() -> tuple[str, ...]:
    """The file suffixes `read_requirements` reads, without the empty one."""
    return tuple(sorted((_TEXT | set(_SEPARATED) | set(_LIBRARIES)) - {""}))


def _document(path: Path) -> str:
    reader = _reader(path)
    if reader is None:
        what = path.suffix or "this file"
        raise DocumentError(f"{path}: {what} is not supported; {_supported()}")
    try:
        text = reader(path).strip()
    except ModuleNotFoundError as error:
        library = _LIBRARIES.get(path.suffix.lower(), error.name)
        raise DocumentError(f"reading {path.suffix} needs {library}: {EXTRA}") from error
    if not text:
        hint = "; a scanned PDF needs OCR first" if path.suffix.lower() == ".pdf" else ""
        raise DocumentError(f"{path}: no text found{hint}")
    return text


def _reader(path: Path) -> Callable[[Path], str] | None:
    suffix = path.suffix.lower()
    if suffix in _TEXT:
        return _text
    if suffix in _SEPARATED:
        return _separated
    return {".pdf": _pdf, ".docx": _docx, ".xlsx": _xlsx, ".xlsm": _xlsx}.get(suffix)


def _supported() -> str:
    return ", ".join(supported_suffixes())


def _text(path: Path) -> str:
    return _decode(path.read_bytes())


def _decode(data: bytes) -> str:
    """Text from `data`, UTF-8 or Windows-1252, with Unix line endings."""
    for encoding in _ENCODINGS[:-1]:
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode(_ENCODINGS[-1])
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _separated(path: Path) -> str:
    text = _decode(path.read_bytes())
    delimiter = _SEPARATED[path.suffix.lower()]
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    return _table(csv.reader(StringIO(text), delimiter=delimiter))


def _pdf(path: Path) -> str:
    from pypdf import PdfReader  # noqa: PLC0415

    reader = PdfReader(path)
    if reader.is_encrypted:
        raise DocumentError(f"{path}: the PDF is encrypted; remove the password first")
    return "\n\n".join(page.extract_text() for page in reader.pages)


def _docx(path: Path) -> str:
    import docx  # noqa: PLC0415
    from docx.table import Table  # noqa: PLC0415

    document = docx.Document(str(path))
    blocks: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            blocks.append(_table([[cell.text for cell in row.cells] for row in block.rows]))
        elif block.text.strip():
            style = block.style.name if block.style is not None else None
            blocks.append(_paragraph(block.text.strip(), style or ""))
    return "\n\n".join(blocks)


def _paragraph(text: str, style: str) -> str:
    if style == "Title":
        return f"# {text}"
    if style.startswith(_HEADING):
        level = style.removeprefix(_HEADING)
        return f"{'#' * int(level) if level.isdigit() else '#'} {text}"
    if style.startswith("List"):
        return f"- {text}"
    return text


def _xlsx(path: Path) -> str:
    from openpyxl import load_workbook  # noqa: PLC0415

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheets: list[str] = []
        for sheet in workbook.worksheets:
            rows = cast("Iterable[Sequence[Any]]", sheet.iter_rows(values_only=True))
            table = _table([_cell(value) for value in row] for row in rows)
            if table:
                sheets.append(f"## {sheet.title}\n\n{table}")
    finally:
        workbook.close()
    return "\n\n".join(sheets)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _table(rows: Iterable[Sequence[str]]) -> str:
    """Rows as a Markdown table, the first row as header, fully empty rows dropped."""
    kept = [[_clean(cell) for cell in row] for row in rows]
    kept = [row for row in kept if any(row)]
    if not kept:
        return ""
    width = max(len(row) for row in kept)
    lines: Iterator[str] = (
        "| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in kept
    )
    header = next(lines)
    return "\n".join([header, "|" + " --- |" * width, *lines])


def _clean(cell: str) -> str:
    return " ".join(cell.split()).replace("|", "\\|")
