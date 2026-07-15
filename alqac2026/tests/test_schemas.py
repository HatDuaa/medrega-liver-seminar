import unittest

from alqac2026.schemas import (
    ALLOWED_LABELS,
    CasePrediction,
    LawArticle,
    LawEvidence,
    OutcomePrediction,
    PrivateCase,
    RetrievedChunk,
)


class SchemaTests(unittest.TestCase):
    def test_happy_path_serializes_only_submission_fields(self) -> None:
        prediction = CasePrediction(
            case_id="c1",
            prediction="A_WIN",
            case_evidence=("chunk-1",),
            law_evidence=(LawEvidence("LAW", 1),),
            confidence=0.8,
            rationale="trace only",
        )
        self.assertEqual(
            prediction.submission_row(),
            {
                "case_id": "c1",
                "prediction": "A_WIN",
                "case_evidence": ["chunk-1"],
                "law_evidence": [{"law_id": "LAW", "aid": 1}],
            },
        )
        self.assertIn("confidence", prediction.trace_row())

    def test_validation_rejects_blank_wrong_types_ranges_and_duplicates(self) -> None:
        factories = [
            lambda: PrivateCase("", "q"),
            lambda: RetrievedChunk(True, "text", "id"),
            lambda: RetrievedChunk(1.0, "", "id"),
            lambda: LawArticle("LAW", True, "text"),
            lambda: LawEvidence("LAW", True),
            lambda: OutcomePrediction("UNKNOWN", 0.5, "why"),
            lambda: OutcomePrediction(next(iter(ALLOWED_LABELS)), 1.1, "why"),
            lambda: CasePrediction("c", "A_WIN", ("dup", "dup")),
            lambda: CasePrediction("c", "A_WIN", law_evidence=(LawEvidence("L", 1), LawEvidence("L", 1))),
        ]
        for factory in factories:
            with self.subTest(factory=factory), self.assertRaises(ValueError):
                factory()


if __name__ == "__main__":
    unittest.main()
