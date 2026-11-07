"""Where automations are read from: a local folder or file, or a git repository.

Remote repositories are shallow-cloned into a cache directory and updated on later runs, so
pointing FlowGlyph at a GitHub URL is as cheap as pointing it at a folder after the first time.
Adapters never see URLs: they only ever read local files.
"""

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from flowglyph.errors import SourceError

_GITHUB_TREE = re.compile(
    r"^https://(?P<host>github\.com|gitlab\.com)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?"
    r"/(?:-/)?tree/(?P<ref>[^/]+)(?:/(?P<subdir>.+))?/?$"
)
_GIT_URL = re.compile(r"^(https?://|git@|ssh://|file://)\S+$")


@dataclass(frozen=True)
class Source:
    """A source resolved to a local path, with where it came from."""

    path: Path
    origin: str | None = None
    revision: str | None = None


def cache_directory() -> Path:
    """Where cloned repositories are kept: `$FLOWGLYPH_CACHE` or `~/.cache/flowglyph`."""
    configured = os.environ.get("FLOWGLYPH_CACHE")
    return Path(configured) if configured else Path.home() / ".cache" / "flowglyph"


def is_remote(spec: str) -> bool:
    """Whether `spec` names a git repository rather than a local path."""
    return bool(_GIT_URL.match(spec)) and not Path(spec).exists()


def resolve(spec: str | Path, *, ref: str | None = None) -> Source:
    """Turn a folder, file or repository URL into a local `Source`.

    GitHub and GitLab `.../tree/<ref>/<subdir>` URLs are understood, so a link copied from the
    browser works as is.

    Raises:
        SourceError: If the path does not exist, the ref is not a ref, or the repository cannot
            be cloned.
    """
    text = str(spec)
    if not is_remote(text):
        path = Path(text).expanduser()
        if not path.exists():
            raise SourceError(f"{path} does not exist")
        return Source(path=path)
    url, subdir = text, ""
    tree = _GITHUB_TREE.match(text)
    if tree:
        url = f"https://{tree['host']}/{tree['owner']}/{tree['repo']}.git"
        ref = ref or tree["ref"]
        subdir = tree["subdir"] or ""
    if ref is not None and ref.startswith("-"):
        # git would read it as an option: `--upload-pack=<command>` runs that command.
        raise SourceError(f"{ref!r} is not a branch, tag or commit")
    checkout = _checkout(url, ref, subdir)
    path = checkout / subdir if subdir else checkout
    if not path.exists():
        raise SourceError(f"{subdir} does not exist in {url}")
    return Source(path=path, origin=url, revision=_git("rev-parse", "HEAD", cwd=checkout))


def _checkout(url: str, ref: str | None, subdir: str = "") -> Path:
    """Clone or refresh `url`. With `subdir`, only that folder is downloaded."""
    if shutil.which("git") is None:
        raise SourceError("reading a repository needs git on PATH")
    key = hashlib.sha256(f"{url}@{ref or ''}:{subdir}".encode()).hexdigest()[:16]
    name = checkout_name(url)
    target = cache_directory() / "sources" / key / name
    if (target / ".git").is_dir():
        _git("fetch", "--depth", "1", "--end-of-options", "origin", ref or "HEAD", cwd=target)
        _git("reset", "--hard", "FETCH_HEAD", cwd=target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    branch = ["--branch", ref] if ref else []
    sparse = ["--filter=blob:none", "--sparse"] if subdir else []
    _git(
        "clone",
        "--depth",
        "1",
        "--single-branch",
        *sparse,
        *branch,
        "--end-of-options",
        url,
        target,
    )
    if subdir:
        _git("sparse-checkout", "set", subdir, cwd=target)
    return target


def checkout_name(url: str) -> str:
    """The folder a repository is checked out into: its name, safe on every file system."""
    last = re.split(r"[/\\]", url.rstrip("/\\").removesuffix(".git"))[-1]
    return re.sub(r"[^\w.-]+", "_", last) or "repository"


def _git(*arguments: str | Path, cwd: Path | None = None) -> str:
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
    completed = subprocess.run(
        # Windows limits paths to 260 characters unless git is told otherwise, and automation
        # repositories nest deeply.
        ["git", "-c", "core.longpaths=true", *arguments],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=600,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        raise SourceError(f"git {arguments[0]} failed: {detail[-1] if detail else 'no output'}")
    return completed.stdout.strip()
