from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from ..schemas import LawArticle


_TOKEN_RE = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)
_STOP_WORDS = frozenset(
    {
        "và",
        "của",
        "có",
        "các",
        "cho",
        "là",
        "được",
        "theo",
        "tại",
        "một",
        "những",
        "này",
        "với",
        "về",
        "do",
        "để",
        "trong",
        "khi",
        "người",
        "điều",
        "khoản",
    }
)


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text).casefold()
    return [
        token
        for token in _TOKEN_RE.findall(normalized)
        if len(token) > 1 and token not in _STOP_WORDS
    ]


@dataclass(frozen=True)
class LawHit:
    article: LawArticle
    score: float


class LawIndex:
    def __init__(self, articles: list[LawArticle], *, k1: float = 1.5, b: float = 0.75):
        if not articles:
            raise ValueError("law index requires at least one article")
        self.articles = tuple(articles)
        self.k1 = k1
        self.b = b
        self._term_counts: list[Counter[str]] = []
        self._lengths: list[int] = []
        self._articles_by_number: dict[tuple[str, int], LawArticle] = {}
        self._number_by_pair: dict[tuple[str, int], int] = {}
        next_number_by_law: Counter[str] = Counter()
        document_frequency: Counter[str] = Counter()
        for article in self.articles:
            next_number_by_law[article.law_id] += 1
            article_number = next_number_by_law[article.law_id]
            self._articles_by_number[(article.law_id, article_number)] = article
            self._number_by_pair[(article.law_id, article.aid)] = article_number
            counts = Counter(
                tokenize(
                    f"{article.text} {article.law_id} điều {article_number}"
                )
            )
            self._term_counts.append(counts)
            length = sum(counts.values())
            self._lengths.append(length)
            document_frequency.update(counts.keys())
        self._average_length = sum(self._lengths) / len(self._lengths)
        total = len(self.articles)
        self._idf = {
            term: math.log(1.0 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def article_by_number(self, law_id: str, article_number: int) -> LawArticle | None:
        return self._articles_by_number.get((law_id, article_number))

    def article_number(self, article: LawArticle) -> int | None:
        return self._number_by_pair.get((article.law_id, article.aid))

    def search(self, query: str, *, top_k: int = 5) -> list[LawHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        query_terms = Counter(tokenize(query))
        scored: list[LawHit] = []
        for article, counts, length in zip(
            self.articles, self._term_counts, self._lengths, strict=True
        ):
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1.0 - self.b + self.b * length / max(self._average_length, 1.0)
                )
                score += (
                    self._idf.get(term, 0.0)
                    * frequency
                    * (self.k1 + 1.0)
                    / denominator
                    * min(query_frequency, 2)
                )
            if score > 0:
                scored.append(LawHit(article=article, score=score))
        scored.sort(
            key=lambda hit: (-hit.score, hit.article.law_id, hit.article.aid)
        )
        return scored[:top_k]
