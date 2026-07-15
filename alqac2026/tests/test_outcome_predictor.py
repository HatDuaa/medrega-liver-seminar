import unittest

from alqac2026.reasoning.outcome_predictor import predict_outcome
from alqac2026.schemas import PrivateCase, RetrievedChunk


class OutcomePredictorTests(unittest.TestCase):
    def test_predicts_all_signal_branches_and_fallback(self) -> None:
        case = PrivateCase("c1", "hop dong vay va tra no")
        fixtures = [
            ("chap nhan yeu cau cua nguyen don", "A_WIN"),
            ("khong chap nhan yeu cau khoi kien", "B_WIN"),
            ("chap nhan mot phan yeu cau cua nguyen don", "PARTIAL_A_WIN"),
            ("chap nhan mot phan yeu cau phan to va khong chap nhan yeu cau khoi kien", "PARTIAL_B_WIN"),
        ]
        for text, expected in fixtures:
            with self.subTest(text=text):
                result = predict_outcome(case, [RetrievedChunk(1.0, text, "chunk")])
                self.assertEqual(result.prediction, expected)
        self.assertEqual(predict_outcome(case).prediction, "A_WIN")

    def test_rejects_non_private_case_and_invalid_chunk_items(self) -> None:
        case = PrivateCase("c1", "query")
        with self.assertRaises(TypeError):
            predict_outcome({"case_id": "c1"})  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            predict_outcome(case, ["raw chunk"])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
