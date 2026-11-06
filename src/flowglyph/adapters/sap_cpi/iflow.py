from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
IFL = "http:///com.sap.ifl.model/Ifl.xsd"
_STEP_TAGS = frozenset(
    {"callActivity", "serviceTask", "exclusiveGateway", "parallelGateway", "startEvent", "endEvent"}
)


@dataclass(frozen=True)
class Channel:
    """An adapter: how the iFlow is called (sender) or what it calls (receiver)."""

    id: str
    name: str
    component: str
    direction: str
    source: str
    target: str
    properties: dict[str, str]

    @property
    def address(self) -> str:
        """The endpoint path or address the channel uses, as written in the iFlow."""
        for key in ("urlPath", "address", "httpAddressWithoutQuery", "Address", "host"):
            if self.properties.get(key):
                return self.properties[key]
        return ""


@dataclass(frozen=True)
class Step:
    """One BPMN element of a process: an activity, gateway or event."""

    id: str
    kind: str
    name: str
    activity_type: str
    properties: dict[str, str]
    default_flow: str | None = None
    event: str | None = None


@dataclass(frozen=True)
class Flow:
    """A sequence flow, with the condition a router evaluates on it."""

    id: str
    source: str
    target: str
    name: str
    condition: str | None


@dataclass
class Process:
    """A main or local integration process."""

    id: str
    name: str
    steps: list[Step] = field(default_factory=list[Step])
    flows: list[Flow] = field(default_factory=list[Flow])
    handler_steps: list[Step] = field(default_factory=list[Step])
    has_exception_handler: bool = False

    @property
    def all_steps(self) -> list[Step]:
        """Steps of the main path and of exception handlers, which also call and change things."""
        return self.steps + self.handler_steps

    def step(self, step_id: str) -> Step | None:
        """The step with id `step_id`, if it belongs to this process."""
        return next((s for s in self.steps if s.id == step_id), None)


@dataclass
class IFlow:
    """The parts of an `.iflw` document FlowGlyph uses."""

    senders: list[Channel] = field(default_factory=list[Channel])
    receivers: list[Channel] = field(default_factory=list[Channel])
    processes: dict[str, Process] = field(default_factory=dict[str, Process])
    participants: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def main(self) -> Process | None:
        """The process that starts on a message or a timer; the others are local processes."""
        targets = {sender.target for sender in self.senders}
        for process in self.processes.values():
            if any(step.id in targets or step.event == "timer" for step in process.steps):
                return process
        return next(iter(self.processes.values()), None)

    def receivers_of(self, step_id: str) -> list[Channel]:
        """The receiver channels attached to an external call step."""
        return [channel for channel in self.receivers if channel.source == step_id]

    def references(self) -> set[str]:
        """Every `{{parameter}}` the iFlow refers to."""
        names: set[str] = set()
        for channel in self.senders + self.receivers:
            names.update(_parameter_references(channel.properties))
        for process in self.processes.values():
            for step in process.all_steps:
                names.update(_parameter_references(step.properties))
        return names


def parse_iflow(root: ET.Element) -> IFlow:
    """Read an `.iflw` document."""
    iflow = IFlow()
    for participant in root.iter(f"{{{BPMN}}}participant"):
        iflow.participants[participant.get("id", "")] = participant.get(f"{{{IFL}}}type", "")
    for message_flow in root.iter(f"{{{BPMN}}}messageFlow"):
        channel = _channel(message_flow)
        if channel.direction.lower() == "sender":
            iflow.senders.append(channel)
        else:
            iflow.receivers.append(channel)
    for element in root.iter(f"{{{BPMN}}}process"):
        process = Process(id=element.get("id", ""), name=element.get("name", ""))
        for child in element:
            _add(process, child)
        iflow.processes[process.id] = process
    return iflow


def properties(element: ET.Element) -> dict[str, str]:
    """The `ifl:property` key-value pairs of an element's own extension elements."""
    found: dict[str, str] = {}
    extension = element.find(f"{{{BPMN}}}extensionElements")
    if extension is None:
        return found
    for prop in extension.iter(f"{{{IFL}}}property"):
        key = prop.findtext("key")
        if key:
            found[key] = (prop.findtext("value") or "").strip()
    return found


def _channel(element: ET.Element) -> Channel:
    props = properties(element)
    return Channel(
        id=element.get("id", ""),
        name=element.get("name", "") or props.get("Name", ""),
        component=props.get("ComponentType", "") or element.get("name", ""),
        direction=props.get("direction") or props.get("Direction") or "",
        source=element.get("sourceRef", ""),
        target=element.get("targetRef", ""),
        properties=props,
    )


def _add(process: Process, element: ET.Element) -> None:
    local = element.tag.rsplit("}", 1)[-1]
    if local == "sequenceFlow":
        condition = element.findtext(f"{{{BPMN}}}conditionExpression")
        process.flows.append(
            Flow(
                id=element.get("id", ""),
                source=element.get("sourceRef", ""),
                target=element.get("targetRef", ""),
                name=element.get("name", ""),
                condition=condition.strip() if condition else None,
            )
        )
    elif local == "subProcess":
        if _is_exception_handler(element):
            process.has_exception_handler = True
        handler = Process(id=element.get("id", ""), name=element.get("name", ""))
        for child in element:
            _add(handler, child)
        process.handler_steps.extend(handler.all_steps)
    elif local in _STEP_TAGS:
        props = properties(element)
        process.steps.append(
            Step(
                id=element.get("id", ""),
                kind=local,
                name=element.get("name", "") or local,
                activity_type=props.get("activityType", local),
                properties=props,
                default_flow=element.get("default"),
                event=_event_kind(element),
            )
        )


def _is_exception_handler(element: ET.Element) -> bool:
    """SAP marks exception subprocesses with an activity type; plain BPMN uses triggeredByEvent."""
    if element.get("triggeredByEvent") == "true":
        return True
    if "ErrorEventSubProcess" in properties(element).get("activityType", ""):
        return True
    return any(
        child.tag.endswith("startEvent") and _event_kind(child) == "error" for child in element
    )


def _event_kind(element: ET.Element) -> str | None:
    for child in element:
        local = child.tag.rsplit("}", 1)[-1]
        if local.endswith("EventDefinition"):
            return local.removesuffix("EventDefinition")
    return None


def _parameter_references(values: dict[str, str]) -> set[str]:
    found: set[str] = set()
    for value in values.values():
        start = value.find("{{")
        while start != -1:
            end = value.find("}}", start)
            if end == -1:
                break
            found.add(value[start + 2 : end].strip())
            start = value.find("{{", end)
    return found
