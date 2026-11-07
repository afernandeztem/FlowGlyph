"""The gateway: validates arguments, applies policy, deduplicates runs and executes them."""

import json
import shlex
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaError

from flowglyph._internal import markdown
from flowglyph._internal.hashing import fingerprint
from flowglyph.catalog import Catalog, load_catalog
from flowglyph.errors import CatalogError, FlowGlyphError
from flowglyph.gateway.audit import AuditLog
from flowglyph.gateway.executors import DryRunExecutor, Executor
from flowglyph.gateway.ledger import Ledger, Run, Ticket
from flowglyph.gateway.policy import DEFAULT_POLICY, Decision, Policy
from flowglyph.ir import Capability
from flowglyph.views import l0_card

DEFAULT_TTL_SECONDS = 24 * 60 * 60

type Status = Literal[
    "done",
    "replayed",
    "in_progress",
    "failed",
    "denied",
    "approval_required",
    "invalid",
    "conflict",
]


@dataclass(frozen=True)
class RunResult:
    """What the gateway did with one request to run a capability."""

    status: Status
    capability: str
    version: str
    idempotency_key: str | None = None
    enforcement: Literal["ledger", "none"] = "none"
    result: Any = None
    errors: list[str] = field(default_factory=list[str])
    reason: str | None = None

    @property
    def ok(self) -> bool:
        """Whether the capability ran, now or in an earlier call with the same key."""
        return self.status in {"done", "replayed"}

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable view, without empty fields."""
        return {key: value for key, value in asdict(self).items() if value not in (None, [])}


class Gateway:
    """Runs catalog capabilities on behalf of an agent, enforcing what the IR promises.

    Every request is validated against the capability's input schema, checked against the
    policy, deduplicated through the ledger when it has side effects or needs approval,
    executed, and recorded in the audit log. The catalog is reloaded when the files on disk
    change, so a re-run of `flowglyph extract` is picked up without a restart.
    """

    def __init__(
        self,
        catalog_dir: str | Path,
        *,
        policy: Policy = DEFAULT_POLICY,
        executor: Executor | None = None,
        state_dir: str | Path | None = None,
    ) -> None:
        """Serve the catalog saved in `catalog_dir`, keeping state in `state_dir`."""
        self.catalog_dir = Path(catalog_dir)
        self.state_dir = Path(state_dir) if state_dir else None
        state = self.state_dir or self.catalog_dir / ".flowglyph"
        self.policy = policy
        self.executor = executor or DryRunExecutor()
        self.ledger = Ledger(state / "ledger.sqlite")
        self.audit = AuditLog(state / "audit.jsonl")
        self._catalog: Catalog | None = None
        self._catalog_mtime: float | None = None

    @property
    def catalog(self) -> Catalog:
        """The current catalog, reloaded if it changed on disk."""
        mtime = (self.catalog_dir / "catalog.jsonl").stat().st_mtime_ns
        if self._catalog is None or mtime != self._catalog_mtime:
            self._catalog = load_catalog(self.catalog_dir)
            self._catalog_mtime = mtime
        return self._catalog

    def search(
        self, query: str, limit: int = 20, *, invocable_only: bool = True
    ) -> list[dict[str, Any]]:
        """L0 cards of the capabilities that best match `query`."""
        found = self.catalog.search(query, limit=limit, invocable=True if invocable_only else None)
        return [l0_card(capability) for capability in found]

    def describe(self, reference: str) -> str:
        """The L1 card of a capability, as Markdown."""
        catalog = self.catalog
        capability = catalog.get(reference)
        return markdown.render_capability(capability, catalog.workflows, catalog.capabilities)

    def contract(self, reference: str) -> dict[str, Any]:
        """The L2 view of a capability: its full IR document."""
        return self.catalog.get(reference).model_dump(mode="json")

    def status(self, idempotency_key: str) -> Run | None:
        """The ledger entry for `idempotency_key`, if there is one."""
        return self.ledger.get(idempotency_key)

    def run(
        self,
        reference: str,
        arguments: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> RunResult:
        """Run a capability, or explain why it was not run.

        Whatever the executor raises becomes a `failed` result; an exception never escapes
        with the ledger row still running. Every call leaves a line in the audit log.
        """
        try:
            capability = self.catalog.get(reference)
        except CatalogError as error:
            return RunResult("invalid", reference, "", errors=[str(error)])
        rejection, decision = self._admit(capability, arguments)
        if rejection is not None:
            self._record("run", capability, arguments, **_outcome(rejection))
            return rejection
        result = _result(capability, "failed", errors=["the run was interrupted"])
        try:
            if capability.effects.has_side_effects or decision.action == "require_approval":
                ticket = Ticket(
                    key=idempotency_key_for(capability, arguments, idempotency_key),
                    capability=capability.id,
                    version=capability.version,
                    arguments_hash=fingerprint(arguments),
                    ttl_seconds=capability.idempotency.ttl_seconds or DEFAULT_TTL_SECONDS,
                    arguments=arguments,
                )
                result = self._run_once(capability, arguments, ticket, decision)
            else:
                result = self._execute(capability, arguments)
        finally:
            self._record("run", capability, arguments, **_outcome(result))
        return result

    def approve(self, key: str, *, actor: str) -> Run | None:
        """Let the run waiting under `key` go ahead, in `actor`'s name.

        Returns the approved run, or None when nothing was waiting under `key`.
        """
        run = self.ledger.approve(key)
        if run is not None:
            self.audit.record(
                "approve",
                actor=actor,
                capability=run.capability,
                version=run.version,
                idempotency_key=run.key,
                arguments_hash=run.arguments_hash,
            )
        return run

    def _admit(
        self, capability: Capability, arguments: dict[str, Any]
    ) -> tuple[RunResult | None, Decision]:
        decision = self.policy.decide(capability)
        if not capability.invocable:
            errors = [f"{capability.id} is documentation only and cannot be run on its own"]
            return _result(capability, "invalid", errors=errors), decision
        if decision.action == "deny":
            # Before validation, so an agent never fixes arguments for a call it may not make.
            return _result(capability, "denied", reason=decision.reason), decision
        errors = validate_arguments(capability, arguments)
        if errors:
            return _result(capability, "invalid", errors=errors), decision
        return None, decision

    def _run_once(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        ticket: Ticket,
        decision: Decision,
    ) -> RunResult:
        ledger = {"idempotency_key": ticket.key, "enforcement": "ledger"}
        if decision.action == "require_approval":
            claim = self.ledger.claim(ticket, status="awaiting_approval")
            if claim.claimed:
                reason = f"{decision.reason}; a person must run {self.approval_command(ticket.key)}"
                return _result(capability, "approval_required", reason=reason, **ledger)
            if claim.existing is None or claim.existing.status != "approved":
                return self._existing(capability, claim.existing, ticket)
        claim = self.ledger.claim(ticket, status="running")
        if not claim.claimed:
            return self._existing(capability, claim.existing, ticket)
        result = self._execute(capability, arguments, idempotency_key=ticket.key)
        if result.status == "failed":
            self.ledger.finish(ticket.key, "failed", {"error": result.errors[0]})
        else:
            self.ledger.finish(ticket.key, "done", result.result)
        return replace(result, **ledger)

    def _execute(
        self, capability: Capability, arguments: dict[str, Any], idempotency_key: str | None = None
    ) -> RunResult:
        self._record("start", capability, arguments, idempotency_key=idempotency_key)
        try:
            output = self.executor.execute(capability, arguments)
        except Exception as error:  # noqa: BLE001
            # Executors are plug-ins that talk to remote systems; whatever they raise is a
            # failed run, never a crash of the gateway with the ledger row left running.
            return _result(capability, "failed", errors=[_describe(error)])
        return _result(capability, "done", result=output)

    def _record(
        self, event: str, capability: Capability, arguments: dict[str, Any], **fields: Any
    ) -> None:
        self.audit.record(
            event,
            capability=capability.id,
            version=capability.version,
            argument_names=sorted(arguments),
            arguments_hash=fingerprint(arguments),
            **fields,
        )

    def approval_command(self, key: str) -> str:
        """The command a person runs to approve the run waiting under `key`."""
        arguments = ["flowglyph", "approve", str(self.catalog_dir), key]
        if self.state_dir is not None:
            arguments += ["--state", str(self.state_dir)]
        return f"`{shlex.join(arguments)}`"

    def _existing(self, capability: Capability, run: Run | None, ticket: Ticket) -> RunResult:
        ledger = {"idempotency_key": ticket.key, "enforcement": "ledger"}
        if run is None:
            return _result(capability, "in_progress", **ledger)
        if run.arguments_hash != ticket.arguments_hash:
            errors = ["this idempotency key was already used with different arguments"]
            return _result(capability, "conflict", errors=errors, **ledger)
        if run.status == "done":
            return _result(capability, "replayed", result=run.result, **ledger)
        if run.status == "awaiting_approval":
            reason = f"waiting for approval; a person must run {self.approval_command(ticket.key)}"
            return _result(capability, "approval_required", reason=reason, **ledger)
        return _result(capability, "in_progress", **ledger)


def _result(capability: Capability, status: Status, **fields: Any) -> RunResult:
    return RunResult(status=status, capability=capability.id, version=capability.version, **fields)


def _outcome(result: RunResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "idempotency_key": result.idempotency_key,
        "enforcement": result.enforcement,
        "reason": result.reason,
    }


def _describe(error: Exception) -> str:
    if isinstance(error, FlowGlyphError):
        return str(error)
    return f"{type(error).__name__}: {error}"


def idempotency_key_for(
    capability: Capability, arguments: dict[str, Any], explicit: str | None
) -> str:
    """The ledger key for a call: explicit, from the capability's key fields, or a hash.

    Keys are namespaced by capability so the same business id can be used with different
    capabilities without colliding.
    """
    if explicit:
        return f"{capability.id}#{explicit}"
    key_fields = capability.idempotency.key_fields
    has_key = all(name in arguments for name in key_fields)
    if capability.idempotency.mode == "key" and key_fields and has_key:
        values = "|".join(json.dumps(arguments[name], sort_keys=True) for name in key_fields)
        return f"{capability.id}#{values}"
    return f"{capability.id}#auto:{fingerprint(arguments).removeprefix('sha256:')}"


def validate_arguments(capability: Capability, arguments: dict[str, Any]) -> list[str]:
    """Problems with `arguments` against the capability's input schema, as readable messages."""
    validator = Draft202012Validator(capability.input_schema)
    errors = cast("Iterable[SchemaError]", validator.iter_errors(arguments))  # pyright: ignore[reportUnknownMemberType]
    problems: list[str] = []
    for error in sorted(errors, key=lambda e: [str(part) for part in e.path]):
        where = "/".join(str(part) for part in error.path)
        problems.append(f"{where}: {error.message}" if where else error.message)
    return problems
