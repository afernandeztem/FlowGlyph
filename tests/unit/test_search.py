from flowglyph._internal.search import BM25Index, Document
from flowglyph._internal.text import first_line, tokenize


def test_tokenize_splits_identifiers():
    assert tokenize("in_ConfigFile GetHTTPResponse snake_case") == [
        "config", "file", "get", "http", "response", "snake", "case",
    ]  # fmt: skip


def test_plurals_match_singulars():
    assert tokenize("duplicates entries status address") == [
        "duplicate",
        "entry",
        "status",
        "address",
    ]


def test_first_line_truncates():
    assert first_line("one\ntwo") == "one"
    assert first_line("x" * 10, limit=5) == "xxxx…"


def test_bm25_ranks_weighted_matches_first():
    index = BM25Index(
        [
            Document("settings", [("InitAllSettings", 3), ("read config from excel", 1)]),
            Document("mail", [("SendMail", 3), ("send an email", 1)]),
            Document("other", [("Close applications", 3)]),
        ]
    )
    assert [key for key, _ in index.search("read the config settings")] == ["settings"]
    assert index.search("nothing matches") == []


def test_distinguishing_names():
    from flowglyph._internal.paths import distinguishing_names  # noqa: PLC0415

    assert distinguishing_names(["v2/API/API.edmx", "v4/API/API.edmx"]) == ["v2", "v4"]
    assert distinguishing_names(["specs/eu.yaml", "specs/us.yaml"]) == ["eu", "us"]
