import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alqac2026.law.index import LawIndex
from alqac2026.reasoning.pipeline import PipelineConfig, run_batch, run_case
from alqac2026.retrieval.budget import CallLedger, GlobalRateLimiter
from alqac2026.retrieval.cache import JsonRetrievalCache
from alqac2026.retrieval.client import RetrievalClient
from alqac2026.retrieval.query_planner import build_initial_queries
from alqac2026.schemas import LawArticle, PrivateCase


class OfflinePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = JsonRetrievalCache(self.root / "cache")
        self.client = RetrievalClient(
            base_url="https://example.invalid",
            token="",
            cache=self.cache,
            ledger=CallLedger(self.root / "ledger.json"),
            rate_limiter=GlobalRateLimiter(self.root / "rate.json", min_interval_s=0),
        )
        self.index = LawIndex([
            LawArticle("CIVIL", 1, "hop dong vay tai san tra no"),
            LawArticle("PROC", 2, "thu tuc xet xu"),
        ])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_offline_batch_uses_cache_and_never_opens_network(self) -> None:
        cached_case = PrivateCase("cached", "hop dong vay tra no")
        query = build_initial_queries(cached_case, max_queries=1)[0]
        self.cache.store("cached", query, {"results": [
            {"score": 1.0, "text": "chap nhan yeu cau cua nguyen don", "chunk_id": "known"}
        ]})
        missing_case = PrivateCase("missing", "thu tuc xet xu")
        config = PipelineConfig(max_queries=1, max_case_evidence=1, max_law_evidence=1)
        with patch("alqac2026.retrieval.client.urllib.request.urlopen") as network:
            predictions = run_batch(
                [cached_case, missing_case],
                law_index=self.index,
                retrieval_client=self.client,
                allow_network=False,
                config=config,
            )
        network.assert_not_called()
        self.assertEqual([item.case_id for item in predictions], ["cached", "missing"])
        self.assertEqual(predictions[0].case_evidence, ("known",))
        self.assertEqual(predictions[1].case_evidence, ())
        self.assertTrue(all(item.law_evidence for item in predictions))

    def test_pipeline_rejects_raw_public_mapping(self) -> None:
        with self.assertRaises(TypeError):
            run_case(
                {"case_id": "c", "case_query": "q", "verdict_label": "B_WIN"},  # type: ignore[arg-type]
                law_index=self.index,
                retrieval_client=self.client,
            )


if __name__ == "__main__":
    unittest.main()
