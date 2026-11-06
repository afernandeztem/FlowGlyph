"""XML parsing for untrusted sources: documents that declare a DTD are refused."""

from pathlib import Path
from xml.etree import ElementTree as ET
from xml.parsers import expat

from flowglyph.errors import AdapterError

_LAST_CHUNK = True


def load_xml(path: Path) -> ET.Element:
    """Parse an XML file, refusing documents that declare a DTD.

    Raises:
        AdapterError: If the file is not well-formed XML or declares a DTD.
    """
    return parse_xml(path.read_bytes(), str(path))


def parse_xml(data: bytes, name: str) -> ET.Element:
    """Parse XML bytes, refusing documents that declare a DTD.

    Raises:
        AdapterError: If the data is not well-formed XML or declares a DTD.
    """
    _refuse_dtd(data, name)
    try:
        # ElementTree never resolves external entities, and with DTDs refused there are no
        # internal entities to expand, so this input is safe to parse.
        return ET.fromstring(data)  # noqa: S314
    except ET.ParseError as error:
        raise AdapterError(f"{name}: {error}") from error


def _refuse_dtd(data: bytes, name: str) -> None:
    """Scan the whole document with expat, which reports a DOCTYPE wherever it appears."""

    def refuse(*_: object) -> None:
        raise AdapterError(f"{name}: XML documents must not declare a DTD")

    scanner = expat.ParserCreate()
    scanner.StartDoctypeDeclHandler = refuse
    try:
        scanner.Parse(data, _LAST_CHUNK)
    except expat.ExpatError as error:
        raise AdapterError(f"{name}: {error}") from error
