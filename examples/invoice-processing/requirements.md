# Supplier invoice intake

When an invoice arrives, check that the vendor exists in our records.

If the amount is above 10,000 EUR, ask the finance approver before going on.

Then create the invoice in the payments system, using the invoice reference so that a retry
never books it twice, and archive the PDF.
