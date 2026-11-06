"""What SAP Cloud Integration adapters and steps do, and what makes an iFlow fragile."""

import re
from typing import Literal

from flowglyph.adapters.sap_cpi.iflow import Channel, IFlow, Step
from flowglyph.ir import Effects, Idempotency, Tri

type Finding = tuple[Literal["info", "warning"], str]

_READ = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
_WRITE = Effects(reads=Tri.UNKNOWN, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
_OVERWRITE = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.YES, destructive=Tri.UNKNOWN, external=Tri.YES
)
_DELETE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.YES, external=Tri.YES)
_UNKNOWN = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.YES
)
_TENANT_WRITE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.NO)
_TENANT_READ = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.NO)
_TENANT_DELETE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.YES, external=Tri.NO)
_SCRIPT = Effects(reads=Tri.NO, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.UNKNOWN)

_HTTP_METHODS = {
    "GET": _READ,
    "HEAD": _READ,
    "POST": _WRITE,
    "PUT": _OVERWRITE,
    "PATCH": _OVERWRITE,
    "DELETE": _DELETE,
}
_SENDING_ADAPTERS = frozenset(
    {"MAIL", "SFTP", "FTP", "SOAP", "IDOC", "XI", "AS2", "AS4", "JMS", "AMQP", "KAFKA", "ELSTER"}
)
_EXACTLY_ONCE = re.compile(r"exactly\s*once", re.IGNORECASE)
_IDEMPOTENT = re.compile(r"idempot", re.IGNORECASE)
_MESSAGE_ID_KEY = re.compile(r"(message|unique)\s*id|idempot\w*id", re.IGNORECASE)
_BODY_COPY = re.compile(r"\$\{(in\.)?body\}")


def channel_effects(channel: Channel) -> Effects | None:
    """Effects of calling a receiver channel; None for ProcessDirect, resolved through the call."""
    component = channel.component.upper()
    if component == "PROCESSDIRECT":
        return None
    if component in {"HTTP", "HTTPS"}:
        return _HTTP_METHODS.get(channel.properties.get("httpMethod", "").upper(), _UNKNOWN)
    if "ODATA" in component:
        return _odata_operation(channel.properties.get("operation", ""))
    if component in _SENDING_ADAPTERS:
        return _WRITE
    return _UNKNOWN


def step_effects(step: Step) -> Effects | None:
    """Effects of a process step on its own; None for steps that only shape the message."""
    activity = step.activity_type
    if activity == "DBstorage":
        operation = step.properties.get("operation", "").lower()
        if operation in {"put", "write"}:
            return _TENANT_WRITE
        if operation in {"delete"}:
            return _TENANT_DELETE
        return _TENANT_READ
    if activity == "Script":
        return _SCRIPT
    if activity in {"Variables", "WriteVariables", "Persist"}:
        return _TENANT_WRITE
    return None


def declared_idempotency(iflow: IFlow) -> tuple[Idempotency, str] | None:
    """Idempotency the iFlow itself guarantees, with a note saying where it comes from."""
    for process in iflow.processes.values():
        for step in process.all_steps:
            if _mentions_idempotency(step):
                key = _message_id(step.properties)
                note = "declared by the iFlow: an idempotent process call deduplicates on " + (
                    key or "the message id"
                )
                return _declared(key), note
    for sender in iflow.senders:
        if any(_EXACTLY_ONCE.search(value) for value in sender.properties.values()):
            note = f"declared by the iFlow: its {sender.component} sender delivers exactly once"
            return _declared(None), note
    for process in iflow.processes.values():
        for step in process.all_steps:
            entry = step.properties.get("messageId", "")
            guarded = step.properties.get("override", "").lower() == "false"
            if step.activity_type == "DBstorage" and guarded and "${" in entry:
                note = (
                    f"a Data Store write without overwrite rejects repeated {entry}; "
                    "retries are safe only if it runs before any external call"
                )
                fields = (entry,)
                return Idempotency(mode="conditional", key_fields=fields, confidence=0.6), note
    return None


def design_findings(iflow: IFlow) -> list[Finding]:
    """Design problems that make an iFlow fragile or insecure, as (level, message) pairs."""
    findings: list[Finding] = []
    main = iflow.main
    if main is not None and not main.has_exception_handler:
        findings.append(
            ("warning", "the main process has no exception subprocess: a failure ends unhandled")
        )
    for channel in iflow.receivers:
        findings.extend(_receiver_findings(channel))
    for sender in iflow.senders:
        if sender.component.upper() == "HTTPS" and sender.properties.get("xsrfProtection") == "0":
            findings.append(("info", f"CSRF protection is off on endpoint {sender.address}"))
    for process in iflow.processes.values():
        for step in process.all_steps:
            findings.extend(_step_findings(step))
    return findings


def _receiver_findings(channel: Channel) -> list[Finding]:
    findings: list[Finding] = []
    address = channel.address
    component = channel.component.upper()
    if address.lower().startswith("http://"):
        findings.append(("warning", f"{channel.component} receiver uses plain HTTP: {address}"))
    if address and "{{" not in address and "${" not in address and component != "PROCESSDIRECT":
        findings.append(
            ("info", f"{channel.component} receiver address is hard-coded; externalize {address}")
        )
    timeout = channel.properties.get("httpRequestTimeout")
    if component in {"HTTP", "HTTPS"} and (timeout is None or timeout.strip() in {"", "0"}):
        findings.append(
            ("warning", f"{channel.component} receiver {address} has no request timeout")
        )
    return findings


def _step_findings(step: Step) -> list[Finding]:
    findings: list[Finding] = []
    if step.kind == "exclusiveGateway" and not step.default_flow:
        findings.append(("warning", f"router {step.name!r} has no default route"))
    if step.activity_type == "Splitter" and step.properties.get("streaming", "").lower() != "true":
        findings.append(("info", f"splitter {step.name!r} does not stream"))
    if step.activity_type == "Enricher":
        table = step.properties.get("propertyTable", "")
        if _BODY_COPY.search(table):
            findings.append(
                ("warning", f"{step.name!r} copies the whole body into a property, doubling memory")
            )
    return findings


def _odata_operation(operation: str) -> Effects:
    lowered = operation.lower()
    if any(word in lowered for word in ("query", "read", "get")):
        return _READ
    if any(word in lowered for word in ("create", "post", "insert")):
        return _WRITE
    if any(word in lowered for word in ("update", "merge", "patch", "put")):
        return _OVERWRITE
    if "delete" in lowered:
        return _DELETE
    return _UNKNOWN


def _mentions_idempotency(step: Step) -> bool:
    return any(_IDEMPOTENT.search(text) for text in (step.activity_type, *step.properties.values()))


def _message_id(properties: dict[str, str]) -> str | None:
    for key, value in properties.items():
        if _MESSAGE_ID_KEY.search(key) and value:
            return value
    return None


def _declared(key: str | None) -> Idempotency:
    return Idempotency(
        mode="key",
        key_fields=(key,) if key else (),
        provenance="declared",
        confidence=0.95,
        inferred_by=None,
    )
