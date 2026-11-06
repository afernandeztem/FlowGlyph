---
id: "uipath/activity/Sequence"
kind: "activity"
category: "control"
version: "1.0.0"
effects: "none"
idempotency: "natural"
invocable: false
---

# Sequence

Validate an invoice and book it, asking for approval above the threshold.

- **Source:** `Main.xaml` (uipath)
- **Effects:** reads: no, mutates state: no, destructive: no, external: no
- **Idempotency:** natural, safe to retry (inferred, confidence 0.8)

## Inputs

None.

## Used in

- `Main.xaml`
- `Steps/BookInvoice.xaml`
- `Steps/RequestApproval.xaml`
- `Steps/ValidateVendor.xaml`

## Contract

```json
{
  "input": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "output": {
    "type": "object",
    "properties": {}
  }
}
```
