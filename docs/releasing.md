# Releasing

Releases are cut from tags by `.github/workflows/release.yml`, which runs the test suite,
checks that the plugin manifests carry the tagged version, builds the sdist and wheel,
publishes them to PyPI with Trusted Publishing, and creates a GitHub release.

## Before the first public release

1. The repository is `afernandeztem/FlowGlyph`, public since 2026-11-07. If it moves, replace `afernandeztem/FlowGlyph` in `pyproject.toml`, `README.md`,
   `CONTRIBUTING.md` and `.github/ISSUE_TEMPLATE/config.yml`.
2. Enable private vulnerability reporting in the repository's security settings.
3. The README references its images and the walkthrough GIF by absolute
   `https://raw.githubusercontent.com/afernandeztem/FlowGlyph/main/docs/assets/...` URLs, so the
   PyPI page shows them too (done on 2026-11-07; keep it that way).
4. On PyPI, add a pending trusted publisher for `flowglyph`: workflow `release.yml`,
   environment `pypi`. Create the `pypi` environment in GitHub with required reviewers.
5. Check that the name is still free on PyPI.

## Every release

1. `make check` and `make diagrams` with no diff.
2. Optionally run the planner evaluation: `make test-llm` (billed).
3. Move the `Unreleased` entries in `CHANGELOG.md` under the new version and date.
4. Bump the plugin manifests to the new version: `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`
   and `gemini-extension.json`, and both `version` fields of `server.json`. The release workflow
   refuses a tag they do not match.
5. Commit, then tag: `git tag -a v0.1.0 -m "FlowGlyph 0.1.0"` (`-s` instead of `-a` once a signing
   key is configured).
6. `git push --follow-tags`. The workflow does the rest: after PyPI it publishes `server.json`
   to the MCP Registry with GitHub OIDC, so the registry lists the new version too. The registry
   checks ownership by reading the `mcp-name` line in the README on PyPI: keep it.

Extend the link references at the end of `CHANGELOG.md` on every release:

```markdown
[Unreleased]: https://github.com/afernandeztem/FlowGlyph/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/afernandeztem/FlowGlyph/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/afernandeztem/FlowGlyph/releases/tag/v0.1.0
```
