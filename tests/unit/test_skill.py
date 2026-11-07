"""The Agent Skill is valid, the same everywhere it is published, and installable."""

import json
import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from flowglyph.cli.main import app

ROOT = Path(__file__).parents[2]
PACKAGED = ROOT / "src" / "flowglyph" / "skill" / "SKILL.md"
MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    "gemini-extension.json",
)


def test_the_skill_has_the_frontmatter_agents_require():
    text = PACKAGED.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match is not None
    front = yaml.safe_load(match.group(1))
    assert front["name"] == "flowglyph"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", front["name"])
    assert 0 < len(front["description"]) <= 1024


def test_the_published_copy_is_the_packaged_one():
    published = ROOT / "skills" / "flowglyph" / "SKILL.md"
    assert published.read_text(encoding="utf-8") == PACKAGED.read_text(encoding="utf-8")


def test_every_manifest_names_the_same_plugin():
    manifests = [json.loads((ROOT / path).read_text(encoding="utf-8")) for path in MANIFESTS]
    assert {manifest["name"] for manifest in manifests} == {"flowglyph"}
    assert len({manifest["version"] for manifest in manifests}) == 1
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert [plugin["name"] for plugin in marketplace["plugins"]] == ["flowglyph"]


def test_the_command_installs_the_skill(tmp_path: Path):
    target = tmp_path / ".claude" / "skills" / "flowglyph"
    result = CliRunner().invoke(app, ["skill", "--to", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "SKILL.md").read_text(encoding="utf-8") == PACKAGED.read_text(encoding="utf-8")
