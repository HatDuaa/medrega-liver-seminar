import json
import tempfile
import unittest
from pathlib import Path

from alqac2026.data_loader import load_law_corpus, load_public_cases


class DataLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, name: str, payload: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_public_loader_accepts_unique_rows_and_preserves_public_fields(self) -> None:
        rows = [
            {"case_id": "c1", "case_query": "q1", "verdict_label": "A_WIN"},
            {"case_id": "c2", "case_query": "q2", "judgment_text": "gold"},
        ]
        self.assertEqual(load_public_cases(self._write("cases.json", rows)), rows)

    def test_public_loader_rejects_bad_container_rows_ids_and_json(self) -> None:
        fixtures = [
            {"not": "an array"},
            ["not an object"],
            [{"case_id": ""}],
            [{"case_id": "same"}, {"case_id": "same"}],
        ]
        for index, payload in enumerate(fixtures):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                load_public_cases(self._write(f"bad-{index}.json", payload))
        bad_json = self.root / "invalid.json"
        bad_json.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_public_cases(bad_json)

    def test_law_loader_flattens_articles_and_rejects_invalid_contracts(self) -> None:
        valid = [
            {
                "law_id": "LAW-1",
                "content": [
                    {"aid": 1, "content_Article": "Article one"},
                    {"aid": 2, "content_Article": "Article two"},
                ],
            }
        ]
        articles = load_law_corpus(self._write("laws.json", valid))
        self.assertEqual([(item.law_id, item.aid) for item in articles], [("LAW-1", 1), ("LAW-1", 2)])

        invalid = [
            {"not": "an array"},
            [{"law_id": "", "content": []}],
            [{"law_id": "LAW", "content": "not-array"}],
            [{"law_id": "LAW", "content": [{"aid": True, "content_Article": "x"}]}],
            [{"law_id": "LAW", "content": [
                {"aid": 1, "content_Article": "x"},
                {"aid": 1, "content_Article": "duplicate"},
            ]}],
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                load_law_corpus(self._write(f"bad-law-{index}.json", payload))


if __name__ == "__main__":
    unittest.main()
