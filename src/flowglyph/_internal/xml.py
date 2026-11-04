from pathlib import Path
from xml.etree import ElementTree as ET

from flowglyph.errors import AdapterError


def load_xml(path: Path) -> ET.Element:
    """Parse an XML file, refusing documents that declare a DTD.

    Raises:
        AdapterError: If the file is not well-formed XML or declares a DTD.
    """
    data = path.read_bytes()
    if b"<!DOCTYPE" in data[:4096].upper():
        raise AdapterError(f"{path}: XML documents must not declare a DTD")
    try:
        # ElementTree never resolves external entities, and the bundled expat (2.4.1+)
        # limits entity expansion, so with DTDs rejected above this input is safe to parse.
        return ET.fromstring(data)  # noqa: S314
    except ET.ParseError as error:
        raise AdapterError(f"{path}: {error}") from error
