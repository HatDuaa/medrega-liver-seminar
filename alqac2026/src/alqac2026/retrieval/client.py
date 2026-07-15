from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from ..schemas import RetrievedChunk
from .budget import CallLedger, ExclusiveFileLock, GlobalRateLimiter
from .cache import JsonRetrievalCache


class NetworkDisabled(RuntimeError):
    pass


class RetrievalError(RuntimeError):
    pass


class RetrievalClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        cache: JsonRetrievalCache,
        ledger: CallLedger,
        rate_limiter: GlobalRateLimiter,
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.cache = cache
        self.ledger = ledger
        self.rate_limiter = rate_limiter
        self.timeout_s = timeout_s

    @staticmethod
    def _validate_response(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RetrievalError("retrieve response must be a JSON object")
        results = payload.get("results")
        if not isinstance(results, list):
            raise RetrievalError("retrieve response.results must be an array")
        for index, item in enumerate(results):
            if not isinstance(item, dict):
                raise RetrievalError(f"retrieve result {index} must be an object")
            try:
                RetrievedChunk(
                    score=item.get("score"),
                    text=item.get("text"),
                    chunk_id=item.get("chunk_id"),
                )
            except ValueError as exc:
                raise RetrievalError(f"invalid retrieve result {index}") from exc
        return payload

    def retrieve(
        self, case_id: str, query: str, *, allow_network: bool = False
    ) -> list[RetrievedChunk]:
        cached = self.cache.find(case_id, query)
        if cached is not None:
            return cached
        with ExclusiveFileLock(
            self.cache.case_lock_path(case_id),
            timeout_s=max(60.0, self.timeout_s + self.rate_limiter.min_interval_s + 10.0),
        ):
            # A second process may have populated the cache while this process waited.
            cached = self.cache.find(case_id, query)
            if cached is not None:
                return cached
            if not allow_network:
                raise NetworkDisabled(
                    f"cache miss for {case_id}; pass allow_network=True explicitly"
                )
            if not self._token:
                raise RetrievalError("team token is missing")

            attempt_id = self.ledger.reserve(case_id, query)
            self.rate_limiter.wait_turn()
            body = json.dumps(
                {"query": query, "case_id": case_id}, ensure_ascii=False
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{self.base_url}/retrieve",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-API-Key": self._token,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    raw_bytes = response.read()
            except urllib.error.HTTPError as exc:
                self.ledger.finish(attempt_id, f"http_{exc.code}")
                raise RetrievalError(f"retrieve failed with HTTP {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
                self.ledger.finish(attempt_id, "unknown_delivery")
                raise RetrievalError("retrieve delivery status is unknown") from exc

            try:
                payload = json.loads(raw_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.ledger.finish(attempt_id, "invalid_response")
                raise RetrievalError("retrieve returned invalid JSON") from exc

            try:
                valid_payload = self._validate_response(payload)
                chunks = self.cache.store(case_id, query, valid_payload)
            except (RetrievalError, ValueError, OSError):
                self.ledger.finish(attempt_id, "response_not_cached")
                raise
            self.ledger.finish(attempt_id, "completed")
            return chunks
