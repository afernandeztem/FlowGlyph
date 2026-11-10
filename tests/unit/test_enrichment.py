"""Enrichment describes what sources left undescribed, once per source change, and says so."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

import flowglyph
from flowglyph import enrichment
from flowglyph.cli.main import app
from flowglyph.enrichment import Cache, Description, Descriptions
from flowglyph.planner import StructuredModel

FIXTURES = Path(__file__).parents[1] / "fixtures"


class FakeModel:
    """Answers every capability it is asked about, and records each prompt."""

    def __init__(self, *, extra: bool = False, skip: str | None = None) -> None:
        self.prompts: list[str] = []
        self.extra = extra
        self.skip = skip

    def answer[T: BaseModel](self, system: str, prompt: str, shape: type[T]) -> T:
        assert "Use only the facts given" in system
        self.prompts.append(prompt)
        cards = [json.loads(line) for line in prompt.splitlines() if line.startswith("{")]
        answers = [
            Description(
                id=card["id"],
                summary=f"Runs {card['title']} for the finance team.",
                verb="process",
                entity="invoice",
                domain="unknown",
            )
            for card in cards
            if card["id"] != self.skip
        ]
        if self.extra:
            answers.append(
                Description(id="invented/x", summary="x", verb="x", entity="x", domain="x")
            )
        return shape.model_validate(Descriptions(capabilities=answers).model_dump())

    @property
    def asked(self) -> list[str]:
        return [
            json.loads(line)["id"]
            for prompt in self.prompts
            for line in prompt.splitlines()
            if line.startswith("{")
        ]


@pytest.fixture
def robots() -> flowglyph.Catalog:
    return flowglyph.extract(FIXTURES / "reframework")


def test_only_what_sources_left_undescribed_is_asked(robots: flowglyph.Catalog):
    model = FakeModel()
    assert isinstance(model, StructuredModel)
    result = enrichment.enrich(robots, model, Cache(), model_name="fake")
    assert "uipath/reframework/Main" in model.asked
    assert not [capability_id for capability_id in model.asked if "/activity/" in capability_id]
    main = result.catalog.get("uipath/reframework/Main")
    assert main.description == "Runs Main for the finance team."
    assert main.generated == ("description", "semantics")
    assert (main.semantics.verb, main.semantics.entity, main.semantics.domain) == (
        "process",
        "invoice",
        None,
    )
    settings = result.catalog.get("Framework/InitAllSettings")
    assert settings.description.startswith("Initialize, populate and output")
    assert settings.generated == ("semantics",)


def test_new_text_is_a_patch_and_idempotency_is_untouched(robots: flowglyph.Catalog):
    result = enrichment.enrich(robots, FakeModel(), Cache())
    before = robots.get("uipath/reframework/Main")
    after = result.catalog.get("uipath/reframework/Main")
    assert (before.version, after.version) == ("1.0.0", "1.0.1")
    assert after.idempotency == before.idempotency
    assert after.effects == before.effects


def test_answers_about_other_capabilities_are_ignored(robots: flowglyph.Catalog):
    cache = Cache()
    result = enrichment.enrich(robots, FakeModel(extra=True, skip="uipath/reframework/Main"), cache)
    assert "invented/x" not in cache.entries
    assert result.unanswered == ("uipath/reframework/Main",)
    assert "description" not in result.catalog.get("uipath/reframework/Main").generated


def test_answers_are_reused_until_the_source_changes(tmp_path: Path):
    project = shutil.copytree(FIXTURES / "reframework", tmp_path / "reframework")
    cache = Cache()
    first_model = FakeModel()
    enrichment.enrich(flowglyph.extract(project), first_model, cache)
    second_model = FakeModel()
    again = enrichment.enrich(flowglyph.extract(project), second_model, cache)
    assert second_model.prompts == []
    assert "uipath/reframework/Main" in again.reused
    main = project / "Main.xaml"
    main.write_text(main.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    third_model = FakeModel()
    enrichment.enrich(flowglyph.extract(project), third_model, cache)
    assert third_model.asked == ["uipath/reframework/Main"]


def test_the_cache_round_trips_and_ignores_another_prompt_version(tmp_path: Path):
    cache = Cache({"a": {"source_hash": "h", "summary": "s"}})
    file = tmp_path / enrichment.ENRICHMENT_FILE
    cache.save(file)
    assert Cache.load(file).entries == cache.entries
    document: dict[str, Any] = json.loads(file.read_text(encoding="utf-8"))
    document["prompt_version"] = 999
    file.write_text(json.dumps(document), encoding="utf-8")
    assert Cache.load(file).entries == {}


def test_extracting_again_reapplies_answers_without_new_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    out = tmp_path / "catalog"
    runner = CliRunner()
    assert (
        runner.invoke(app, ["extract", str(FIXTURES / "reframework"), "-o", str(out)]).exit_code
        == 0
    )
    model = FakeModel()

    def backend(via: str, model_name: str | None, effort: str | None) -> FakeModel:
        del via, model_name, effort
        return model

    monkeypatch.setattr("flowglyph.planner.backends.planner_backend", backend)
    enriched = runner.invoke(app, ["enrich", str(out), "--via", "fake"])
    assert enriched.exit_code == 0, enriched.output
    assert "Enriched" in enriched.output
    assert (out / enrichment.ENRICHMENT_FILE).is_file()
    card = (out / "capabilities" / "uipath_reframework_Main.md").read_text(encoding="utf-8")
    assert "written by a language model" in card
    lock = (out / "flowglyph.lock").read_text(encoding="utf-8")
    again = runner.invoke(app, ["extract", str(FIXTURES / "reframework"), "-o", str(out)])
    assert again.exit_code == 0, again.output
    assert "1.0.1 ->" not in again.output
    assert (out / "flowglyph.lock").read_text(encoding="utf-8") == lock
    assert flowglyph.load_catalog(out).get("uipath/reframework/Main").generated == (
        "description",
        "semantics",
    )


@pytest.mark.parametrize(
    ("description", "asked"),
    [
        ("Posts the invoice.", False),
        ("Sends approval e-mail.", False),
        ("请求审批并在SAP中过账发票。", False),
        ("[SAP] Posts the vendor invoice and returns the document number.", False),
        ("[Process title]\n[Process description]", True),
        ("Main workflow", True),
        ("", True),
    ],
)
def test_a_description_the_source_wrote_is_never_replaced(
    robots: flowglyph.Catalog, description: str, asked: bool
):
    stated = next(iter(robots)).model_copy(update={"title": "Main", "description": description})
    assert enrichment._needs_description(stated) is asked  # pyright: ignore[reportPrivateUsage]
