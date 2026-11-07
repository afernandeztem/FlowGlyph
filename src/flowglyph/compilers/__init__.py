"""Compile workflow IR back into something a tool runs: BPMN 2.0 or a UiPath workflow.

The input is any workflow graph: one extracted into a catalog, or one the planner designed. The
output is a document the target tool opens, plus the list of what could not be carried over
exactly, such as conditions written for another expression language.

```python
from flowglyph.compilers import compile_workflow, load_planned

capability, workflow = load_planned("out/workflow.ir.yaml")
compiled = compile_workflow(workflow, capability, to="bpmn", engine="camunda8", catalog=catalog)
Path("invoice.bpmn").write_text(compiled.text)
```
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from flowglyph.catalog import Catalog
from flowglyph.compilers.bpmn import Engine, to_bpmn
from flowglyph.compilers.xaml import to_xaml
from flowglyph.errors import CatalogError
from flowglyph.ir import Capability, Workflow

type Target = Literal["bpmn", "xaml"]

SUFFIXES: dict[Target, str] = {"bpmn": ".bpmn", "xaml": ".xaml"}


@dataclass(frozen=True)
class Compilation:
    """A compiled document and what it could not express exactly."""

    text: str
    suffix: str
    warnings: tuple[str, ...]


def compile_workflow(
    workflow: Workflow,
    capability: Capability,
    *,
    to: Target,
    catalog: Catalog | None = None,
    engine: Engine = "bpmn",
) -> Compilation:
    """Compile `workflow`, the graph of `capability`, into a `to` document.

    `catalog` tells the compilers what each step calls: a BPMN process becomes a call activity,
    a UiPath workflow an Invoke Workflow File. `engine` adds Camunda 7 or Camunda 8 extensions to
    BPMN service tasks, so the result deploys as it is.
    """
    called = {
        node.capability: catalog.capabilities[node.capability]
        for node in workflow.nodes
        if catalog is not None and node.capability in catalog.capabilities
    }
    if to == "bpmn":
        text, warnings = to_bpmn(workflow, capability, called=called, engine=engine)
    else:
        text, warnings = to_xaml(workflow, capability, called=called)
    return Compilation(text, SUFFIXES[to], tuple(dict.fromkeys(warnings)))


def load_planned(path: str | Path) -> tuple[Capability, Workflow]:
    """The capability and workflow in a `workflow.ir.yaml` written by `flowglyph plan`.

    Raises:
        CatalogError: If the file does not hold a planned workflow.
    """
    file = Path(path)
    try:
        document = cast("dict[str, Any]", yaml.safe_load(file.read_text(encoding="utf-8")) or {})
        return (
            Capability.model_validate(document["capability"]),
            Workflow.model_validate(document["workflow"]),
        )
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        raise CatalogError(
            f"{file} is not a workflow written by flowglyph plan: {error}"
        ) from error


__all__ = ["SUFFIXES", "Compilation", "Engine", "Target", "compile_workflow", "load_planned"]
