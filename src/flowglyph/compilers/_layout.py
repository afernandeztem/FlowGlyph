"""A left-to-right layered layout, so compiled diagrams open readable in a modeler."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """Where one element sits: its top-left corner and size."""

    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> tuple[int, int]:
        """The middle of the left side, where incoming flows end."""
        return self.x, self.y + self.height // 2

    @property
    def right(self) -> tuple[int, int]:
        """The middle of the right side, where outgoing flows start."""
        return self.x + self.width, self.y + self.height // 2


def layers(nodes: Sequence[str], edges: Sequence[tuple[str, str]]) -> dict[str, int]:
    """The column of each node: one more than the deepest node pointing to it.

    Edges that close a loop are ignored, so every node gets a finite column.
    """
    successors: defaultdict[str, list[str]] = defaultdict(list)
    for source, target in edges:
        successors[source].append(target)
    order: list[str] = []
    state: dict[str, int] = {}
    back: set[tuple[str, str]] = set()

    def visit(node: str) -> None:
        state[node] = 1
        for target in successors[node]:
            if state.get(target) == 1:
                back.add((node, target))
            elif target not in state:
                visit(target)
        state[node] = 2
        order.append(node)

    for node in nodes:
        if node not in state:
            visit(node)
    column = dict.fromkeys(nodes, 0)
    for node in reversed(order):
        for target in successors[node]:
            if (node, target) not in back:
                column[target] = max(column.get(target, 0), column[node] + 1)
    return column


def place(
    nodes: Sequence[str],
    edges: Sequence[tuple[str, str]],
    sizes: dict[str, tuple[int, int]],
) -> dict[str, Box]:
    """A box for every node, columns left to right and nodes of a column top to bottom."""
    column = layers(nodes, edges)
    rows: defaultdict[int, int] = defaultdict(int)
    boxes: dict[str, Box] = {}
    for node in nodes:
        width, height = sizes.get(node, (100, 80))
        index = rows[column[node]]
        rows[column[node]] += 1
        x = 160 + column[node] * 180 + (100 - width) // 2
        y = 80 + index * 130 + (80 - height) // 2
        boxes[node] = Box(x, y, width, height)
    return boxes
