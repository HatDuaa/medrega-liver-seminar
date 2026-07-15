from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ApiConfig
from .data_loader import load_law_corpus, load_public_cases
from .evaluation.metrics import outcome_metrics
from .law.index import LawIndex
from .private_view import to_private_view
from .reasoning.llm_runner import DeterministicRunner
from .reasoning.pipeline import PipelineConfig, run_batch
from .retrieval.budget import CallLedger, GlobalRateLimiter
from .retrieval.cache import JsonRetrievalCache, write_json_atomic
from .retrieval.client import NetworkDisabled, RetrievalClient
from .retrieval.query_planner import build_initial_queries
from .schemas import RunManifest
from .submission.builder import (
    build_submission,
    file_sha256,
    write_official_artifacts,
)
from .submission.validator import validate_submission


def _paths(project_root: Path) -> dict[str, Path]:
    return {
        "cases": project_root / "data" / "public" / "ALQAC2026_public_test.json",
        "laws": project_root / "data" / "public" / "corpus_law_pub.json",
        "cache": project_root / "data" / "retrieval-cache",
        "ledger": project_root / "data" / "runs" / "retrieval-ledger.json",
        "rate": project_root / "data" / "runs" / "retrieval-rate.json",
        "submission": project_root / "submissions" / "submission.json",
    }


def _client(project_root: Path, *, max_calls_per_case: int) -> RetrievalClient:
    paths = _paths(project_root)
    config = ApiConfig.from_project(project_root)
    return RetrievalClient(
        base_url=config.base_url,
        token=config.token,
        cache=JsonRetrievalCache(paths["cache"]),
        ledger=CallLedger(
            paths["ledger"], max_calls_per_case=max_calls_per_case
        ),
        rate_limiter=GlobalRateLimiter(
            paths["rate"], min_interval_s=config.min_interval_s
        ),
        timeout_s=config.timeout_s,
    )


