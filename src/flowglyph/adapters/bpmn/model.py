"""The parts of a BPMN 2.0 document FlowGlyph reads, with Camunda 7 and Camunda 8 extensions."""

from dataclasses import dataclass, field
from typing import Literal
from xml.etree import ElementTree as ET

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA = "http://camunda.org/schema/1.0/bpmn"
ZEEBE = "http://camunda.org/schema/zeebe/1.0"

type Engine = Literal["Camunda 7", "Camunda 8", "BPMN"]

TASKS = frozenset(
    {
        "task",
        "serviceTask",
        "sendTask",
        "receiveTask",
        "userTask",
        "manualTask",
        "scriptTask",
        "businessRuleTask",
        "callActivity",
        "subProcess",
        "transaction",
    }
)
GATEWAYS = frozenset(
    {
        "exclusiveGateway",
        "inclusiveGateway",
        "parallelGateway",
        "eventBasedGateway",
        "complexGateway",
    }
)
EVENTS = frozenset(
    {
        "startEvent",
        "endEvent",
        "intermediateThrowEvent",
        "intermediateCatchEvent",
        "boundaryEvent",
    }
)


@dataclass(frozen=True)
class FormField:
    """One field of a Camunda 7 start form: a variable the process expects."""

    name: str
    type: str
    label: str | None
    default: str | None


@dataclass(frozen=True)
class Step:
    """A task, gateway or event of a process."""

    id: str
    kind: str
    name: str
    event: str | None = None
    detail: str | None = None
    implementation: str | None = None
    called: str | None = None
    attached_to: str | None = None
    default_flow: str | None = None
    children: tuple["Step", ...] = ()


@dataclass(frozen=True)
class Flow:
    """A sequence flow and the condition on it, if any."""

    id: str
    source: str
    target: str
    name: str
    condition: str | None


@dataclass
class Process:
    """One process of a BPMN document."""

    id: str
    name: str
    executable: bool
    documentation: str
    steps: list[Step] = field(default_factory=list[Step])
    flows: list[Flow] = field(default_factory=list[Flow])
    form: list[FormField] = field(default_factory=list[FormField])
    messages: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def start(self) -> Step | None:
        """The start event an outside caller triggers: a message or none start before a timer."""
        starts = [step for step in self.steps if step.kind == "startEvent"]
        ranked = sorted(starts, key=lambda step: {None: 0, "message": 1}.get(step.event, 2))
        return ranked[0] if ranked else None

    def all_steps(self) -> list[Step]:
        """Every step, including those inside embedded subprocesses."""
        found: list[Step] = []
        pending = list(self.steps)
        while pending:
            step = pending.pop(0)
            found.append(step)
            pending.extend(step.children)
        return found


@dataclass
class Document:
    """A BPMN definitions document."""

    engine: Engine
    processes: list[Process] = field(default_factory=list[Process])


def is_bpmn(root: ET.Element) -> bool:
    """Whether `root` is a BPMN 2.0 `definitions` element."""
    return root.tag == f"{{{BPMN}}}definitions"


def parse_document(root: ET.Element) -> Document:
    """Read every process of a BPMN document."""
    namespaces = {element.tag.split("}")[0][1:] for element in root.iter() if "}" in element.tag}
    attributes = {
        name.split("}")[0][1:] for element in root.iter() for name in element.attrib if "}" in name
    }
    used = namespaces | attributes
    engine: Engine = "Camunda 8" if ZEEBE in used else "Camunda 7" if CAMUNDA in used else "BPMN"
    messages = {
        message.get("id", ""): message.get("name", "")
        for message in root.iter(f"{{{BPMN}}}message")
    }
    document = Document(engine=engine)
    for element in root.iter(f"{{{BPMN}}}process"):
        documentation = element.findtext(f"{{{BPMN}}}documentation") or ""
        process = Process(
            id=element.get("id", ""),
            name=element.get("name", "") or element.get("id", ""),
            executable=element.get("isExecutable", "true") != "false",
            documentation=documentation.strip(),
            messages=messages,
        )
        process.steps, process.flows = _children(element)
        start = process.start
        if start is not None:
            process.form = _form(_find(element, start.id))
        document.processes.append(process)
    return document


