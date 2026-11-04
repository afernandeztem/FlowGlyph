import re

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_WORD = re.compile(r"[^\W_]+")
_ARGUMENT_PREFIX = re.compile(r"^(in|out|io)_")


def tokenize(text: str) -> list[str]:
    """Lower-case search tokens, splitting camelCase and snake_case identifiers.

    UiPath argument prefixes (`in_`, `out_`, `io_`) are dropped so that `in_ConfigFile`
    matches a search for "config file".
    """
    tokens: list[str] = []
    for raw in text.split():
        for word in _WORD.findall(_ARGUMENT_PREFIX.sub("", raw)):
            tokens.extend(part.lower() for part in _CAMEL_BOUNDARY.split(word) if len(part) > 1)
    return tokens


def first_line(text: str, limit: int = 120) -> str:
    """The first line of `text`, cut to `limit` characters."""
    line = text.strip().split("\n", 1)[0].strip()
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"
