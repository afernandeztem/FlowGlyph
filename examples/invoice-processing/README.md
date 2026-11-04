# Example: supplier invoice intake

This example plans and serves a workflow over two kinds of sources at once: a UiPath project
and an OpenAPI document. It uses the sample sources shipped in `tests/fixtures/`.

## 1. Build one catalog from both sources

```python
import flowglyph

uipath = flowglyph.extract("tests/fixtures/synthetic/invoices")
api = flowglyph.extract("tests/fixtures/openapi/payments.yaml")
uipath.merge(api).save("examples/invoice-processing/catalog")
```

## 2. Plan the workflow from the requirements

Needs `pip install "flowglyph[llm]"` and Anthropic credentials (`ANTHROPIC_API_KEY` or
`ant auth login`).

```bash
flowglyph plan examples/invoice-processing/requirements.md examples/invoice-processing/catalog \
  -o examples/invoice-processing/out
```

The planner shortlists candidate capabilities with BM25, asks Claude for a plan, and checks
every step against the catalog. Expect three resolved steps (validate vendor, request approval
above the threshold, create invoice with the reference as idempotency key) and one step marked
**missing**: nothing in these sources archives a PDF. The planner reports the gap instead of
inventing a capability for it.

`out/workflow.plan.yaml` is the model's proposal; `out/workflow.ir.yaml` is the checked
workflow IR with its problems, gaps and warnings.

## 3. Serve it to an agent with a policy

```bash
flowglyph serve examples/invoice-processing/catalog --policy examples/invoice-processing/policy.yaml
```

The policy denies payments outright and holds anything destructive for a person to approve.