def _json_print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def command_inspect_data(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    paths = _paths(root)
    cases = load_public_cases(paths["cases"])
    articles = load_law_corpus(paths["laws"])
    _json_print(
        {
            "cases": len(cases),
            "unique_case_ids": len({row["case_id"] for row in cases}),
            "law_articles": len(articles),
            "unique_law_pairs": len({(item.law_id, item.aid) for item in articles}),
        }
    )
    return 0


def command_retrieve_public(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    paths = _paths(root)
    cases = [to_private_view(row) for row in load_public_cases(paths["cases"])]
    selected = cases[args.start : args.start + args.limit]
    if not selected:
        raise ValueError("selected Public slice is empty")
    config = ApiConfig.from_project(root)
    if args.allow_network:
        config.require_token()
    client = _client(root, max_calls_per_case=args.max_calls_per_case)
    cache_hits = 0
    network_calls = 0
    chunks_found = 0
    for case in selected:
        for query in build_initial_queries(case, max_queries=args.max_queries):
            was_cached = client.cache.find(case.case_id, query) is not None
            try:
                chunks = client.retrieve(
                    case.case_id, query, allow_network=args.allow_network
                )
            except NetworkDisabled:
                continue
            cache_hits += int(was_cached)
            network_calls += int(not was_cached)
            chunks_found += len(chunks)
    _json_print(
        {
            "cases_processed": len(selected),
            "start": args.start,
            "queries_per_case": args.max_queries,
            "cache_hits": cache_hits,
            "network_calls": network_calls,
            "chunks_found": chunks_found,
        }
    )
    return 0


def command_run_public(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    paths = _paths(root)
    public_rows = load_public_cases(paths["cases"])
    private_cases = [to_private_view(row) for row in public_rows]
    articles = load_law_corpus(paths["laws"])
    law_index = LawIndex(articles)
    client = _client(root, max_calls_per_case=args.max_calls_per_case)
    outcome_runner = DeterministicRunner()
    pipeline_config = PipelineConfig(
        max_queries=args.max_queries,
        max_case_evidence=args.max_case_evidence,
        max_law_evidence=args.max_law_evidence,
    )
    predictions = run_batch(
        private_cases,
        law_index=law_index,
        retrieval_client=client,
        outcome_runner=outcome_runner,
        allow_network=False,
        config=pipeline_config,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = RunManifest(
        run_id=run_id,
        backend_id="deterministic_v0",
        config={
            "max_queries": args.max_queries,
            "max_case_evidence": args.max_case_evidence,
            "max_law_evidence": args.max_law_evidence,
            "private_view_only": True,
            "backend_metadata": outcome_runner.metadata.to_dict(),
        },
    )
    expected_ids = {case.case_id for case in private_cases}
    rows = build_submission(
        predictions,
        expected_case_ids=expected_ids,
        law_corpus=articles,
        cache=client.cache,
        manifest=manifest,
    )
    output_path = Path(args.output).resolve() if args.output else paths["submission"]
    output_path, artifact_manifest_path, artifact_manifest = write_official_artifacts(
        output_path, rows, manifest
    )

    run_dir = root / "data" / "runs" / run_id
    write_json_atomic(run_dir / "manifest.json", artifact_manifest)
    write_json_atomic(
        run_dir / "predictions-trace.json",
        [prediction.trace_row() for prediction in predictions],
    )
    metrics = outcome_metrics(public_rows, predictions)
    write_json_atomic(run_dir / "evaluation.json", metrics)
    _json_print(
        {
            "run_id": run_id,
            "submission": str(output_path),
            "artifact_manifest": str(artifact_manifest_path),
            "rows": len(rows),
            "outcome_accuracy": metrics["outcome_accuracy"],
            "case_evidence_nonempty": sum(bool(row["case_evidence"]) for row in rows),
            "law_evidence_total": sum(len(row["law_evidence"]) for row in rows),
        }
    )
    return 0


def command_validate_submission(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    paths = _paths(root)
    input_path = Path(args.input).resolve()
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    manifest_path = (
        Path(args.manifest).resolve()
        if args.manifest
        else input_path.with_suffix(".manifest.json")
    )
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_payload, dict):
        raise ValueError("artifact manifest must be a JSON object")
    artifact = manifest_payload.get("artifact")
    if not isinstance(artifact, dict) or artifact.get("type") != "official_submission":
        raise ValueError("artifact manifest is not an official submission manifest")
    if artifact.get("submission_filename") != input_path.name:
        raise ValueError("artifact manifest filename does not match submission")
    if artifact.get("submission_sha256") != file_sha256(input_path):
        raise ValueError("artifact manifest hash does not match submission")
    config = manifest_payload.get("config")
    if not isinstance(config, dict):
        raise ValueError("artifact manifest config must be an object")
    public_rows = load_public_cases(paths["cases"])
    articles = load_law_corpus(paths["laws"])
    manifest = RunManifest(
        run_id=manifest_payload.get("run_id"),
        backend_id=manifest_payload.get("backend_id"),
        config=config,
    )
    report = validate_submission(
        rows,
        expected_case_ids={row["case_id"] for row in public_rows},
        law_corpus=articles,
        cache=JsonRetrievalCache(paths["cache"]),
        manifest=manifest,
    )
    _json_print(report.to_dict())
    return 0 if report.valid else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alqac2026")
    parser.add_argument("--project-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-data")
    inspect_parser.set_defaults(handler=command_inspect_data)

    retrieve_parser = subparsers.add_parser("retrieve-public")
    retrieve_parser.add_argument("--start", type=int, default=0)
    retrieve_parser.add_argument("--limit", type=int, default=1)
    retrieve_parser.add_argument("--max-queries", type=int, choices=(1, 2), default=2)
    retrieve_parser.add_argument(
        "--max-calls-per-case", type=int, choices=(1, 2), default=2
    )
    retrieve_parser.add_argument("--allow-network", action="store_true")
    retrieve_parser.set_defaults(handler=command_retrieve_public)

    run_parser = subparsers.add_parser("run-public")
    run_parser.add_argument("--output")
    run_parser.add_argument("--max-queries", type=int, choices=(1, 2), default=2)
    run_parser.add_argument(
        "--max-calls-per-case", type=int, choices=(1, 2), default=2
    )
    run_parser.add_argument("--max-case-evidence", type=int, default=2)
    run_parser.add_argument("--max-law-evidence", type=int, default=3)
    run_parser.set_defaults(handler=command_run_public)

    validate_parser = subparsers.add_parser("validate-submission")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--manifest")
    validate_parser.set_defaults(handler=command_validate_submission)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
