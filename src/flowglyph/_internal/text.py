"""Tokenizing and trimming text for search and summaries."""

import re

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_WORD = re.compile(r"[^\W_]+")
_ARGUMENT_PREFIX = re.compile(r"^(in|out|io)_")
_SHORTEST_PLURAL = 4


def tokenize(text: str) -> list[str]:
    """Lower-case search tokens, splitting camelCase and snake_case identifiers.

    UiPath argument prefixes (`in_`, `out_`, `io_`) are dropped so that `in_ConfigFile`
    matches a search for "config file".
    """
    tokens: list[str] = []
    for raw in text.split():
        for word in _WORD.findall(_ARGUMENT_PREFIX.sub("", raw)):
            tokens.extend(
                _singular(part.lower()) for part in _CAMEL_BOUNDARY.split(word) if len(part) > 1
            )
    return tokens


def _singular(token: str) -> str:
    """Fold simple English plurals so "duplicates" matches "Duplicate"."""
    if len(token) > _SHORTEST_PLURAL and token.endswith("ies"):
        return token[:-3] + "y"
    if (
        len(token) >= _SHORTEST_PLURAL
        and token.endswith("s")
        and not token.endswith(("ss", "us", "is"))
    ):
        return token[:-1]
    return token


def first_line(text: str, limit: int = 120) -> str:
    """The first line of `text`, cut to `limit` characters."""
    line = text.strip().split("\n", 1)[0].strip()
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"
