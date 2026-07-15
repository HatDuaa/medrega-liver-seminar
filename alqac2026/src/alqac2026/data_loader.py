from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import LawArticle


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON from {path}") from exc


def validate_unique_case_ids(cases: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for index, row in enumerate(cases):
        if not isinstance(row, dict):
            raise ValueError(f"case at index {index} must be an object")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"case at index {index} has invalid case_id")
        if case_id in seen:
            raise ValueError(f"duplicate case_id: {case_id}")
        seen.add(case_id)


def load_public_cases(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(Path(path))
    if not isinstance(payload, list):
        raise ValueError("case dataset must be a JSON array")
    validate_unique_case_ids(payload)
    return payload


def load_law_corpus(path: str | Path) -> list[LawArticle]:
    payload = _load_json(Path(path))
    if not isinstance(payload, list):
        raise ValueError("law corpus must be a JSON array")

    articles: list[LawArticle] = []
    seen: set[tuple[str, int]] = set()
    for law_index, law in enumerate(payload):
        if not isinstance(law, dict):
            raise ValueError(f"law at index {law_index} must be an object")
        law_id = law.get("law_id")
        content = law.get("content")
        if not isinstance(law_id, str) or not law_id.strip():
            raise ValueError(f"law at index {law_index} has invalid law_id")
        if not isinstance(content, list):
            raise ValueError(f"law {law_id} content must be an array")
        for article_index, article in enumerate(content):
            if not isinstance(article, dict):
                raise ValueError(
                    f"article {article_index} in law {law_id} must be an object"
                )
            item = LawArticle(
                law_id=law_id,
                aid=article.get("aid"),
                text=article.get("content_Article"),
            )
            pair = (item.law_id, item.aid)
            if pair in seen:
                raise ValueError(f"duplicate law pair: {pair}")
            seen.add(pair)
            articles.append(item)
    return articles
