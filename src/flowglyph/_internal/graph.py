"""Graph steps every adapter needs: following flows through folded nodes, and marking joins."""

from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence

from flowglyph.ir import Edge, Node

type Flow = tuple[str, str | None]
"""Where a flow goes and under which condition, if any."""


def follow(outgoing: Mapping[str, Sequence[Flow]], kept: Collection[str]) -> list[Edge]:
    """Edges between kept nodes, following flows through the nodes that were folded away.

    A flow keeps the first condition met on its way, so two branches that meet again in a
    folded node still reach the next kept node as two edges, each with its own condition.
    """
    edges: set[Edge] = set()
    for start in kept:
        seen: set[Flow] = set()
        pending = list(outgoing.get(start, ()))
        while pending:
            target, condition = pending.pop()
            if target in kept:
                edges.add(Edge(source=start, target=target, condition=condition))
            elif (target, condition) not in seen:
                seen.add((target, condition))
                pending.extend(
                    (next_target, condition or next_condition)
                    for next_target, next_condition in outgoing.get(target, ())
                )
    return sorted(edges, key=lambda edge: (edge.source, edge.target, edge.condition or ""))


def with_joins(
    nodes: Iterable[Node], edges: Iterable[Edge], parallel: Collection[str] = ()
) -> list[Node]:
    """Nodes where several edges meet wait for any of them, unless they join parallel branches."""
    incoming = Counter(edge.target for edge in edges)
    return [
        node.model_copy(update={"join": "any"})
        if incoming[node.id] > 1 and node.id not in parallel
        else node
        for node in nodes
    ]
