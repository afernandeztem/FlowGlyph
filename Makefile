.PHONY: install lint format typecheck test test-llm check diagrams schemas examples build clean

install:
	uv sync --all-extras
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run pyright

test:
	uv run pytest --cov

test-llm:
	uv run pytest -m llm

check: lint typecheck test

diagrams:
	cd scripts && npm ci && node export_diagrams.mjs

build:
	uv build

clean:
	rm -rf dist build .pytest_cache .ruff_cache .coverage htmlcov scripts/dist

examples:
	uv run python scripts/build_examples.py

schemas:
	uv run python -c "from flowglyph.ir import export_json_schemas; export_json_schemas('schemas')"
