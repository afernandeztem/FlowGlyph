from flowglyph._internal.graph import follow, with_joins
from flowglyph.ir import Node, Workflow


def test_branches_that_meet_in_a_folded_node_keep_their_conditions():
    outgoing = {
        "check": [("prep", "true"), ("prep", "false")],
        "prep": [("call", None)],
    }
    edges = follow(outgoing, {"check", "call"})
    assert [(e.source, e.target, e.condition) for e in edges] == [
        ("check", "call", "false"),
        ("check", "call", "true"),
    ]
    nodes = with_joins(
        [Node(id="check", kind="decision", label="?"), Node(id="call", kind="activity", label="!")],
        edges,
    )
    workflow = Workflow(id="w", capability="w", nodes=tuple(nodes), edges=tuple(edges))
    for truth in ("true", "false"):
        assert workflow.simulate(lambda c, truth=truth: c == truth) == ["check", "call"]


def test_a_flow_keeps_the_first_condition_on_its_way():
    outgoing = {"a": [("x", "c1")], "x": [("y", "c2")], "y": [("b", None)]}
    assert [e.condition for e in follow(outgoing, {"a", "b"})] == ["c1"]


def test_loops_through_folded_nodes_terminate():
    outgoing = {"a": [("x", None)], "x": [("y", None)], "y": [("x", None), ("b", None)]}
    assert [(e.source, e.target) for e in follow(outgoing, {"a", "b"})] == [("a", "b")]


def test_parallel_joins_wait_for_every_branch():
    nodes = [Node(id="join", kind="decision", label="+")]
    edges = follow({"a": [("join", None)], "b": [("join", None)]}, {"a", "b", "join"})
    assert with_joins(nodes, edges)[0].join == "any"
    assert with_joins(nodes, edges, parallel={"join"})[0].join == "all"
