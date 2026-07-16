import unittest

from alqac2026.evaluation.metrics import outcome_metrics
from alqac2026.schemas import CasePrediction


class QualityMetricsTests(unittest.TestCase):
    def test_report_includes_distribution_per_label_and_fallbacks(self) -> None:
        rows = [
            {"case_id": "a", "verdict_label": "A_WIN"},
            {"case_id": "b", "verdict_label": "B_WIN"},
        ]
        predictions = [
            CasePrediction("a", "A_WIN", rationale="court decision"),
            CasePrediction("b", "A_WIN", rationale="Fallback: prior"),
        ]
        report = outcome_metrics(rows, predictions)
        self.assertEqual(report["prediction_distribution"]["A_WIN"], 2)
        self.assertEqual(report["per_label"]["A_WIN"]["recall"], 1.0)
        self.assertEqual(report["per_label"]["B_WIN"]["recall"], 0.0)
        self.assertEqual(report["fallback_count"], 1)
        self.assertEqual(report["fallback_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
