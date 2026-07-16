import unittest

from alqac2026.retrieval.query_planner import build_initial_queries
from alqac2026.schemas import PrivateCase


class QueryPlannerTests(unittest.TestCase):
    def test_decision_v1_is_short_case_scoped_and_not_focus_biased(self) -> None:
        case = PrivateCase(
            "case_1",
            "Ông Nguyễn Văn A yêu cầu bà B trả 999.000.000 đồng và giao thửa đất 123.",
        )
        queries = build_initial_queries(
            case, max_queries=2, strategy="decision_v1"
        )
        self.assertEqual(len(queries), 2)
        self.assertEqual(len(set(queries)), 2)
        self.assertTrue(all(len(query) < 220 for query in queries))
        self.assertTrue(all("nguyễn văn a" not in query.casefold() for query in queries))
        self.assertTrue(any("quyết định" in query.casefold() for query in queries))
        self.assertTrue(any("nhận định" in query.casefold() for query in queries))

    def test_legacy_v0_remains_reproducible(self) -> None:
        case = PrivateCase("case_1", "Tranh chấp hợp đồng vay. Theo bạn ai thắng?")
        query = build_initial_queries(
            case, max_queries=1, strategy="legacy_v0"
        )[0]
        self.assertIn("chấp nhận yêu cầu khởi kiện của nguyên đơn", query)
        self.assertIn("tranh chấp hợp đồng vay", query.casefold())

    def test_rejects_unknown_strategy(self) -> None:
        with self.assertRaises(ValueError):
            build_initial_queries(
                PrivateCase("case_1", "query"), strategy="unknown"
            )


if __name__ == "__main__":
    unittest.main()
