import shutil
import subprocess
from pathlib import Path

import pytest

import flowglyph
from flowglyph import sources
from flowglyph.errors import AdapterNotFoundError, CatalogError


def git(*arguments: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def monorepo(synthetic: Path, reframework: Path, tmp_path: Path) -> Path:
    root = tmp_path / "automations"
    shutil.copytree(synthetic / "invoices", root / "finance" / "invoices")
    shutil.copytree(reframework, root / "templates" / "reframework")
    (root / "apis").mkdir()
    shutil.copy(synthetic.parent / "openapi" / "payments.yaml", root / "apis")
    (root / "scratch").mkdir()
    shutil.copy(synthetic / "invoices" / "Steps" / "BookInvoice.xaml", root / "scratch")
    return root


def test_every_project_in_a_tree_is_extracted(monorepo: Path):
    catalog = flowglyph.extract(monorepo)
    providers = {c.id.split("/")[1] for c in catalog if c.kind == "workflow"}
    assert {"Invoices", "reframework", "automations"} <= providers
    assert catalog.get("createInvoice").source.provider == "openapi"
    assert set(catalog.lock.adapters) == {"uipath", "openapi"}
    assert "finance/invoices/Main.xaml" in catalog.lock.artifacts
    assert "templates/reframework/Main.xaml" in catalog.lock.artifacts
    assert "apis/payments.yaml" in catalog.lock.artifacts
    loose = catalog.get("uipath/automations/scratch/BookInvoice")
    assert loose.source.location == "scratch/BookInvoice.xaml"


def test_one_adapter_can_be_selected(monorepo: Path):
    catalog = flowglyph.extract(monorepo, adapter="openapi")
    assert {c.source.provider for c in catalog} == {"openapi"}
    with pytest.raises(AdapterNotFoundError, match="looked for: openapi"):
        flowglyph.extract(monorepo / "templates", adapter="openapi")


def test_nested_projects_are_not_read_twice(monorepo: Path):
    catalog = flowglyph.extract(monorepo, adapter="uipath")
    assert not [c for c in catalog if c.id.startswith("uipath/automations/finance")]


def test_local_paths_resolve_to_themselves(tmp_path: Path):
    assert sources.resolve(tmp_path).path == tmp_path
    with pytest.raises(CatalogError, match="does not exist"):
        sources.resolve(tmp_path / "missing")


def test_repositories_are_cloned_and_updated(
    synthetic: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("FLOWGLYPH_CACHE", str(tmp_path / "cache"))
    upstream = tmp_path / "upstream"
    shutil.copytree(synthetic / "invoices", upstream / "invoices")
    git("init", "-q", "-b", "main", cwd=upstream)
    git("add", ".", cwd=upstream)
    git("commit", "-q", "-m", "first", cwd=upstream)

    first = sources.resolve(f"file://{upstream}")
    assert first.path.is_relative_to(tmp_path / "cache")
    assert first.path.name == "upstream", "the checkout is named after the repository"
    assert (first.path / "invoices" / "Main.xaml").is_file()
    assert first.origin == f"file://{upstream}"

    (upstream / "invoices" / "Steps" / "BookInvoice.xaml").unlink()
    git("commit", "-q", "-am", "second", cwd=upstream)
    second = sources.resolve(f"file://{upstream}")
    assert second.revision != first.revision
    assert not (second.path / "invoices" / "Steps" / "BookInvoice.xaml").exists()

    catalog = flowglyph.extract(f"file://{upstream}")
    assert catalog.lock.origin == f"file://{upstream}"
    assert catalog.lock.revision == second.revision


def test_browser_links_to_folders_are_understood(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls: list[tuple[str, str | None, str]] = []

    def fake_checkout(url: str, ref: str | None, subdir: str = "") -> Path:
        calls.append((url, ref, subdir))
        (tmp_path / "Framework").mkdir(exist_ok=True)
        return tmp_path

    def fake_git(*arguments: str, cwd: Path | None = None) -> str:
        return "abc123"

    monkeypatch.setattr(sources, "_checkout", fake_checkout)
    monkeypatch.setattr(sources, "_git", fake_git)
    resolved = sources.resolve("https://github.com/UiPath/ReFrameWork/tree/master/Framework")
    assert calls == [("https://github.com/UiPath/ReFrameWork.git", "master", "Framework")]
    assert resolved.path == tmp_path / "Framework"
    assert resolved.revision == "abc123"
