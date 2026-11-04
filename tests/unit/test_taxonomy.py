import pytest

from flowglyph.adapters.uipath.taxonomy import default_taxonomy
from flowglyph.ir import Tri

UIPATH = "http://schemas.uipath.com/workflow/activities"
SYSTEM = "http://schemas.microsoft.com/netfx/2009/xaml/activities"


@pytest.mark.parametrize(
    ("namespace", "name", "category"),
    [
        (SYSTEM, "Assign", "control"),
        (UIPATH, "InvokeWorkflowFile", "control"),
        (UIPATH, "LogMessage", "logging"),
        (UIPATH, "GetQueueItem", "orchestrator"),
        (UIPATH, "ExcelReadRange", "integration.excel"),
        (UIPATH, "TypeInto", "ui"),
        (UIPATH, "InvokeCode", "scripting"),
        ("clr-namespace:Vendor.Unknown", "DoSomething", "unknown"),
    ],
)
def test_classification(namespace: str, name: str, category: str):
    assert default_taxonomy().classify(namespace, name).name == category


def test_activity_overrides_refine_category_defaults():
    taxonomy = default_taxonomy()
    asset = taxonomy.classify(UIPATH, "GetRobotAsset").effects
    queue = taxonomy.classify(UIPATH, "GetQueueItem").effects
    assert asset.mutates_state is Tri.NO
    assert queue.mutates_state is Tri.YES


def test_ui_automation_is_never_assumed_harmless():
    effects = default_taxonomy().classify(UIPATH, "Click").effects
    assert effects.mutates_state is Tri.UNKNOWN
    assert effects.has_side_effects
