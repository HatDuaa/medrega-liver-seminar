from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..schemas import OutcomePrediction, PrivateCase, RetrievedChunk
from .llm_runner import BackendMetadata, codex_executable


BATCH_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "predictions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "prediction": {
                        "type": "string",
                        "enum": ["A_WIN", "PARTIAL_A_WIN", "B_WIN", "PARTIAL_B_WIN"],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                },
                "required": ["case_id", "prediction", "confidence", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["predictions"],
    "additionalProperties": False,
}


def build_batch_prompt(
    items: list[tuple[PrivateCase, list[RetrievedChunk]]],
    *,
    max_chunk_chars: int = 2200,
) -> str:
    if max_chunk_chars < 200:
        raise ValueError("max_chunk_chars must be at least 200")
    cases: list[dict[str, Any]] = []
    for case, chunks in items:
        if not isinstance(case, PrivateCase):
            raise TypeError("dev batch only accepts PrivateCase")
        cases.append(
            {
                "case_id": case.case_id,
                "case_query": case.case_query,
                "retrieved_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text[:max_chunk_chars],
                    }
                    for chunk in chunks
                ],
            }
        )
    payload = json.dumps(cases, ensure_ascii=False, separators=(",", ":"))
    return f"""Bạn đang làm bản đánh giá DEV-ONLY cho các vụ án dân sự Việt Nam.
Chỉ dùng case_query và retrieved_chunks dưới đây. Không được giả định có nhãn ẩn.

Nhãn:
- A_WIN: nguyên đơn thắng toàn bộ hoặc phần cốt lõi áp đảo.
- PARTIAL_A_WIN: nguyên đơn được chấp nhận một phần đáng kể và nhìn chung thắng nhiều hơn.
- B_WIN: yêu cầu cốt lõi của nguyên đơn bị bác, nguyên đơn hầu như không nhận được lợi ích.
- PARTIAL_B_WIN: nguyên đơn được một phần nhỏ nhưng bị đơn nhìn chung thắng nhiều hơn, hoặc phản tố/yêu cầu độc lập phía bị đơn chiếm ưu thế.

Phải phân biệt lời trình bày/yêu cầu của đương sự với nhận định hoặc quyết định thật của Tòa.
Nếu chunk là mảnh văn bản, ưu tiên câu tuyên xử, bác/chấp nhận, nghĩa vụ Tòa buộc thực hiện và tỷ lệ yêu cầu được chấp nhận.
Trả đúng một prediction cho mỗi case_id, không thiếu và không thêm.

CASES_JSON={payload}
"""


def parse_batch_prediction_payload(
    payload: Any, expected_case_ids: set[str]
) -> dict[str, OutcomePrediction]:
    if not isinstance(payload, dict) or not isinstance(payload.get("predictions"), list):
        raise ValueError("batch output must contain predictions array")
    parsed: dict[str, OutcomePrediction] = {}
    for index, row in enumerate(payload["predictions"]):
        if not isinstance(row, dict):
            raise ValueError(f"prediction {index} must be an object")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or case_id not in expected_case_ids:
            raise ValueError(f"prediction {index} has unknown case_id")
        if case_id in parsed:
            raise ValueError(f"duplicate case_id in batch output: {case_id}")
        parsed[case_id] = OutcomePrediction(
            prediction=row.get("prediction"),
            confidence=row.get("confidence"),
            rationale=row.get("rationale"),
        )
    if set(parsed) != expected_case_ids:
        raise ValueError("batch output case IDs do not match expected IDs")
    return parsed


@dataclass(frozen=True)
class BatchDraftResult:
    metadata: BackendMetadata
    predictions: dict[str, OutcomePrediction]
    raw_payload: dict[str, Any]


class CodexBatchDraftRunner:
    def __init__(self, *, version: str = "0.65.0") -> None:
        self.version = version

    def run(
        self,
        items: list[tuple[PrivateCase, list[RetrievedChunk]]],
        *,
        isolated_root: str | Path,
        timeout_s: float = 1200.0,
        max_chunk_chars: int = 2200,
    ) -> BatchDraftResult:
        prompt = build_batch_prompt(items, max_chunk_chars=max_chunk_chars)
        expected_ids = {case.case_id for case, _ in items}
        root = Path(isolated_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp_dir:
            cwd = Path(temp_dir)
            schema_path = cwd / "schema.json"
            output_path = cwd / "output.json"
            schema_path.write_text(
                json.dumps(BATCH_OUTPUT_SCHEMA, ensure_ascii=False), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    codex_executable(),
                    "exec",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(output_path),
                    "-",
                ],
                input=prompt,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout_s,
                cwd=cwd,
                shell=False,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()[-1200:]
                raise RuntimeError(
                    f"codex CLI exited with {completed.returncode}: {detail}"
                )
            try:
                raw_payload = json.loads(output_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("codex batch output is not valid JSON") from exc
        predictions = parse_batch_prediction_payload(raw_payload, expected_ids)
        return BatchDraftResult(
            metadata=BackendMetadata(
                backend_id="codex_cli",
                model_id="codex-cli",
                version=self.version,
                eligible_for_submission=False,
                prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            ),
            predictions=predictions,
            raw_payload=raw_payload,
        )
