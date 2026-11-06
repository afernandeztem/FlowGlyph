"""Run three SAP capabilities through the gateway and print what it decided."""

import tempfile
from pathlib import Path

from flowglyph.gateway import Gateway, Policy

HERE = Path(__file__).parent
CREATE = "sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/create"

with tempfile.TemporaryDirectory() as state:
    gateway = Gateway(HERE / "catalog", policy=Policy.load(HERE / "policy.yaml"), state_dir=state)
    invoice = {
        "body": {
            "CompanyCode": "1010",
            "InvoicingParty": "17300001",
            "SupplierInvoiceIDByInvcgParty": "INV-2291",
        }
    }
    first = gateway.run(CREATE, invoice)
    again = gateway.run(CREATE, invoice)
    print(f"create: {first.status}, then {again.status} (enforced by the {first.enforcement})")

    blocked = gateway.run(
        "sap/zbusinesspartner/BusinessPartner/block", {"BusinessPartner": "17300001"}
    )
    print(f"block: {blocked.status}, {blocked.reason}")

    held = gateway.run(
        "sap/ZSUPPLIER_INVOICE_SRV/Release", {"SupplierInvoice": "5100000123", "FiscalYear": "2026"}
    )
    why, _, how = (held.reason or "").partition("; ")
    print(f"release: {held.status}, {why}")
    print(f"  {how}")
