import unittest

from alqac2026.reasoning.naive_bayes import (
    TrainingExample,
    apply_high_precision_override,
    fit_naive_bayes,
    leave_one_out_predictions,
)
from alqac2026.schemas import OutcomePrediction, PrivateCase, RetrievedChunk


class NaiveBayesTests(unittest.TestCase):
    def test_fit_predict_uses_private_text_and_chunks(self) -> None:
        examples = [
            TrainingExample(
                PrivateCase("a1", "nghĩa vụ trả nợ"),
                (RetrievedChunk(1, "buộc bị đơn thanh toán toàn bộ", "a"),),
                "A_WIN",
            ),
            TrainingExample(
                PrivateCase("b1", "yêu cầu không có căn cứ"),
                (RetrievedChunk(1, "bác toàn bộ yêu cầu khởi kiện", "b"),),
                "B_WIN",
            ),
            TrainingExample(
                PrivateCase("pa1", "nhiều khoản bồi thường"),
                (RetrievedChunk(1, "chấp nhận một phần yêu cầu", "pa"),),
                "PARTIAL_A_WIN",
            ),
            TrainingExample(
                PrivateCase("pb1", "nguyên đơn chỉ được phần nhỏ"),
                (RetrievedChunk(1, "bác phần lớn yêu cầu", "pb"),),
                "PARTIAL_B_WIN",
            ),
        ]
        runner = fit_naive_bayes(examples, alpha=0.3)
        prediction = runner.predict(
            PrivateCase("new", "yêu cầu không có căn cứ"),
            [RetrievedChunk(1, "bác toàn bộ yêu cầu khởi kiện", "new_chunk")],
        )
        self.assertEqual(prediction.prediction, "B_WIN")
        self.assertFalse(runner.metadata.eligible_for_submission)

    def test_leave_one_out_returns_each_case_once(self) -> None:
        examples = [
            TrainingExample(PrivateCase(f"a{i}", "trả nợ ngân hàng"), (), "A_WIN")
            for i in range(2)
        ] + [
            TrainingExample(PrivateCase(f"b{i}", "bác yêu cầu"), (), "B_WIN")
            for i in range(2)
        ]
        predictions = leave_one_out_predictions(examples, alpha=1.0)
        self.assertEqual(set(predictions), {"a0", "a1", "b0", "b1"})
        self.assertTrue(all(item.rationale.startswith("Naive Bayes") for item in predictions.values()))

    def test_only_explicit_full_positive_decision_overrides_base_model(self) -> None:
        case = PrivateCase("c", "tranh chấp")
        base = OutcomePrediction("PARTIAL_A_WIN", 0.6, "Naive Bayes base")
        positive = apply_high_precision_override(
            case,
            [RetrievedChunk(1, "QUYẾT ĐỊNH: Chấp nhận yêu cầu của nguyên đơn.", "p")],
            base,
        )
        negative = apply_high_precision_override(
            case,
            [RetrievedChunk(1, "QUYẾT ĐỊNH: Không chấp nhận yêu cầu khởi kiện.", "n")],
            base,
        )
        self.assertEqual(positive.prediction, "A_WIN")
        self.assertIn("override", positive.rationale.casefold())
        self.assertEqual(negative, base)


if __name__ == "__main__":
    unittest.main()
