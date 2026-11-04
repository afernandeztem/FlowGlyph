import pytest
from pydantic import ValidationError

from flowglyph.ir import Capability, Effects, Idempotency, Source, Tri

SOURCE = Source(provider="test", artifact="a", location="a.xaml", source_hash="sha256:0")


def test_unknown_counts_as_possible():
    assert Tri.UNKNOWN.possible
    assert Tri.YES.possible
    assert not Tri.NO.possible


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([Tri.NO, Tri.NO], Tri.NO),
        ([Tri.NO, Tri.UNKNOWN], Tri.UNKNOWN),
        ([Tri.UNKNOWN, Tri.YES], Tri.YES),
        ([], Tri.NO),
    ],
)
def test_combine_prefers_the_most_cautious_answer(values: list[Tri], expected: Tri):
    assert Tri.combine(values) is expected


def test_effects_code_marks_unknowns_in_lower_case():
    effects = Effects(
        reads=Tri.YES, mutates_state=Tri.UNKNOWN, destructive=Tri.NO, external=Tri.YES
    )
    assert effects.code() == "RwX"
    assert effects.has_side_effects


def test_pure_effects_have_no_side_effects():
    effects = Effects.combine([])
    assert effects.code() == ""
    assert not effects.has_side_effects


def test_card_is_compact():
    capability = Capability(
        id="x/y",
        kind="workflow",
        title="Y",
        description="Does y.\nMore detail.",
        input_schema={"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
        source=SOURCE,
    )
    assert capability.card() == {
        "id": "x/y",
        "d": "Does y.",
        "in": ["a"],
        "out": [],
        "e": "rwdx",
        "i": "none",
    }
    assert capability.inputs[0].required


def test_models_are_strict():
    with pytest.raises(ValidationError):
        Idempotency(mode="sometimes")  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValidationError):
        Idempotency(confidence=1.5)
