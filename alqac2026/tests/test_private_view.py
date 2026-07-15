import unittest

from alqac2026.private_view import to_private_view
from alqac2026.reasoning.outcome_predictor import predict_outcome
from alqac2026.schemas import PrivateCase


class PrivateViewTests(unittest.TestCase):
    def test_private_view_copies_only_allowed_fields(self) -> None:
        public = {
            "case_id": "case-1",
            "case_query": "Noi dung vu an",
            "verdict_label": "B_WIN",
            "judgment_text": "LEAKED GOLD",
            "related_law_provisions": "LEAKED LAW GOLD",
        }

        private = to_private_view(public)

        self.assertEqual(private, PrivateCase("case-1", "Noi dung vu an"))
        self.assertFalse(hasattr(private, "verdict_label"))
        self.assertFalse(hasattr(private, "judgment_text"))
        self.assertFalse(hasattr(private, "related_law_provisions"))

    def test_missing_fields_and_raw_mapping_are_rejected(self) -> None:
        for row in ({"case_id": "case-1"}, {"case_query": "query"}, None):
            with self.subTest(row=row), self.assertRaises((TypeError, ValueError)):
                to_private_view(row)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            predict_outcome({"case_id": "case-1", "case_query": "query"})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
