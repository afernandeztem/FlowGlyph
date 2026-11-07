# Releasing

Releases are cut from tags by `.github/workflows/release.yml`, which runs the test suite,
checks that the plugin manifests carry the tagged version, builds the sdist and wheel,
publishes them to PyPI with Trusted Publishing, and creates a GitHub release.

## Before the first public release

1. The repository is `afernandeztem/FlowGlyph`, private until the first release. Make it public in its
   settings. If it moves, replace `afernandeztem/FlowGlyph` in `pyproject.toml`, `README.md`,
   `CONTRIBUTING.md` and `.github/ISSUE_TEMPLATE/config.yml`.
2. Enable private vulnerability reporting in the repository's security settings.
3. The README references its images and the walkthrough GIF by relative path, which GitHub
   renders in a private repository and PyPI does not. Once the repository is public, make them
   absolute (`https://raw.githubusercontent.com/afernandeztem/FlowGlyph/main/docs/assets/...`)
   so the PyPI page shows them too.
4. On PyPI, add a pending trusted publisher for `flowglyph`: workflow `release.yml`,
   environment `pypi`. Create the `pypi` environment in GitHub with required reviewers.
5. Check that the name is still free on PyPI.

## Every release

1. `make check` and `make diagrams` with no diff.
2. Optionally run the planner evaluation: `make test-llm` (billed).
3. Move the `Unreleased` entries in `CHANGELOG.md` under the new version and date.
4. Bump the plugin manifests to the new version: `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`
   and `gemini-extension.json`. The release workflow refuses a tag they do not match.
5. Commit, then tag with a signed-off commit: `git tag -s v0.1.0 -m "FlowGlyph 0.1.0"`.
6. `git push --follow-tags`. The workflow does the rest.

After the first tag, add the link reference Keep a Changelog expects at the end of
`CHANGELOG.md`, and extend it on every release:

```markdown
[Unreleased]: https://github.com/afernandeztem/FlowGlyph/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/afernandeztem/FlowGlyph/releases/tag/v0.1.0
```
