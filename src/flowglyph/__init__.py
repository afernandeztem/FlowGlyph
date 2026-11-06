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

from flowglyph.adapters import Adapter, register_adapter
from flowglyph.catalog import Catalog, Lock, extract, load_catalog
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import (
    IR_VERSION,
    Capability,
    Edge,
    Effects,
    Idempotency,
    Node,
    Tri,
    Trigger,
    Workflow,
)

try:
    __version__ = version("flowglyph")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "IR_VERSION",
    "Adapter",
    "Capability",
    "Catalog",
    "Edge",
    "Effects",
    "FlowGlyphError",
    "Idempotency",
    "Lock",
    "Node",
    "Tri",
    "Trigger",
    "Workflow",
    "__version__",
    "extract",
    "load_catalog",
    "register_adapter",
]
