# Example: an SAP landscape

This example reads two kinds of SAP sources at once and takes them through every stage of
FlowGlyph: the catalog, the idempotency report, overrides, the LLM wiki and the gateway.

```
sources/
├── integration/          SAP Cloud Integration iFlows, unpacked as they are kept in git
│   ├── orders/           Orders_Inbound: HTTPS endpoint, calls Notify through ProcessDirect
│   ├── notify/           Notify_Customer: ProcessDirect endpoint, sends mail, records a Data Store entry
│   └── nightly-report/   Nightly_Stock_Report: timer, reads stock over OData
└── odata/                SAP OData $metadata: one V2 service, one V4 service
overrides.yaml            what the owners know, used in step 4
policy.yaml               what an agent may run, used in step 6
```

The sources are small synthetic samples, written for FlowGlyph's tests. Run every command from
this directory with `flowglyph[cli]` installed (`pip install "flowglyph[cli]"`, or prefix them
with `uv run` in a checkout). The committed `catalog/` is what step 4 leaves behind; to replay
the steps from the start, remove it first (`rm -rf catalog`) and restore it afterwards with
`git checkout catalog`.

## 1. What can be read

```console
$ flowglyph adapters
 Adapter  Version  Reads
 bpmn     0.1.0    Turns BPMN 2.0 processes into capabilities, with Camunda 7 and Camunda 8 extensions.
 n8n      0.1.0    Turns n8n workflows into capabilities, linked through their Execute Workflow nodes.
 openapi  0.1.0    Turns every operation of an OpenAPI 3.x document into an invocable capability.
 sap      0.1.0    Turns an SAP OData service's metadata into one capability per allowed operation.
 sap-cpi  0.1.0    Turns SAP Cloud Integration iFlows into capabilities, one per endpoint they expose.
 sbpa     0.1.0    Turns SAP Build Process Automation projects into processes, automations and decisions.
 uipath   0.1.0    Extracts capabilities and workflow graphs from a UiPath project.
```

By default every adapter is tried on every folder. `--adapter sap` or `--adapter sap-cpi` reads
only one kind of source.

## 2. The idempotency of every OData operation

The report is the catalog and nothing else: no files are written.

```console
$ flowglyph idempotency sources/odata --adapter sap
 Capability                                        Kind       Effects  Idempotency  Status
 sap/ZSUPPLIER_INVOICE_SRV/GetDuplicateCandidates  operation  RX       natural      safe
 sap/ZSUPPLIER_INVOICE_SRV/Release                 operation  rwdX     none         review
 sap/ZSUPPLIER_INVOICE_SRV/Supplier/query          operation  RX       natural      safe
 sap/ZSUPPLIER_INVOICE_SRV/Supplier/read           operation  RX       natural      safe
 sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/create  operation  WX       none         review
 sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/query   operation  RX       natural      safe
 sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/read    operation  RX       natural      safe
 sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/update  operation  WdX      natural      safe
 sap/zbusinesspartner/BusinessPartner/block        operation  rwdX     none         review
 sap/zbusinesspartner/BusinessPartner/create       operation  WX       none         review
 sap/zbusinesspartner/BusinessPartner/query        operation  RX       natural      safe
 sap/zbusinesspartner/BusinessPartner/read         operation  RX       natural      safe
 sap/zbusinesspartner/BusinessPartner/update       operation  WdX      natural      safe
 sap/zbusinesspartner/checkDuplicates              operation  RX       natural      safe
14 capabilities, 4 to review.
```

Each row follows OData semantics ([ADR-0006](../../docs/adr/0006-sap-odata-adapter.md)): reads
and `GET` functions are safe to retry; `PATCH` and `DELETE` leave the same state when repeated;
`POST` creates a new record every time, and an action could do anything, so those four rows
need someone who knows the service. The effects code reads `R`ead, `W`rite, `D`estroy,
e`X`ternal, upper case for yes and lower case when it may.

Add `--format csv`, `markdown` or `json` and `-o file` to hand the report to someone.

## 3. One catalog for the whole landscape

