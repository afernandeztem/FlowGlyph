from collections.abc import Callable
from pathlib import Path

import flowglyph
from flowglyph.ir import export_json_schemas


def test_reframework_catalog_is_stable(
    reframework: Path, tmp_path: Path, golden: Callable[[str, str], None]
):
    out = flowglyph.extract(reframework).save(tmp_path / "out")
    golden("reframework/catalog.jsonl", (out / "catalog.jsonl").read_text(encoding="utf-8"))
    golden("reframework/graph.json", (out / "graph.json").read_text(encoding="utf-8"))
    golden("reframework/flowglyph.lock", (out / "flowglyph.lock").read_text(encoding="utf-8"))
    golden("reframework/INDEX.md", (out / "INDEX.md").read_text(encoding="utf-8"))


def test_taxonomy_of_reframework_activities(reframework: Path, golden: Callable[[str, str], None]):
    activities = sorted(
        f"{c.title}: {c.category} {c.effects.code() or '-'}"
        for c in flowglyph.extract(reframework)
        if c.kind == "activity"
    )
    golden("reframework/taxonomy.txt", "\n".join(activities) + "\n")


def test_committed_json_schemas_are_current(tmp_path: Path):
    for generated in export_json_schemas(tmp_path):
        committed = Path(__file__).parents[2] / "schemas" / generated.name
        assert committed.read_text() == generated.read_text(), "run `make schemas`"
