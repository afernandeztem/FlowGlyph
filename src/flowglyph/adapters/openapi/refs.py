"""Resolving local `$ref` pointers in an OpenAPI document; recursive schemas are cut short."""

from collections.abc import Mapping
from typing import Any, cast

from flowglyph.ir import JsonSchema

_MAX_DEPTH = 200


class RefResolver:
    """Resolves local `$ref` pointers inside one OpenAPI document.

    References to other files or URLs are left in place and recorded in `unresolved`, since
    adapters must not touch the network. Recursive schemas are cut at the first repetition and
    replaced by an object that names the reference it stands for.
    """

    def __init__(self, document: Mapping[str, Any]) -> None:
        self.document = document
        self.unresolved: set[str] = set()

    def resolve(self, node: Any) -> dict[str, Any]:
        """Follow `$ref` until reaching a concrete object."""
        seen: set[str] = set()
        current = node
        while isinstance(current, Mapping) and "$ref" in current:
            ref = str(cast("Mapping[str, Any]", current)["$ref"])
            if ref in seen:
                break
            seen.add(ref)
            target = self._lookup(ref)
            if target is None:
                return dict(cast("Mapping[str, Any]", current))
            current = target
        return dict(cast("Mapping[str, Any]", current)) if isinstance(current, Mapping) else {}

    def inline(self, schema: Any) -> JsonSchema:
        """A copy of `schema` with every local reference replaced by its target."""
        return cast("JsonSchema", self._inline(schema, (), 0))

    def _inline(self, node: Any, stack: tuple[str, ...], depth: int) -> Any:
        if isinstance(node, list):
            return [self._inline(item, stack, depth + 1) for item in cast("list[Any]", node)]
        if not isinstance(node, Mapping):
            return node
        mapping = cast("Mapping[str, Any]", node)
        if "$ref" in mapping:
            ref = str(mapping["$ref"])
            if ref in stack or len(stack) > _MAX_DEPTH:
                return {"type": "object", "x-recursive-ref": ref}
            target = self._lookup(ref)
            if target is None:
                return dict(mapping)
            return self._inline(target, (*stack, ref), depth + 1)
        return {key: self._inline(value, stack, depth + 1) for key, value in mapping.items()}

    def _lookup(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            self.unresolved.add(ref)
            return None
        node: Any = self.document
        for part in ref[2:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, Mapping) or key not in node:
                self.unresolved.add(ref)
                return None
            node = cast("Mapping[str, Any]", node)[key]
        return node
