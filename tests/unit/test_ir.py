import pytest
from pydantic import ValidationError

from flowglyph.ir import Capability, Edge, Effects, Idempotency, Node, Source, Tri, Workflow
from flowglyph.views import effects_code, l0_card

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
    assert effects_code(effects) == "RwX"
    assert effects.has_side_effects


def test_pure_effects_have_no_side_effects():
    effects = Effects.combine([])
    assert effects_code(effects) == ""
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
    assert l0_card(capability) == {
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


def approval_workflow(join: str) -> Workflow:
    return Workflow(
        id="w",
        capability="w",
        nodes=(
            Node(id="validate", kind="invoke", label="validate"),
            Node(id="approve", kind="invoke", label="approve"),
            Node(id="create", kind="invoke", label="create", join=join),  # pyright: ignore[reportArgumentType]
        ),
        edges=(
            Edge(source="validate", target="approve", condition="amount > 10000"),
            Edge(source="validate", target="create"),
            Edge(source="approve", target="create"),
        ),
    )


@pytest.mark.parametrize(
    ("join", "large", "small"),
    [
        ("all", ["validate", "approve", "create"], ["validate"]),
        ("any", ["validate", "approve", "create"], ["validate", "create"]),
    ],
)
def test_join_decides_what_runs_after_an_optional_step(
    join: str, large: list[str], small: list[str]
):
    workflow = approval_workflow(join)
    assert workflow.simulate(lambda condition: True) == large
    assert workflow.simulate(lambda condition: False) == small


def test_skips_propagate():
    workflow = Workflow(
        id="w",
        capability="w",
        nodes=(
            Node(id="a", kind="invoke", label="a"),
            Node(id="b", kind="invoke", label="b"),
            Node(id="c", kind="invoke", label="c"),
        ),
        edges=(Edge(source="a", target="b", condition="x"), Edge(source="b", target="c")),
    )
    assert workflow.simulate(lambda condition: False) == ["a"]
