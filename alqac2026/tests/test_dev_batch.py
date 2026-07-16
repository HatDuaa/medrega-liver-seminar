import json
import unittest

from alqac2026.reasoning.dev_batch import (
    build_batch_prompt,
    parse_batch_prediction_payload,
)
from alqac2026.schemas import PrivateCase, RetrievedChunk


class DevBatchTests(unittest.TestCase):
    def test_prompt_contains_only_private_case_and_cached_chunks(self) -> None:
        prompt = build_batch_prompt([
            (
                PrivateCase("case_1", "Ai thắng trong tranh chấp này?"),
                [RetrievedChunk(2.0, "QUYẾT ĐỊNH: Bác yêu cầu khởi kiện", "seg_1")],
            )
        ])
        self.assertIn("case_1", prompt)
        self.assertIn("seg_1", prompt)
        self.assertNotIn("verdict_label", prompt)
        self.assertNotIn("court_verdict", prompt)

    def test_payload_requires_exact_ids_and_valid_labels(self) -> None:
        payload = {
            "predictions": [
                {
                    "case_id": "case_1",
                    "prediction": "B_WIN",
                    "confidence": 0.8,
                    "rationale": "Court rejected the claim.",
                }
            ]
        }
        parsed = parse_batch_prediction_payload(payload, {"case_1"})
        self.assertEqual(parsed["case_1"].prediction, "B_WIN")
        for bad in (
            {"predictions": []},
            {"predictions": [{**payload["predictions"][0], "case_id": "other"}]},
            {"predictions": [{**payload["predictions"][0], "prediction": "INVALID"}]},
        ):
            with self.subTest(bad=json.dumps(bad)), self.assertRaises(ValueError):
                parse_batch_prediction_payload(bad, {"case_1"})


if __name__ == "__main__":
    unittest.main()
