from __future__ import annotations

from ..schemas import LawEvidence
from .index import LawIndex


def retrieve_law_evidence(
    index: LawIndex, query: str, *, top_k: int = 3
) -> tuple[LawEvidence, ...]:
    seen: set[tuple[str, int]] = set()
    evidence: list[LawEvidence] = []
    for hit in index.search(query, top_k=max(top_k * 2, top_k)):
        pair = (hit.article.law_id, hit.article.aid)
        if pair in seen:
            continue
        seen.add(pair)
        evidence.append(LawEvidence(law_id=pair[0], aid=pair[1]))
        if len(evidence) == top_k:
            break
    return tuple(evidence)