def _children(container: ET.Element) -> tuple[list[Step], list[Flow]]:
    steps: list[Step] = []
    flows: list[Flow] = []
    for child in container:
        local = _local(child.tag)
        if local == "sequenceFlow":
            condition = child.findtext(f"{{{BPMN}}}conditionExpression")
            flows.append(
                Flow(
                    id=child.get("id", ""),
                    source=child.get("sourceRef", ""),
                    target=child.get("targetRef", ""),
                    name=child.get("name", ""),
                    condition=condition.strip() if condition else None,
                )
            )
        elif local in TASKS or local in GATEWAYS or local in EVENTS:
            inner: tuple[Step, ...] = ()
            if local in {"subProcess", "transaction"}:
                nested, nested_flows = _children(child)
                inner = tuple(nested)
                flows.extend(nested_flows)
            steps.append(
                Step(
                    id=child.get("id", ""),
                    kind=local,
                    name=child.get("name", "") or child.get("id", ""),
                    event=_event_kind(child),
                    detail=_event_detail(child),
                    implementation=_implementation(child),
                    called=_called(child),
                    attached_to=child.get("attachedToRef"),
                    default_flow=child.get("default"),
                    children=inner,
                )
            )
    return steps, flows


def _implementation(element: ET.Element) -> str | None:
    """How the engine runs a task: a Camunda 7 topic, class or expression, or a Camunda 8 job."""
    if element.get(f"{{{CAMUNDA}}}type") == "external":
        return f"external task {element.get(f'{{{CAMUNDA}}}topic', '')}".strip()
    for attribute, label in (
        ("class", "class"),
        ("delegateExpression", "delegate"),
        ("expression", "expression"),
    ):
        value = element.get(f"{{{CAMUNDA}}}{attribute}")
        if value:
            return f"{label} {value}"
    definition = element.find(f".//{{{ZEEBE}}}taskDefinition")
    if definition is not None:
        return f"job {definition.get('type', '')}".strip()
    connector = element.find(f".//{{{CAMUNDA}}}connectorId")
    if connector is not None and connector.text:
        return f"connector {connector.text.strip()}"
    decision = element.get(f"{{{CAMUNDA}}}decisionRef")
    zeebe_decision = element.find(f".//{{{ZEEBE}}}calledDecision")
    if decision or zeebe_decision is not None:
        name = decision or (
            zeebe_decision.get("decisionId", "") if zeebe_decision is not None else ""
        )
        return f"decision {name}".strip()
    script = element.get("scriptFormat")
    return f"script {script}" if script else None


def _called(element: ET.Element) -> str | None:
    if _local(element.tag) != "callActivity":
        return None
    zeebe = element.find(f".//{{{ZEEBE}}}calledElement")
    if zeebe is not None:
        return zeebe.get("processId")
    return element.get("calledElement")


def _form(start: ET.Element | None) -> list[FormField]:
    if start is None:
        return []
    return [
        FormField(
            name=field_element.get("id", ""),
            type=field_element.get("type", "string"),
            label=field_element.get("label"),
            default=field_element.get("defaultValue"),
        )
        for field_element in start.iter(f"{{{CAMUNDA}}}formField")
        if field_element.get("id")
    ]


def _find(container: ET.Element, step_id: str) -> ET.Element | None:
    return next((child for child in container if child.get("id") == step_id), None)


def _event_kind(element: ET.Element) -> str | None:
    for child in element:
        local = _local(child.tag)
        if local.endswith("EventDefinition"):
            return local.removesuffix("EventDefinition")
    return None


def _event_detail(element: ET.Element) -> str | None:
    """The message an event waits for, or the schedule of a timer."""
    for child in element:
        local = _local(child.tag)
        if local == "messageEventDefinition":
            return child.get("messageRef")
        if local == "timerEventDefinition":
            for timer in child:
                if timer.text and timer.text.strip():
                    return timer.text.strip()
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
