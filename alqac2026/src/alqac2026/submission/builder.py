from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..retrieval.cache import JsonRetrievalCache, write_json_atomic
from ..schemas import CasePrediction, LawArticle, RunManifest
from .validator import validate_submission


def build_submission(
    predictions: list[CasePrediction],
    *,
    expected_case_ids: set[str],
    law_corpus: list[LawArticle],
    cache: JsonRetrievalCache,
    manifest: RunManifest,
) -> list[dict]:
    rows = [prediction.submission_row() for prediction in predictions]
    report = validate_submission(
        rows,
        expected_case_ids=expected_case_ids,
        law_corpus=law_corpus,
        cache=cache,
        manifest=manifest,
    )
    if not report.valid:
        raise ValueError("invalid official submission: " + "; ".join(report.errors))
    return rows


def write_submission_atomic(path: str | Path, rows: list[dict]) -> None:
    write_json_atomic(Path(path), rows)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_official_artifacts(
    submission_path: str | Path,
    rows: list[dict],
    manifest: RunManifest,
) -> tuple[Path, Path, dict[str, Any]]:
    output_path = Path(submission_path)
    write_submission_atomic(output_path, rows)
    artifact_manifest = manifest.to_dict()
    artifact_manifest["artifact"] = {
        "type": "official_submission",
        "submission_filename": output_path.name,
        "submission_sha256": file_sha256(output_path),
    }
    manifest_path = output_path.with_suffix(".manifest.json")
    write_json_atomic(manifest_path, artifact_manifest)
    return output_path, manifest_path, artifact_manifest
