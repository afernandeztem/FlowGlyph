# 4. An agent that cannot break the rules

**For:** AI platform teams, security, whoever is asked "can the agent run our robots?".
**Takes:** one policy file and one command. **Needs:** `pip install "flowglyph[mcp]"`.

<img alt="Four calls through the gateway: done, replayed, denied, approval required." src="../assets/walkthrough-serve.gif" width="100%">

## The situation

Agents are good at finding the function that does what they want. The risk is the rest: a
retry that books an invoice twice, a call nobody approved, an action that deletes, a run nobody
can account for later. Giving an agent the vendor's API directly leaves every one of those to
the model's judgement. Giving it nothing leaves the automations unused.

## What you do

```yaml
# policy.yaml: the first matching rule decides
default: allow
rules:
  - capabilities: "sap/zbusinesspartner/BusinessPartner/block"
    action: deny
    reason: blocking a business partner is a decision for the credit team
  - capabilities: "sap/*/Release"
    action: require_approval
    reason: releasing an invoice lets it be paid
  - if_effects: [destructive]
    action: require_approval
    reason: may destroy data
```

```bash
flowglyph serve catalog --policy policy.yaml                       # dry run: shows what would be sent
flowglyph serve catalog --policy policy.yaml --connections flowglyph.connections.yaml   # for real
claude mcp add flowglyph -- flowglyph serve /path/to/catalog --policy /path/to/policy.yaml
```

## What you see

Three calls from an agent on the SAP example, the second one a retry of the first:

```text
create: done, then replayed (enforced by the ledger)
block: denied, blocking a business partner is a decision for the credit team
release: approval_required, releasing an invoice lets it be paid
  a person must run `flowglyph approve catalog 'sap/ZSUPPLIER_INVOICE_SRV/Release#auto:69abe32e...'`
```

On every call the gateway validates the arguments against the capability's JSON Schema,
applies the policy, runs anything with side effects at most once per idempotency key and gives
a retry the stored result, executes (as a dry run, or through the systems named in a
connections file that holds the names of environment variables, never secrets), and writes an
audit line without the argument values. `flowglyph approvals` lists what is waiting, with the
arguments, and `flowglyph approve` records who let it through.

The agent sees the catalog at three sizes, so it never loads more than it uses:

| MCP tool | What the agent gets |
|---|---|
| `catalog_search` | short cards, about 40 tokens each, to scan thousands of functions |
| `catalog_card` | one function's inputs, outputs, steps and retry advice |
| `catalog_contract` | the full contract |
| `run_capability`, or one tool per function | a run through the gateway, with an optional idempotency key |
| `run_status` | the outcome of an earlier run |

## What changes

Effects and idempotency modes describe intent; the gateway is the one place that enforces it,
and the one place that has to be trusted. The same policy covers UiPath robots, SAP services
and APIs, and the audit log answers "who ran what, when, under which rule" without ever holding
a payload.

## Telling it

- **Hook:** the agent asked to pay an invoice twice; the second answer was `replayed`, and
  nothing ran.
- **Three points:** one MCP server for every platform; policy by id pattern or by effect, with
  a person in the loop when you say so; idempotency enforced by a ledger, not promised by a
  prompt.
- **Demo:** `serve` in dry-run mode on the SAP example, Claude Code connected, ask it to
  create a business partner and then block one; show `done`, `denied` and the audit line.
- **Where:** MCP and agent-security audiences (Hacker News, X, the MCP community), SAP
  Community for the OData and CPI angle, LinkedIn for platform leads.
