# ADR-0008: Sources are folders, files or git repositories

- Status: accepted
- Date: 2026-11-06 (recorded after the feature shipped)

## Context

Automations live in git: one repository per UiPath project, a monorepo of iFlow packages, a
folder of API specs. Asking people to clone first and point FlowGlyph at the clone worked, but
made the most common case, "show me what is in this repository", two steps, and lost where the
catalog came from.

## Decision

- `extract`, and every command that accepts a source, takes a folder, a file, or a git URL. A
  GitHub or GitLab link to a folder (`.../tree/<ref>/<path>`) reads only that folder.
- Repositories are shallow-cloned (`--depth 1`, one branch) into
  `~/.cache/flowglyph/sources/<key>/<repository>`, with a sparse checkout when a folder is given.
  Later runs fetch and reset instead of cloning again. `FLOWGLYPH_CACHE` moves the cache.
- Git runs with prompts and LFS downloads disabled, so a private repository fails clearly
  instead of waiting for a password, and large binaries are not fetched.
- The lock file records the origin URL and the commit, so a catalog says exactly what it
  describes.
- Every source found under the path is extracted: all UiPath projects, EDMX documents, iFlows
  and OpenAPI specs in a repository become one catalog.

## Alternatives considered

- **The GitHub API or archive downloads.** No git needed, but tied to one host, rate-limited, and
  without a commit to record.
- **Leaving cloning to the user.** It remains possible, and is what CI should do; the URL form is
  for people exploring.

## Consequences

- Adapters never see a URL: they still read only local files, so they stay offline and
  deterministic.
- Repository content is untrusted data. It is parsed, never executed: no hooks, no build files,
  no scripts are run.
- The cache grows with every repository read; deleting it is always safe.