```console
$ flowglyph extract sources -o catalog
Extracted 16 invocable capabilities and 1 that cannot be run on their own into catalog
  warning …/Notify_Customer.iflw: the main process has no exception subprocess: a failure ends unhandled
  warning …/Orders_Inbound.iflw: HTTP receiver uses plain HTTP: http://legacy.example.com/stock
  info …/Orders_Inbound.iflw: HTTP receiver address is hard-coded; externalize http://legacy.example.com/stock
  warning …/Orders_Inbound.iflw: HTTP receiver http://legacy.example.com/stock has no request timeout
  info …/Orders_Inbound.iflw: CSRF protection is off on endpoint /orders
  warning …/Orders_Inbound.iflw: 'Keep original order' copies the whole body into a property, doubling memory
  warning …/Orders_Inbound.iflw: router 'Order type' has no default route
```

The warnings are design findings in the iFlows: things that work today and fail under load or
on the first error ([ADR-0007](../../docs/adr/0007-sap-cloud-integration-adapter.md)). The timer
iFlow is the one capability that cannot be run on its own: nothing can call it.

The ProcessDirect link between the two iFlows becomes a call:

```console
$ flowglyph inspect catalog
Nightly Stock Report RX natural
Orders Inbound RWX key
└── Notify Customer rWX conditional
```

`Orders Inbound` is `key` because the iFlow itself says so: it wraps its work in an idempotent
process call on the order number. FlowGlyph records that as *declared*, with a note saying where
it comes from, and does not second-guess it. `Notify Customer` is `conditional`: its Data Store
write rejects a repeated order number, so a retry is safe only if it runs before the mail is
sent; step 4 settles that. `flowglyph inspect catalog sap-cpi/Orders_Inbound`
shows the full card; the same cards are in [`catalog/capabilities/`](catalog/capabilities/).

## 4. Settle what the sources cannot say

[`overrides.yaml`](overrides.yaml) records what the owners of these processes know: the invoice
service rejects a repeated supplier reference, releasing an invoice twice changes nothing but
needs a person, and `Notify_Customer` deduplicates on its Data Store entry. FlowGlyph reads
overrides from `flowglyph.overrides.yaml` next to the sources, so put the file there and
extract again; the catalog's lock file versions what changed:

```console
$ cp overrides.yaml sources/flowglyph.overrides.yaml
$ flowglyph extract sources -o catalog
Extracted 16 invocable capabilities and 1 that cannot be run on their own into catalog
Capability                                        Change   Bump   Version
sap-cpi/Notify_Customer                           changed  minor  1.0.0 -> 1.1.0
sap/ZSUPPLIER_INVOICE_SRV/Release                 changed  minor  1.0.0 -> 1.1.0
sap/ZSUPPLIER_INVOICE_SRV/SupplierInvoice/create  changed  minor  1.0.0 -> 1.1.0

$ flowglyph idempotency catalog --review
 Capability                                   Kind       Effects  Idempotency  Status
 sap/zbusinesspartner/BusinessPartner/block   operation  rwdX     none         review
 sap/zbusinesspartner/BusinessPartner/create  operation  WX       none         review
2 capabilities, 2 to review.
```

Changing a capability's idempotency is a minor version: callers keep working, but what they
may assume changed. Two rows are left for the business partner team; this is the loop to repeat
until the list is empty.

The committed [`catalog/`](catalog/) is what these steps produce.

## 5. A wiki to keep the knowledge

```console
$ flowglyph wiki build catalog -o wiki
Wiki 29 pages in wiki
$ flowglyph wiki lint wiki
```

Every capability, iFlow and category gets a page. FlowGlyph writes the part above the
`<!-- flowglyph:notes -->` marker; below it, people or an LLM add what no source says (owners,
incidents, why a router has no default route), and rebuilding keeps it. `wiki/AGENTS.md` tells
an LLM how to maintain the wiki; `wiki lint` lists the design findings, the rows to review, and
broken links ([ADR-0009](../../docs/adr/0009-llm-wiki.md)).

## 6. Let an agent run it, safely

[`policy.yaml`](policy.yaml) denies blocking business partners, holds invoice releases for a
person, and holds anything destructive. [`demo_gateway.py`](demo_gateway.py) sends three
requests through the gateway with the dry-run executor:

```console
$ python demo_gateway.py
create: done, then replayed (enforced by the ledger)
block: denied, blocking a business partner is a decision for the credit team
release: approval_required, releasing an invoice lets it be paid
  a person must run `flowglyph approve …/catalog 'sap/ZSUPPLIER_INVOICE_SRV/Release#auto:…' --state …`
```

The second `create` with the same invoice is not run again: the ledger returns the first result,
because the override declared the body as the idempotency key. The same gateway serves agents
over MCP:

```console
$ flowglyph serve catalog --policy policy.yaml
```
