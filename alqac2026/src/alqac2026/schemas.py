from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


ALLOWED_LABELS = frozenset(
    {"A_WIN", "B_WIN", "PARTIAL_A_WIN", "PARTIAL_B_WIN"}
)


def _non_blank(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


@dataclass(frozen=True)
class PrivateCase:
    case_id: str
    case_query: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _non_blank(self.case_id, "case_id"))
        object.__setattr__(
            self, "case_query", _non_blank(self.case_query, "case_query")
        )


@dataclass(frozen=True)
class RetrievedChunk:
    score: float
    text: str
    chunk_id: str

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("score must be numeric")
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "text", _non_blank(self.text, "text"))
        object.__setattr__(
            self, "chunk_id", _non_blank(self.chunk_id, "chunk_id")
        )

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "text": self.text, "chunk_id": self.chunk_id}


@dataclass(frozen=True)
class LawArticle:
    law_id: str
    aid: int
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "law_id", _non_blank(self.law_id, "law_id"))
        if isinstance(self.aid, bool) or not isinstance(self.aid, int):
            raise ValueError("aid must be an integer")
        object.__setattr__(self, "text", _non_blank(self.text, "article text"))


@dataclass(frozen=True)
class LawEvidence:
    law_id: str
    aid: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "law_id", _non_blank(self.law_id, "law_id"))
        if isinstance(self.aid, bool) or not isinstance(self.aid, int):
            raise ValueError("aid must be an integer")

    def to_dict(self) -> dict[str, Any]:
        return {"law_id": self.law_id, "aid": self.aid}


@dataclass(frozen=True)
class OutcomePrediction:
    prediction: str
    confidence: float
    rationale: str

    def __post_init__(self) -> None:
        if self.prediction not in ALLOWED_LABELS:
            raise ValueError(f"invalid prediction label: {self.prediction!r}")
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(
            self, "rationale", _non_blank(self.rationale, "rationale")
        )


@dataclass(frozen=True)
class CasePrediction:
    case_id: str
    prediction: str
    case_evidence: tuple[str, ...] = ()
    law_evidence: tuple[LawEvidence, ...] = ()
    confidence: float = 0.0
    rationale: str = "deterministic baseline"

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _non_blank(self.case_id, "case_id"))
        if self.prediction not in ALLOWED_LABELS:
            raise ValueError(f"invalid prediction label: {self.prediction!r}")
        if len(set(self.case_evidence)) != len(self.case_evidence):
            raise ValueError("case_evidence contains duplicates")
        law_pairs = {(item.law_id, item.aid) for item in self.law_evidence}
        if len(law_pairs) != len(self.law_evidence):
            raise ValueError("law_evidence contains duplicates")

    def submission_row(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "prediction": self.prediction,
            "case_evidence": list(self.case_evidence),
            "law_evidence": [item.to_dict() for item in self.law_evidence],
        }
    def trace_row(self) -> dict[str, Any]:
        row = self.submission_row()
        row.update({"confidence": self.confidence, "rationale": self.rationale})
        return row


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    backend_id: str
    config: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _non_blank(self.run_id, "run_id"))
        object.__setattr__(
            self, "backend_id", _non_blank(self.backend_id, "backend_id")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "backend_id": self.backend_id,
            "config": dict(self.config),
        }


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
