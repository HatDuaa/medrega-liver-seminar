from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..schemas import OutcomePrediction, PrivateCase, RetrievedChunk


BACKEND_REGISTRY: dict[str, dict[str, Any]] = {
    "deterministic_v0": {
        "eligible_for_submission": True,
        "kind": "algorithm",
    },
    "codex_cli": {
        "eligible_for_submission": False,
        "kind": "proprietary_dev_only",
    },
    "claude_cli": {
        "eligible_for_submission": False,
        "kind": "proprietary_dev_only",
    },
}


def backend_is_submission_eligible(backend_id: str) -> bool:
    backend = BACKEND_REGISTRY.get(backend_id)
    return bool(backend and backend["eligible_for_submission"])


@dataclass(frozen=True)
class BackendMetadata:
    backend_id: str
    model_id: str
    version: str
    eligible_for_submission: bool
    prompt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "model_id": self.model_id,
            "version": self.version,
            "eligible_for_submission": self.eligible_for_submission,
            "prompt_hash": self.prompt_hash,
        }


class OutcomeRunner(Protocol):
    metadata: BackendMetadata

    def predict(
        self, case: PrivateCase, chunks: list[RetrievedChunk]
    ) -> OutcomePrediction: ...


class DeterministicRunner:
    metadata = BackendMetadata(
        backend_id="deterministic_v0",
        model_id="bm25-rule-baseline",
        version="0.1.0",
        eligible_for_submission=True,
        prompt_hash=hashlib.sha256(b"deterministic_v0_rules_2026-07-16").hexdigest(),
    )

    def predict(
        self, case: PrivateCase, chunks: list[RetrievedChunk]
    ) -> OutcomePrediction:
        from .outcome_predictor import predict_outcome

        return predict_outcome(case, chunks)


@dataclass(frozen=True)
class CliRunResult:
    metadata: BackendMetadata
    raw_envelope: dict[str, Any]
    prediction: OutcomePrediction

    @property
    def backend_id(self) -> str:
        return self.metadata.backend_id


def _parse_prediction(payload: Any) -> OutcomePrediction:
    if not isinstance(payload, dict):
        raise ValueError("structured output must be an object")
    return OutcomePrediction(
        prediction=payload.get("prediction"),
        confidence=payload.get("confidence"),
        rationale=payload.get("rationale"),
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("CLI output is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("CLI JSON envelope must be an object")
    return payload


class CodexCliRunner:
    backend_id = "codex_cli"

    def __init__(self, *, model_id: str = "codex-cli", version: str = "unverified"):
        self.model_id = model_id
        self.version = version

    def run(
        self,
        prompt: str,
        *,
        schema_path: str | Path,
        isolated_cwd: str | Path,
        timeout_s: float = 120.0,
    ) -> CliRunResult:
        cwd = Path(isolated_cwd).resolve()
        schema = Path(schema_path).resolve()
        cwd.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            suffix=".json", dir=cwd, delete=False
        ) as output_handle:
            output_path = Path(output_handle.name)
        try:
            completed = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--output-schema",
                    str(schema),
                    "--output-last-message",
                    str(output_path),
                    "-",
                ],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                cwd=cwd,
                shell=False,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"codex CLI exited with {completed.returncode}")
            envelope = _parse_json_object(output_path.read_text(encoding="utf-8"))
            return CliRunResult(
                metadata=BackendMetadata(
                    backend_id=self.backend_id,
                    model_id=self.model_id,
                    version=self.version,
                    eligible_for_submission=False,
                    prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                ),
                raw_envelope=envelope,
                prediction=_parse_prediction(envelope),
            )
        finally:
            output_path.unlink(missing_ok=True)


class ClaudeCliRunner:
    backend_id = "claude_cli"

    def __init__(self, *, model_id: str = "claude-cli", version: str = "unverified"):
        self.model_id = model_id
        self.version = version

    def run(
        self,
        prompt: str,
        *,
        json_schema: dict[str, Any],
        isolated_cwd: str | Path,
        timeout_s: float = 120.0,
    ) -> CliRunResult:
        cwd = Path(isolated_cwd).resolve()
        cwd.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [
                "claude",
                "-p",
                "--tools",
                "",
                "--no-session-persistence",
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(json_schema, ensure_ascii=False),
            ],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            cwd=cwd,
            shell=False,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"claude CLI exited with {completed.returncode}")
        envelope = _parse_json_object(completed.stdout)
        structured = envelope.get("structured_output")
        if structured is None:
            result = envelope.get("result")
            if isinstance(result, str):
                structured = _parse_json_object(result)
            elif isinstance(result, dict):
                structured = result
        if structured is None:
            raise ValueError("claude envelope has no structured output")
        return CliRunResult(
            metadata=BackendMetadata(
                backend_id=self.backend_id,
                model_id=self.model_id,
                version=self.version,
                eligible_for_submission=False,
                prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            ),
            raw_envelope=envelope,
            prediction=_parse_prediction(structured),
        )
