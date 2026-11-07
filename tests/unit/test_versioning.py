from typing import Any

import pytest

from flowglyph.catalog.lock import Bump, Lock, Shape, Signature
from flowglyph.catalog.versioning import assign_versions, lock_entry
from flowglyph.ir import Capability, Idempotency, Source


def capability(
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    *,
    required: list[str] | None = None,
    output_required: list[str] | None = None,
    invocable: bool = True,
) -> Capability:
    return Capability(
        id="test/Thing",
        kind="operation",
        title="Thing",
        input_schema={"type": "object", "properties": inputs or {}, "required": required or []},
        output_schema={
            "type": "object",
            "properties": outputs or {},
            "required": output_required or [],
        },
        invocable=invocable,
        source=Source(provider="test", artifact="thing", location="thing", source_hash="0"),
    )


def bump(old: Capability, new: Capability) -> Bump:
    return Signature.of(old).bump_to(Signature.of(new))


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
NULLABLE_STRING = {"type": ["string", "null"]}
STRING_OR_INTEGER = {"type": ["string", "integer"]}


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (capability({"a": STRING}), capability({"a": STRING}), Bump.NONE),
        (capability({"a": STRING}), capability({"a": STRING, "b": STRING}), Bump.MINOR),
        (
            capability({"a": STRING}),
            capability({"a": STRING, "b": STRING}, required=["b"]),
            Bump.MAJOR,
        ),
        (capability({"a": STRING}), capability({}), Bump.MAJOR),
        (capability({"a": STRING}), capability({"a": INTEGER}), Bump.MAJOR),
        (capability({"a": STRING}), capability({"a": STRING_OR_INTEGER}), Bump.MINOR),
        (capability({"a": STRING_OR_INTEGER}), capability({"a": STRING}), Bump.MAJOR),
        (capability({"a": NULLABLE_STRING}), capability({"a": STRING}), Bump.MAJOR),
        (capability({"a": STRING}), capability({"a": NULLABLE_STRING}), Bump.MINOR),
        (capability({"a": STRING}), capability({"a": {}}), Bump.MINOR),
        (capability({"a": {}}), capability({"a": STRING}), Bump.MAJOR),
        (capability({"a": STRING}, required=["a"]), capability({"a": STRING}), Bump.MINOR),
        (capability({}, {"r": STRING}), capability({}, {"r": STRING, "s": STRING}), Bump.MINOR),
        (capability({}, {"r": STRING}), capability({}, {}), Bump.MAJOR),
        (capability({}, {"r": STRING}), capability({}, {"r": NULLABLE_STRING}), Bump.MAJOR),
        (capability({}, {"r": NULLABLE_STRING}), capability({}, {"r": STRING}), Bump.MINOR),
        (capability({}, {"r": STRING}), capability({}, {"r": {}}), Bump.MAJOR),
        (
            capability({}, {"r": STRING}, output_required=["r"]),
            capability({}, {"r": STRING}),
            Bump.MAJOR,
        ),
        (capability(), capability(invocable=False), Bump.MAJOR),
        (capability(invocable=False), capability(), Bump.MINOR),
    ],
    ids=[
        "same",
        "optional input added",
        "required input added",
        "input removed",
        "input retyped",
        "input widened",
        "input narrowed",
        "input stops accepting null",
        "input starts accepting null",
        "input accepts anything",
        "input no longer accepts anything",
        "input no longer required",
        "output added",
        "output removed",
        "output becomes nullable",
        "output stops being nullable",
        "output may be anything",
        "output no longer required",
        "no longer invocable",
        "becomes invocable",
    ],
)
def test_breaking_changes_are_major(old: Capability, new: Capability, expected: Bump):
    assert bump(old, new) is expected


def test_nested_contracts_count_too():
    address = {
        "type": "object",
        "properties": {"city": STRING, "zip": STRING},
        "required": ["city"],
    }
    without_zip = {"type": "object", "properties": {"city": STRING}, "required": ["city"]}
    zip_required = {**address, "required": ["city", "zip"]}
    old = capability({"address": address})
    assert bump(old, capability({"address": without_zip})) is Bump.MAJOR
    assert bump(old, capability({"address": zip_required})) is Bump.MAJOR
    assert bump(capability({"address": without_zip}), old) is Bump.MINOR
    strings = {"type": "array", "items": STRING}
    numbers = {"type": "array", "items": INTEGER}
    assert bump(capability({"tags": strings}), capability({"tags": numbers})) is Bump.MAJOR
    assert bump(capability({}, {"tags": strings}), capability({}, {"tags": numbers})) is Bump.MAJOR


def test_wording_inside_a_schema_is_a_patch():
    choice = {"anyOf": [{"type": "string", "description": "A code."}, {"type": "null"}]}
    reworded = {"anyOf": [{"type": "string", "description": "An ISO code."}, {"type": "null"}]}
    old = capability({"code": choice})
    previous = Lock(capabilities={old.id: lock_entry(old, "1.0.0")})
    versioned, _, changes = assign_versions([capability({"code": reworded})], previous)
    assert [change.bump for change in changes] == [Bump.PATCH]
    assert versioned[0].version == "1.0.1"


def test_shapes_read_what_matters_from_a_schema():
    shape = Shape.of({"type": ["null", "string"], "properties": {"x": {}}, "required": ["x"]})
    assert shape.types == ("null", "string")
    assert shape.properties["x"] == Shape(required=True)
    assert Shape.of({"type": "array", "items": {"type": "integer"}}).items == Shape(
        types=("integer",)
    )


def test_declared_idempotency_was_inferred_by_nobody():
    assert Idempotency(provenance="declared").inferred_by is None
    assert Idempotency(provenance="inferred").inferred_by == "heuristic"
