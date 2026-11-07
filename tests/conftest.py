import json
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"

type GoldenCheck = Callable[[str, str], None]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="rewrite golden files from the current output instead of comparing",
    )


@pytest.fixture
def reframework() -> Path:
    return FIXTURES / "reframework"


@pytest.fixture
def synthetic() -> Path:
    return FIXTURES / "synthetic"


@pytest.fixture
def no_anthropic_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No key or token in the environment, and no `ant auth login` profile on disk."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


@pytest.fixture
def golden(request: pytest.FixtureRequest) -> GoldenCheck:
    update = bool(request.config.getoption("--update-golden"))

    def check(name: str, actual: str) -> None:
        path = GOLDEN / name
        if update:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            return
        assert path.exists(), f"missing golden file {name}; run pytest --update-golden"
        expected = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            assert json.loads(actual) == json.loads(expected)
        else:
            assert actual == expected

    return check
