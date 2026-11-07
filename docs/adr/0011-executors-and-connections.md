# ADR-0011: Executors run through declared connections

- Status: accepted
- Date: 2026-11-07

## Context

The gateway validated, policed, deduplicated and audited every run, then handed it to a dry-run
executor that only reported what would have been sent. Running for real needs three things the
catalog does not hold: where each system is, how to authenticate, and which capabilities each
system owns. Adapters cannot know them: the same OData metadata describes the development and
the production system.

## Decision

- **A connections file**, `flowglyph.connections.yaml`, declares each system once: its type
  (`http`, `odata`, `uipath`), its address, its authentication, and the capability id patterns
  it runs. `flowglyph serve --connections` builds a `ConnectedExecutor` from it; without the
  flag every run stays a dry run.
- **Secrets never enter the file.** Authentication names environment variables
  (`token_env`, `password_env`, `client_secret_env`); the file can be committed next to the
  catalog and reviewed. A field that would hold a value, such as `token`, is rejected. Before
  serving, the command checks every named variable is set.
- **One executor per system kind**, each written for how that system really behaves:
  - `HttpExecutor` reads the `x-in` the OpenAPI adapter records on each input and places it in
    the path, query, a header, a cookie or the body.
  - `ODataExecutor` fetches the CSRF token SAP requires before a change, retries once when the
    server says it expired, writes keys and parameters as OData URL literals of their EDM type,
    tunnels V2 updates as `MERGE`, sends `If-Match: *`, and quotes SAP's own error message.
  - `OrchestratorExecutor` runs a project's entry point as a published process: it finds the
    folder and the release, starts a job with the inputs as job arguments, polls until the job
    ends and returns its output arguments. Other workflows of a project are refused: they only
    run inside the process.
- **Capabilities no connection claims are refused**, not dry-run, so an agent is never told
  something ran when it did not.
- **The HTTP client refuses redirects** and non-`http(s)` URLs, caps responses at 16 MiB and
  keeps cookies per system, so a credential is only ever sent to the address in the file.
- The SAP adapter writes operation addresses as calls, `GET checkDuplicates()`,
  `POST BusinessPartner(key)/zbusinesspartner.block()`, and marks key inputs with
  `x-odata-key`, so an executor can tell an operation from an entity set without guessing.

## Alternatives considered

- **Addresses in the catalog.** Extraction would then depend on an environment, and the same
  catalog could not serve development and production.
- **One generic HTTP executor for everything.** SAP's CSRF dance, OData literals and
  Orchestrator's job lifecycle are not generic; hiding them behind "HTTP" would make every real
  run fail in a different way.
- **Credentials in the file, encrypted.** Still a file of secrets to manage; environment
  variables are what every CI system and container runtime already provides.

## Consequences

- Executors are tested against fake servers that play each system, including token rotation,
  faulted jobs and timeouts; none has yet been run against a real SAP or Orchestrator tenant.
- Orchestrator runs are synchronous: the gateway waits for the job, up to a configurable
  timeout, so an agent gets outputs in the same call.
- iFlows (SAP Cloud Integration) are not run yet: calling one means calling its endpoint, which
  an `http` connection can do once the iFlow's address is known.
