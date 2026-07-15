import json
import tempfile
import unittest
from pathlib import Path

from alqac2026.retrieval.cache import JsonRetrievalCache, make_cache_key, normalize_query


class RetrievalCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = JsonRetrievalCache(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_normalization_and_key_are_exact_and_case_scoped(self) -> None:
        normalized = normalize_query("  Alpha\n BETA?! ")
        self.assertEqual(normalized, "alpha beta")
        self.assertEqual(normalized, normalize_query("alpha beta."))
        self.assertNotEqual(make_cache_key("c1", normalized), make_cache_key("c2", normalized))
        self.assertNotEqual(make_cache_key("c1", normalized), make_cache_key("c1", "beta alpha"))
        for invalid in ("", "   ", None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                normalize_query(invalid)  # type: ignore[arg-type]

    def test_store_find_empty_and_many_results_are_visible_in_json(self) -> None:
        self.assertIsNone(self.cache.find("c1", "query"))
        empty = self.cache.store("c1", "empty", {"results": []})
        self.assertEqual(empty, [])
        chunks = self.cache.store("c1", "Query!", {"results": [
            {"score": 0.9, "text": "first", "chunk_id": "a"},
            {"score": 0.8, "text": "second", "chunk_id": "b"},
        ]})
        self.assertEqual([chunk.chunk_id for chunk in chunks], ["a", "b"])
        self.assertEqual([chunk.chunk_id for chunk in self.cache.find("c1", " query ") or []], ["a", "b"])
        self.assertEqual(self.cache.chunk_ids("c1"), {"a", "b"})
        payload = json.loads((self.root / "c1.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["case_id"], "c1")
        self.assertEqual(len(payload["entries"]), 2)

    def test_rejects_unsafe_case_corrupt_cache_and_invalid_response_schema(self) -> None:
        with self.assertRaises(ValueError):
            self.cache.find("../escape", "query")
        for raw in ({}, {"results": "bad"}, {"results": [{"score": "bad", "text": "x", "chunk_id": "id"}]}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.cache.store("c1", "query", raw)  # type: ignore[arg-type]
        (self.root / "bad.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.cache.find("bad", "query")


if __name__ == "__main__":
    unittest.main()
