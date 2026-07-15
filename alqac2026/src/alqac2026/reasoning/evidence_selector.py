from __future__ import annotations

from ..schemas import RetrievedChunk


def deduplicate_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    best_by_id: dict[str, RetrievedChunk] = {}
    for chunk in chunks:
        previous = best_by_id.get(chunk.chunk_id)
        if previous is None or chunk.score > previous.score:
            best_by_id[chunk.chunk_id] = chunk
    return sorted(best_by_id.values(), key=lambda chunk: (-chunk.score, chunk.chunk_id))


def select_case_evidence(
    chunks: list[RetrievedChunk], *, max_items: int = 2
) -> tuple[str, ...]:
    if max_items < 0:
        raise ValueError("max_items cannot be negative")
    return tuple(chunk.chunk_id for chunk in deduplicate_chunks(chunks)[:max_items])
