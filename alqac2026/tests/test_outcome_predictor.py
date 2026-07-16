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

    def test_party_request_is_not_treated_as_a_court_decision(self) -> None:
        case = PrivateCase("c1", "tranh chấp bồi thường nhiều khoản thiệt hại")
        result = predict_outcome(
            case,
            [
                RetrievedChunk(
                    1.0,
                    "Nguyên đơn trình bày và yêu cầu Tòa án chấp nhận toàn bộ yêu cầu khởi kiện.",
                    "chunk",
                )
            ],
        )
        self.assertEqual(result.prediction, "PARTIAL_A_WIN")
        self.assertIn("Fallback", result.rationale)

    def test_court_decision_handles_partial_and_counterclaim(self) -> None:
        case = PrivateCase("c1", "tranh chấp hợp đồng")
        partial_a = predict_outcome(
            case,
            [
                RetrievedChunk(
                    1.0,
                    "QUYẾT ĐỊNH: Chấp nhận một phần yêu cầu khởi kiện của nguyên đơn.",
                    "a",
                )
            ],
        )
        partial_b = predict_outcome(
            case,
            [
                RetrievedChunk(
                    1.0,
                    "QUYẾT ĐỊNH: Không chấp nhận yêu cầu khởi kiện; chấp nhận một phần yêu cầu phản tố.",
                    "b",
                )
            ],
        )
        self.assertEqual(partial_a.prediction, "PARTIAL_A_WIN")
        self.assertEqual(partial_b.prediction, "PARTIAL_B_WIN")

    def test_rejects_non_private_case_and_invalid_chunk_items(self) -> None:
        case = PrivateCase("c1", "query")
        with self.assertRaises(TypeError):
            predict_outcome({"case_id": "c1"})  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            predict_outcome(case, ["raw chunk"])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
