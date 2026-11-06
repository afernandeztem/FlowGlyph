from pathlib import Path

import pytest

from flowglyph._internal.xml import parse_xml
from flowglyph.adapters.uipath.xaml import argument_direction, json_schema_for, load
from flowglyph.errors import AdapterError


@pytest.mark.parametrize(
    ("clr_type", "json_type"),
    [
        ("InArgument(x:String)", "string"),
        ("InArgument(x:Int32)", "integer"),
        ("OutArgument(x:Decimal)", "number"),
        ("InArgument(x:String[])", "array"),
        ("InArgument(scg:List(x:String))", "array"),
        ("InArgument(scg:Dictionary(x:String, x:Object))", "object"),
        ("InOutArgument(sd:DataTable)", "object"),
        ("InArgument(ui:QueueItem)", "object"),
    ],
)
def test_json_schema_for_argument_types(clr_type: str, json_type: str):
    assert json_schema_for(clr_type) == {"type": json_type, "x-clr-type": clr_type}


def test_argument_direction():
    assert argument_direction("InOutArgument(x:String)") == "inout"
    assert argument_direction("OutArgument(x:String)") == "out"
    assert argument_direction("Property(x:String)") == "in"


def test_documents_with_a_dtd_are_rejected(synthetic: Path):
    with pytest.raises(AdapterError, match="DTD"):
        load(synthetic / "doctype.xaml")


def test_a_dtd_after_a_long_comment_is_still_rejected():
    padding = b"<!--" + b" " * 8192 + b"-->"
    document = padding + b'<!DOCTYPE lolz [<!ENTITY lol "lol">]><Activity>&lol;</Activity>'
    with pytest.raises(AdapterError, match="DTD"):
        parse_xml(document, "padded.xaml")
