"""FlowGlyph: enterprise automations as a vendor-neutral IR for agents.

```python
import flowglyph
from flowglyph.views import effects_code

catalog = flowglyph.extract("path/to/uipath-project")
for capability in catalog.search("read configuration from excel", limit=5):
    print(capability.id, effects_code(capability.effects), capability.idempotency.mode)
catalog.save("out")
```
"""

from importlib.metadata import PackageNotFoundError, version

from flowglyph.adapters import Adapter, Diagnostic, Extraction, register_adapter
from flowglyph.catalog import Catalog, Lock, extract, load_catalog
from flowglyph.catalog.lock import Bump
from flowglyph.catalog.versioning import Change
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import (
    IR_VERSION,
    Capability,
    Edge,
    Effects,
    Idempotency,
    Node,
    Parameter,
    Security,
    Semantics,
    Source,
    Tri,
    Trigger,
    Workflow,
    export_json_schemas,
)

try:
    __version__ = version("flowglyph")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "IR_VERSION",
    "Adapter",
    "Bump",
    "Capability",
    "Catalog",
    "Change",
    "Diagnostic",
    "Edge",
    "Effects",
    "Extraction",
    "FlowGlyphError",
    "Idempotency",
    "Lock",
    "Node",
    "Parameter",
    "Security",
    "Semantics",
    "Source",
    "Tri",
    "Trigger",
    "Workflow",
    "__version__",
    "export_json_schemas",
    "extract",
    "load_catalog",
    "register_adapter",
]
