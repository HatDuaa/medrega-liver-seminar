import json
import io
import tempfile
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from alqac2026.retrieval.budget import CallLedger, GlobalRateLimiter
from alqac2026.retrieval.cache import JsonRetrievalCache
from alqac2026.retrieval.client import NetworkDisabled, RetrievalClient, RetrievalError


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class RetrievalClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = JsonRetrievalCache(self.root / "cache")
        self.ledger_path = self.root / "ledger.json"
        self.client = self._client()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _client(self, token: str = "test-token") -> RetrievalClient:
        return RetrievalClient(
            base_url="https://example.invalid/",
            token=token,
            cache=self.cache,
            ledger=CallLedger(self.ledger_path, max_calls_per_case=2),
            rate_limiter=GlobalRateLimiter(self.root / "rate.json", min_interval_s=0),
            timeout_s=0.1,
        )

    @staticmethod
    def _response(results: list[dict[str, object]]) -> FakeResponse:
        return FakeResponse(json.dumps({"results": results}).encode("utf-8"))

    def _ledger_statuses(self) -> list[str]:
        payload = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        return [item["status"] for item in payload["attempts"]]

    def test_zero_one_and_many_results_are_supported(self) -> None:
        fixtures = [
            ("c0", [], []),
            ("c1", [{"score": 1.0, "text": "one", "chunk_id": "id-1"}], ["id-1"]),
            ("cn", [
                {"score": 1.0, "text": "one", "chunk_id": "id-1"},
                {"score": 0.5, "text": "two", "chunk_id": "id-2"},
            ], ["id-1", "id-2"]),
        ]
        for case_id, results, expected in fixtures:
            with self.subTest(case_id=case_id), patch(
                "alqac2026.retrieval.client.urllib.request.urlopen",
                return_value=self._response(results),
            ) as mocked:
                chunks = self.client.retrieve(case_id, "query", allow_network=True)
                self.assertEqual([chunk.chunk_id for chunk in chunks], expected)
                self.assertEqual(mocked.call_count, 1)

    def test_cache_hit_uses_zero_network_calls(self) -> None:
        self.cache.store("c1", "query", {"results": [
            {"score": 1.0, "text": "cached", "chunk_id": "cached-id"}
        ]})
        with patch("alqac2026.retrieval.client.urllib.request.urlopen") as mocked:
            result = self.client.retrieve("c1", "query")
        self.assertEqual(result[0].chunk_id, "cached-id")
        mocked.assert_not_called()
        self.assertFalse(self.ledger_path.exists())

    def test_two_clients_same_case_query_make_only_one_network_call(self) -> None:
        second_client = RetrievalClient(
            base_url="https://example.invalid",
            token="test-token",
            cache=JsonRetrievalCache(self.root / "cache"),
            ledger=CallLedger(self.ledger_path, max_calls_per_case=2),
            rate_limiter=GlobalRateLimiter(self.root / "rate.json", min_interval_s=0),
            timeout_s=0.1,
        )
        response_payload = [{"score": 1.0, "text": "shared", "chunk_id": "shared-id"}]

        def urlopen_once(*args: object, **kwargs: object) -> FakeResponse:
            return self._response(response_payload)

        with patch(
            "alqac2026.retrieval.client.urllib.request.urlopen",
            side_effect=urlopen_once,
        ) as mocked:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(client.retrieve, "same-case", "same query", allow_network=True)
                    for client in (self.client, second_client)
                ]
                results = [future.result(timeout=2) for future in futures]

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual([[chunk.chunk_id for chunk in result] for result in results], [["shared-id"], ["shared-id"]])
        self.assertEqual(CallLedger(self.ledger_path).count("same-case"), 1)

    def test_cache_miss_is_blocked_by_default_and_missing_token_is_blocked(self) -> None:
        with patch("alqac2026.retrieval.client.urllib.request.urlopen") as mocked:
            with self.assertRaises(NetworkDisabled):
                self.client.retrieve("c1", "query")
            with self.assertRaises(RetrievalError):
                self._client(token="").retrieve("c1", "query", allow_network=True)
        mocked.assert_not_called()

    def test_invalid_json_and_schema_are_not_retried_or_cached(self) -> None:
        payloads = [
            b"{",
            json.dumps({"missing_results": []}).encode(),
            json.dumps({"results": [{"score": "bad", "text": "x", "chunk_id": "id"}]}).encode(),
        ]
        for index, payload in enumerate(payloads):
            case_id = f"bad-{index}"
            with self.subTest(index=index), patch(
                "alqac2026.retrieval.client.urllib.request.urlopen",
                return_value=FakeResponse(payload),
            ) as mocked:
                with self.assertRaises((RetrievalError, ValueError)):
                    self.client.retrieve(case_id, "query", allow_network=True)
                self.assertEqual(mocked.call_count, 1)
                self.assertEqual(self.cache.entry_count(case_id), 0)

    def test_http_error_is_not_retried_and_records_status_without_token(self) -> None:
        error = urllib.error.HTTPError(
            "https://example.invalid/retrieve", 429, "rate", {}, io.BytesIO()
        )
        with patch(
            "alqac2026.retrieval.client.urllib.request.urlopen", side_effect=error
        ) as mocked:
            with self.assertRaises(RetrievalError) as caught:
                self.client.retrieve("http-case", "query", allow_network=True)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(self._ledger_statuses()[-1], "http_429")
        self.assertNotIn("test-token", str(caught.exception))
        error.close()

    def test_timeout_is_not_retried_and_records_unknown_delivery(self) -> None:
        with patch(
            "alqac2026.retrieval.client.urllib.request.urlopen", side_effect=TimeoutError("slow")
        ) as mocked:
            with self.assertRaises(RetrievalError):
                self.client.retrieve("timeout-case", "query", allow_network=True)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(self._ledger_statuses()[-1], "unknown_delivery")


if __name__ == "__main__":
    unittest.main()
