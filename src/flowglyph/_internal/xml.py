from pathlib import Path
from xml.etree import ElementTree as ET

from flowglyph.errors import AdapterError


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
    if b"<!DOCTYPE" in data[:4096].upper():
        raise AdapterError(f"{name}: XML documents must not declare a DTD")
    try:
        # ElementTree never resolves external entities, and the bundled expat (2.4.1+)
        # limits entity expansion, so with DTDs rejected above this input is safe to parse.
        return ET.fromstring(data)  # noqa: S314
    except ET.ParseError as error:
        raise AdapterError(f"{name}: {error}") from error
