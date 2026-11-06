"""Regenerate the catalogs committed in `examples/`, exactly as their walkthroughs produce them.

Run with `make examples`. `tests/e2e/test_examples.py` runs the same functions and fails when a
committed catalog is out of date.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import flowglyph

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "examples"


def build_invoice_processing(target: Path) -> flowglyph.Catalog:
    """One catalog from a UiPath project and an OpenAPI document."""
    uipath = flowglyph.extract(FIXTURES / "synthetic" / "invoices")
    api = flowglyph.extract(FIXTURES / "openapi" / "payments.yaml")
    catalog = uipath.merge(api)
    catalog.save(target)
    return catalog


def build_sap_integration(target: Path) -> flowglyph.Catalog:
    """Extract the SAP sources, then extract again with the owners' overrides in place."""
    example = EXAMPLES / "sap-integration"
    with tempfile.TemporaryDirectory() as scratch:
        sources = Path(shutil.copytree(example / "sources", Path(scratch) / "sources"))
        first = flowglyph.extract(sources)
        shutil.copy(example / "overrides.yaml", sources / "flowglyph.overrides.yaml")
        catalog = flowglyph.extract(sources, previous=first.lock)
    catalog.save(target)
    return catalog


def main() -> None:
    """Rewrite every example catalog in place."""
    for name, build in (
        ("invoice-processing", build_invoice_processing),
        ("sap-integration", build_sap_integration),
    ):
        target = EXAMPLES / name / "catalog"
        shutil.rmtree(target, ignore_errors=True)
        catalog = build(target)
        sys.stdout.write(f"{target.relative_to(ROOT)}: {len(catalog)} capabilities\n")


if __name__ == "__main__":
    main()
