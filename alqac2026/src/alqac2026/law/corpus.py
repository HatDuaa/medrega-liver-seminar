from __future__ import annotations

from ..schemas import LawArticle


def law_pairs(articles: list[LawArticle]) -> set[tuple[str, int]]:
    return {(article.law_id, article.aid) for article in articles}


def validate_law_pair(law_id: str, aid: int, articles: list[LawArticle]) -> bool:
    return (law_id, aid) in law_pairs(articles)
