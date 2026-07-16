from __future__ import annotations

from dataclasses import dataclass

from ..law.index import LawIndex
from ..law.retriever import retrieve_law_evidence
from ..retrieval.client import NetworkDisabled, RetrievalClient
from ..retrieval.query_planner import build_initial_queries
from ..schemas import CasePrediction, PrivateCase, RetrievedChunk
from .evidence_selector import deduplicate_chunks, select_case_evidence
from .llm_runner import DeterministicRunner, OutcomeRunner


@dataclass(frozen=True)
class PipelineConfig:
    max_queries: int = 2
    max_case_evidence: int = 2
    max_law_evidence: int = 3
    query_strategy: str = "legacy_v0"


def collect_cached_or_network_chunks(
    case: PrivateCase,
    client: RetrievalClient,
    *,
    allow_network: bool,
    max_queries: int,
    query_strategy: str = "legacy_v0",
) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for query in build_initial_queries(
        case, max_queries=max_queries, strategy=query_strategy
    ):
        try:
            chunks.extend(client.retrieve(case.case_id, query, allow_network=allow_network))
        except NetworkDisabled:
            continue
    return deduplicate_chunks(chunks)


def run_case(
    case: PrivateCase,
    *,
    law_index: LawIndex,
    retrieval_client: RetrievalClient,
    outcome_runner: OutcomeRunner | None = None,
    allow_network: bool = False,
    config: PipelineConfig = PipelineConfig(),
) -> CasePrediction:
    if not isinstance(case, PrivateCase):
        raise TypeError("pipeline only accepts PrivateCase")
    chunks = collect_cached_or_network_chunks(
        case,
        retrieval_client,
        allow_network=allow_network,
        max_queries=config.max_queries,
        query_strategy=config.query_strategy,
    )
    runner = outcome_runner or DeterministicRunner()
    outcome = runner.predict(case, chunks)
    law_query = case.case_query + "\n" + "\n".join(
        chunk.text[:1600] for chunk in chunks
    )
    law_evidence = retrieve_law_evidence(
        law_index, law_query, top_k=config.max_law_evidence
    )
    return CasePrediction(
        case_id=case.case_id,
        prediction=outcome.prediction,
        case_evidence=select_case_evidence(
            chunks, max_items=config.max_case_evidence
        ),
        law_evidence=law_evidence,
        confidence=outcome.confidence,
        rationale=outcome.rationale,
    )


def run_batch(
    cases: list[PrivateCase],
    *,
    law_index: LawIndex,
    retrieval_client: RetrievalClient,
    outcome_runner: OutcomeRunner | None = None,
    allow_network: bool = False,
    config: PipelineConfig = PipelineConfig(),
) -> list[CasePrediction]:
    return [
        run_case(
            case,
            law_index=law_index,
            retrieval_client=retrieval_client,
            outcome_runner=outcome_runner,
            allow_network=allow_network,
            config=config,
        )
        for case in cases
    ]
