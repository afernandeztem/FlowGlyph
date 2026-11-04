# Releasing

Releases are cut from tags by `.github/workflows/release.yml`, which builds the sdist and
wheel, publishes them to PyPI with Trusted Publishing, and creates a GitHub release.

## Before the first public release

1. Create the GitHub repository and replace `flowglyph/flowglyph` in `pyproject.toml`,
   `CONTRIBUTING.md` and `.github/ISSUE_TEMPLATE/config.yml` with its real owner and name.
2. Enable private vulnerability reporting in the repository's security settings.
3. On PyPI, add a pending trusted publisher for `flowglyph`: workflow `release.yml`,
   environment `pypi`. Create the `pypi` environment in GitHub with required reviewers.
4. Check that the name is still free on PyPI.

## Every release

1. `make check` and `make diagrams` with no diff.
2. Optionally run the planner evaluation: `make test-llm` (billed).
3. Move the `Unreleased` entries in `CHANGELOG.md` under the new version and date.
4. Commit, then tag with a signed-off commit: `git tag -s v0.1.0 -m "FlowGlyph 0.1.0"`.
5. `git push --follow-tags`. The workflow does the rest.
