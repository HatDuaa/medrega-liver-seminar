from __future__ import annotations

from typing import Any

from ..reasoning.llm_runner import backend_is_submission_eligible
from ..retrieval.cache import JsonRetrievalCache
from ..schemas import ALLOWED_LABELS, LawArticle, RunManifest, ValidationReport


_ROW_FIELDS = frozenset(
    {"case_id", "prediction", "case_evidence", "law_evidence"}
)
_LAW_FIELDS = frozenset({"law_id", "aid"})


def validate_submission(
    rows: Any,
    *,
    expected_case_ids: set[str],
    law_corpus: list[LawArticle],
    cache: JsonRetrievalCache,
    manifest: RunManifest,
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    if not backend_is_submission_eligible(manifest.backend_id):
        errors.append(
            f"backend {manifest.backend_id!r} is not eligible for official submission"
        )
    if not isinstance(rows, list):
        return ValidationReport(errors=tuple(errors + ["submission must be an array"]))

    valid_law_pairs = {(article.law_id, article.aid) for article in law_corpus}
    seen_cases: set[str] = set()
    for index, row in enumerate(rows):
        prefix = f"row {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if set(row) != _ROW_FIELDS:
            errors.append(f"{prefix} must contain exactly {sorted(_ROW_FIELDS)}")
            continue
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}.case_id must be a non-blank string")
            continue
        if case_id in seen_cases:
            errors.append(f"duplicate case_id: {case_id}")
        seen_cases.add(case_id)
        if case_id not in expected_case_ids:
            errors.append(f"unknown case_id: {case_id}")

        prediction = row.get("prediction")
        if prediction not in ALLOWED_LABELS:
            errors.append(f"{case_id}.prediction is invalid")

        case_evidence = row.get("case_evidence")
        if not isinstance(case_evidence, list) or any(
            not isinstance(item, str) or not item for item in case_evidence
        ):
            errors.append(f"{case_id}.case_evidence must be an array of strings")
        else:
            if len(case_evidence) != len(set(case_evidence)):
                errors.append(f"{case_id}.case_evidence contains duplicates")
            if case_id in expected_case_ids:
                known_chunks = cache.chunk_ids(case_id)
                unknown_chunks = set(case_evidence) - known_chunks
                if unknown_chunks:
                    errors.append(
                        f"{case_id}.case_evidence contains IDs absent from its raw cache"
                    )
            if not case_evidence:
                warnings.append(f"{case_id} has empty case_evidence")

        law_evidence = row.get("law_evidence")
        if not isinstance(law_evidence, list):
            errors.append(f"{case_id}.law_evidence must be an array")
            continue
        seen_law_pairs: set[tuple[str, int]] = set()
        for evidence_index, evidence in enumerate(law_evidence):
            if not isinstance(evidence, dict) or set(evidence) != _LAW_FIELDS:
                errors.append(
                    f"{case_id}.law_evidence[{evidence_index}] must contain exactly law_id and aid"
                )
                continue
            law_id = evidence.get("law_id")
            aid = evidence.get("aid")
            if (
                not isinstance(law_id, str)
                or not law_id
                or isinstance(aid, bool)
                or not isinstance(aid, int)
            ):
                errors.append(
                    f"{case_id}.law_evidence[{evidence_index}] has invalid types"
                )
                continue
            pair = (law_id, aid)
            if pair in seen_law_pairs:
                errors.append(f"{case_id}.law_evidence contains duplicate pair {pair}")
            seen_law_pairs.add(pair)
            if pair not in valid_law_pairs:
                errors.append(f"{case_id}.law_evidence contains unknown pair {pair}")

    missing = expected_case_ids - seen_cases
    extra = seen_cases - expected_case_ids
    if missing:
        errors.append(f"missing {len(missing)} expected case_id values")
    if extra:
        errors.append(f"contains {len(extra)} unexpected case_id values")
    if len(rows) != len(expected_case_ids):
        errors.append(
            f"submission has {len(rows)} rows; expected {len(expected_case_ids)}"
        )
    return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))
