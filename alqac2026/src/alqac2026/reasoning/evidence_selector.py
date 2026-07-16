from __future__ import annotations

import re
import unicodedata

from ..schemas import RetrievedChunk


def _ascii_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


def _evidence_priority(chunk: RetrievedChunk) -> int:
    text = _ascii_text(chunk.text)
    if any(
        marker in text
        for marker in ("quyet dinh", "tuyen xu", "hoi dong xet xu nhan dinh")
    ):
        return 3
    if any(marker in text for marker in ("xet thay", "co du can cu", "khong co can cu")):
        return 2
    if any(
        marker in text
        for marker in (
            "nguyen don trinh bay",
            "bi don trinh bay",
            "nguyen don yeu cau",
            "tai don khoi kien",
        )
    ):
        return 0
    return 1


def deduplicate_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    best_by_id: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        previous = best_by_id.get(chunk.chunk_id)
        if previous is None or chunk.score > previous.score:
            best_by_id[chunk.chunk_id] = chunk
    return rank_chunks_for_evidence(list(best_by_id.values()))


def rank_chunks_for_evidence(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return sorted(
        chunks,
        key=lambda chunk: (-_evidence_priority(chunk), -chunk.score, chunk.chunk_id),
    )


def select_case_evidence(
    chunks: list[RetrievedChunk], *, max_items: int = 2
) -> tuple[str, ...]:
    if max_items < 0:
        raise ValueError("max_items cannot be negative")
    return tuple(chunk.chunk_id for chunk in deduplicate_chunks(chunks)[:max_items])
