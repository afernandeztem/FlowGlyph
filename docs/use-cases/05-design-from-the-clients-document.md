# 5. A robot from the client's document

**For:** solution architects and delivery teams who start from a process definition document.
**Takes:** one command and a model call. **Needs:** `pip install "flowglyph[cli,documents]"`
and a coding assistant you are signed in to, or an API key.

<img alt="The Word document in, the checked plan out." src="../assets/walkthrough-plan.gif" width="100%">

## The situation

The client sends the process definition: a Word document with a purpose, a table of steps and
their business rules, or a PDF, or a spreadsheet, or all three. The first week goes into
finding out which of the steps the estate already covers, which do not exist yet, and writing
the design. A model could draft that in a minute, if only it could be trusted not to invent a
workflow that sounds right.

## What you do

```bash
flowglyph extract ./handover -o catalog
flowglyph plan ./handover/supplier-invoice-pdd.docx catalog -o plan --via claude-code
flowglyph plan ./handover catalog -o plan --via claude-code        # the whole folder: PDF, Word, Excel, CSV
```

`--via` is whoever you already have: `claude-code`, `codex`, `gemini`, `cursor`, `anthropic`
or `openai-compatible` (OpenAI, Ollama, vLLM). The model sees the document and the candidate
functions; it never sees your sources.

## What you see

The Word document used here has a purpose section, a four-row steps table (check the vendor,
approval above 10,000 EUR, create the invoice keyed on the reference, archive the PDF) and a
list of inputs. The plan:

```text
Book emailed supplier invoices without creating duplicates, then archive the PDF
 Step               Capability                             Intent
 validate_vendor    uipath/Invoices/Steps/ValidateVendor   Check that the vendor on the invoice exists in our records.
 notify_purchasing  missing                                Notify purchasing that the vendor is unknown and stop processing the invoice.
 request_approval   uipath/Invoices/Steps/RequestApproval  Ask the finance approver for approval before booking a high-value invoice.
 create_invoice     openapi/Payments_API/createInvoice     Create the invoice in the payments system, keyed by the invoice reference so a retry never books it twice.
 archive_pdf        missing                                Archive the invoice PDF in the document store with a 10-year retention period.
  warning request_approval has side effects: run it with an idempotency key so retries are safe
Wrote plan/workflow.plan.yaml and plan/workflow.ir.yaml
```

The model proposed the steps; FlowGlyph checked every one against the catalog: the capability
exists, every required input is filled, each argument has the type the input declares, every
reference points to an earlier step. Two steps are **missing** and say so, because nothing in
the sources notifies purchasing or archives a PDF. The plan is at once the design, the gap
list and the estimate.

`workflow.ir.yaml` is the checked workflow in the Automation IR, with the business rule from
the document as the condition on the approval step and the invoice reference as the
idempotency key of the booking.

## What changes

The design starts from what exists, in the client's own words, on day one. What the estate
cannot do is named, not invented, so the gaps go straight into the backlog, and the resolved
part opens in Studio or a BPMN modeler ([use case 6](06-bpmn-and-xaml.md)).

## Telling it

- **Hook:** the client's Word document in, a checked design out, with the two steps nobody
  had built yet named as such.
- **Three points:** reads the document as it came (PDF, Word, Excel, CSV, a folder of them);
  uses only functions that exist, and proves it step by step; the model you already pay for,
  through its command line.
- **Demo:** the two-page PDD from this page, `flowglyph plan` with `--via claude-code`, then
  open `workflow.ir.yaml` and point at the `missing` steps.
- **Where:** LinkedIn for delivery and pre-sales teams, the UiPath Community Forum ("from PDD
  to Studio"), a dev.to post on "a planner that cannot hallucinate a capability".
