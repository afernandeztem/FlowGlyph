"""BM25 ranking over capabilities, with weighted fields and no dependencies."""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from flowglyph._internal.text import tokenize


@dataclass(frozen=True)
class Document:
    """A searchable text with its fields weighted by repetition."""

    key: str
    fields: Sequence[tuple[str, int]]


@dataclass
class BM25Index:
    """Okapi BM25 over a fixed set of documents.

    Small enough to avoid a dependency and fast enough for catalogs of tens of thousands of
    capabilities.
    """

    documents: Sequence[Document]
    k1: float = 1.5
    b: float = 0.75
    _frequencies: list[Counter[str]] = field(init=False, default_factory=list[Counter[str]])
    _idf: dict[str, float] = field(init=False, default_factory=dict[str, float])
    _average_length: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        for document in self.documents:
            counts: Counter[str] = Counter()
            for text, weight in document.fields:
                for token in tokenize(text):
                    counts[token] += weight
            self._frequencies.append(counts)
        total = len(self._frequencies) or 1
        self._average_length = sum(sum(c.values()) for c in self._frequencies) / total
        document_frequency: Counter[str] = Counter()
        for counts in self._frequencies:
            document_frequency.update(counts.keys())
        self._idf = {
            token: math.log(1 + (total - seen + 0.5) / (seen + 0.5))
            for token, seen in document_frequency.items()
        }

    def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        """Keys of the best matching documents with their scores, best first."""
        terms = tokenize(query)
        scored: list[tuple[str, float]] = []
        for document, counts in zip(self.documents, self._frequencies, strict=True):
            length = sum(counts.values())
            score = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                normaliser = self.k1 * (1 - self.b + self.b * length / (self._average_length or 1))
                score += self._idf[term] * frequency * (self.k1 + 1) / (frequency + normaliser)
            if score > 0:
                scored.append((document.key, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:limit]
