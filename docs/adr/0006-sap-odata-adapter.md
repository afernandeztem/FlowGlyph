# ADR-0006: SAP OData services are read from their metadata

- Status: accepted
- Date: 2026-11-06 (recorded after the adapter shipped)

## Context

Most business operations in SAP S/4HANA, SAP Gateway and SAP BTP are exposed as OData services.
Every service publishes `$metadata`: an EDMX document listing its entity sets, what each allows,
their typed properties, and its function imports, functions and actions. OData V2 and V4 are both
in wide use, often side by side on the same system.

## Decision

- The `sap` adapter reads EDMX documents from files. It never calls a service: a `$metadata`
  saved from a system, or published by SAP, is enough.
- Every entity set becomes `query` and `read`; it also gets `create`, `update` and `delete` when
  the metadata allows them, through `sap:creatable`, `sap:updatable` and `sap:deletable` in V2 or
  the Capabilities vocabulary in V4.
- Effects and idempotency follow HTTP and OData semantics:

  | Operation | Request | Effects | Idempotency |
  |---|---|---|---|
  | query, read | `GET` | `R X` | natural |
  | create | `POST` | `W X` | none, with a note asking for a business key override |
  | update | `PATCH` | `W d X` (destructive unknown: fields are overwritten) | natural, low confidence |
  | delete | `DELETE` | `W D X` | natural: deleting twice leaves the same state |
  | V2 function import with `GET`, V4 function | `GET` | `R X` | natural |
  | V2 function import with `POST`, V4 action | `POST` | all unknown, `X` | none |

- Ids are `sap/<service>/<entity set>/<operation>`. When two documents describe services with the
  same name (the V2 and V4 versions of one API, say), names are qualified with the OData version,
  or else with the shortest distinguishing part of their path.
- Some SAP services use the `sap:` prefix without declaring it. The adapter declares the known
  SAP namespaces and reports an `info` diagnostic, instead of failing on a document SAP itself
  serves.

## Alternatives considered

- **Fetching `$metadata` from a live system.** It would always be current, but adapters must be
  offline and deterministic, and credentials have no place in extraction. Saving the document
  is one `curl`.
- **The OpenAPI specs on the SAP Business Accelerator Hub.** They exist for many APIs and the
  `openapi` adapter already reads them, but they are generated from the same metadata with less
  detail (no `sap:` annotations) and are missing for custom services, which only have EDMX.

## Consequences

- Authorization is not in the metadata, so `security` stays empty: declare scopes in overrides.
- Business meaning the protocol cannot express, such as a posting that cannot be reversed, also
  needs an override. The report marks every `create` and every action for review.
- The adapter does not model `$batch`, deep inserts or navigation properties as capabilities.
