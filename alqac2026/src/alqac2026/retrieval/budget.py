from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cache import normalize_query, write_json_atomic


class BudgetExceeded(RuntimeError):
    pass


OFFICIAL_MAX_CALLS_PER_CASE = 2


class ExclusiveFileLock(AbstractContextManager["ExclusiveFileLock"]):
    """Small cross-process lock implemented with atomic file creation."""

    def __init__(
        self, path: str | Path, *, timeout_s: float = 30.0, stale_after_s: float = 120.0
    ) -> None:
        self.path = Path(path)
        self.timeout_s = timeout_s
        self.stale_after_s = stale_after_s
        self._held = False

    def __enter__(self) -> "ExclusiveFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                    handle.write(f"{os.getpid()} {time.time()}\n")
                self._held = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.stale_after_s:
                        self.path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for lock {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False


class CallLedger:
    def __init__(self, path: str | Path, *, max_calls_per_case: int = 2) -> None:
        if not 1 <= max_calls_per_case <= OFFICIAL_MAX_CALLS_PER_CASE:
            raise ValueError(
                f"max_calls_per_case must be between 1 and {OFFICIAL_MAX_CALLS_PER_CASE}"
            )
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.max_calls_per_case = max_calls_per_case

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "attempts": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("retrieval ledger is corrupt") from exc
        if not isinstance(payload, dict) or not isinstance(
            payload.get("attempts"), list
        ):
            raise ValueError("retrieval ledger has invalid schema")
        return payload

    def reserve(self, case_id: str, query: str) -> str:
        with ExclusiveFileLock(self.lock_path):
            payload = self._load()
            count = sum(
                1 for item in payload["attempts"] if item.get("case_id") == case_id
            )
            if count >= self.max_calls_per_case:
                raise BudgetExceeded(
                    f"network call cap reached for {case_id}: {count}/{self.max_calls_per_case}"
                )
            attempt_id = uuid.uuid4().hex
            payload["attempts"].append(
                {
                    "attempt_id": attempt_id,
                    "case_id": case_id,
                    "query": normalize_query(query),
                    "status": "intent",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            write_json_atomic(self.path, payload)
            return attempt_id

    def finish(self, attempt_id: str, status: str) -> None:
        with ExclusiveFileLock(self.lock_path):
            payload = self._load()
            matches = [
                item
                for item in payload["attempts"]
                if item.get("attempt_id") == attempt_id
            ]
            if len(matches) != 1:
                raise ValueError(f"unknown retrieval attempt: {attempt_id}")
            matches[0]["status"] = status
            matches[0]["finished_at"] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(self.path, payload)

    def count(self, case_id: str) -> int:
        with ExclusiveFileLock(self.lock_path):
            payload = self._load()
            return sum(
                1 for item in payload["attempts"] if item.get("case_id") == case_id
            )


class GlobalRateLimiter:
    def __init__(self, state_path: str | Path, *, min_interval_s: float = 5.0) -> None:
        if min_interval_s < 0:
            raise ValueError("min_interval_s cannot be negative")
        self.state_path = Path(state_path)
        self.lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        self.min_interval_s = min_interval_s

    def wait_turn(self) -> None:
        with ExclusiveFileLock(self.lock_path):
            previous = 0.0
            if self.state_path.exists():
                try:
                    payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                    previous = float(payload.get("last_attempt_epoch", 0.0))
                except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    raise ValueError("rate limiter state is corrupt") from exc
            delay = self.min_interval_s - (time.time() - previous)
            if delay > 0:
                time.sleep(delay)
            now = time.time()
            write_json_atomic(
                self.state_path,
                {
                    "last_attempt_epoch": now,
                    "last_attempt_at": datetime.now(timezone.utc).isoformat(),
                },
            )
