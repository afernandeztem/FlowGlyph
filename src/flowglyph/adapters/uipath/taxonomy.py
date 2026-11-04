import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any, cast

import yaml

from flowglyph.ir import Effects, Tri


@dataclass(frozen=True)
class Category:
    """A taxonomy category and the effects its activities have by default."""

    name: str
    effects: Effects


@dataclass(frozen=True)
class Taxonomy:
    """Maps UiPath activity types to categories and effects."""

    categories: dict[str, Effects]
    name_rules: tuple[tuple[re.Pattern[str], str], ...]
    namespace_rules: tuple[tuple[str, str], ...]
    activity_effects: dict[str, dict[str, Tri]]

    def classify(self, namespace: str, name: str) -> Category:
        """Category and effects of the activity `name` from XML namespace `namespace`."""
        category = self._category_name(namespace, name)
        effects = self.categories[category]
        overrides = self.activity_effects.get(name)
        if overrides:
            effects = effects.model_copy(update=overrides)
        return Category(category, effects)

    def _category_name(self, namespace: str, name: str) -> str:
        for pattern, category in self.name_rules:
            if pattern.search(name):
                return category
        for fragment, category in self.namespace_rules:
            if fragment in namespace:
                return category
        return "unknown"


def _tri(value: object) -> Tri:
    # PyYAML follows YAML 1.1, where bare yes/no are booleans.
    if value is True:
        return Tri.YES
    if value is False:
        return Tri.NO
    return Tri(str(value))


def _effects(raw: dict[str, object]) -> dict[str, Tri]:
    return {field: _tri(value) for field, value in raw.items()}


@cache
def default_taxonomy() -> Taxonomy:
    """The taxonomy shipped with FlowGlyph."""
    text = files(__package__).joinpath("taxonomy.yaml").read_text(encoding="utf-8")
    return parse_taxonomy(cast("dict[str, Any]", yaml.safe_load(text)))


def parse_taxonomy(document: dict[str, Any]) -> Taxonomy:
    """Build a `Taxonomy` from its YAML representation."""
    categories = {
        name: Effects(**_effects(spec["effects"])) for name, spec in document["categories"].items()
    }
    return Taxonomy(
        categories=categories,
        name_rules=tuple(
            (re.compile(rule["name"]), rule["category"]) for rule in document["rules"]
        ),
        namespace_rules=tuple(
            (rule["contains"], rule["category"]) for rule in document["namespaces"]
        ),
        activity_effects={
            name: _effects(raw) for name, raw in document.get("activities", {}).items()
        },
    )
