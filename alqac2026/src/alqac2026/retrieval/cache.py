from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..schemas import RetrievedChunk


_SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-blank string")
    normalized = unicodedata.normalize("NFC", query).casefold()
    normalized = " ".join(normalized.split())
    return normalized.rstrip(" .?!;,")


def make_cache_key(case_id: str, normalized_query: str) -> str:
    payload = json.dumps(
        [case_id, normalized_query], ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


class JsonRetrievalCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _case_path(self, case_id: str) -> Path:
        if not isinstance(case_id, str) or not _SAFE_CASE_ID.fullmatch(case_id):
            raise ValueError("case_id contains unsafe characters")
        return self.root / f"{case_id}.json"

    def case_lock_path(self, case_id: str) -> Path:
        return self._case_path(case_id).with_suffix(".json.lock")

    def _load(self, case_id: str) -> dict[str, Any]:
        path = self._case_path(case_id)
        if not path.exists():
            return {"version": 1, "case_id": case_id, "entries": {}}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid retrieval cache for {case_id}") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("case_id") != case_id
            or not isinstance(payload.get("entries"), dict)
        ):
            raise ValueError(f"invalid retrieval cache contract for {case_id}")
        return payload

    @staticmethod
    def _parse_chunks(raw_response: Any) -> list[RetrievedChunk]:
        if not isinstance(raw_response, dict):
            raise ValueError("cached response must be an object")
        results = raw_response.get("results")
        if not isinstance(results, list):
            raise ValueError("cached response results must be an array")
        chunks: list[RetrievedChunk] = []
        for item in results:
            if not isinstance(item, dict):
                raise ValueError("cached result item must be an object")
            chunks.append(
                RetrievedChunk(
                    score=item.get("score"),
                    text=item.get("text"),
                    chunk_id=item.get("chunk_id"),
                )
            )
        return chunks

    def find(self, case_id: str, query: str) -> list[RetrievedChunk] | None:
        normalized = normalize_query(query)
        key = make_cache_key(case_id, normalized)
        entry = self._load(case_id)["entries"].get(key)
        if entry is None:
            return None
        if not isinstance(entry, dict) or entry.get("normalized_query") != normalized:
            raise ValueError(f"cache key collision or corrupt entry for {case_id}")
        return self._parse_chunks(entry.get("raw_response"))

    def store(
        self, case_id: str, query: str, raw_response: dict[str, Any]
    ) -> list[RetrievedChunk]:
        chunks = self._parse_chunks(raw_response)
        normalized = normalize_query(query)
        key = make_cache_key(case_id, normalized)
        payload = self._load(case_id)
        payload["entries"][key] = {
            "normalized_query": normalized,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "raw_response": raw_response,
        }
        write_json_atomic(self._case_path(case_id), payload)
        return chunks

    def chunk_ids(self, case_id: str) -> set[str]:
        payload = self._load(case_id)
        ids: set[str] = set()
        for entry in payload["entries"].values():
            if not isinstance(entry, dict):
                raise ValueError(f"invalid cache entry for {case_id}")
            for chunk in self._parse_chunks(entry.get("raw_response")):
                ids.add(chunk.chunk_id)
        return ids

    def entry_count(self, case_id: str) -> int:
        return len(self._load(case_id)["entries"])
