import unittest

from alqac2026.cli import build_parser


class CliParserTests(unittest.TestCase):
    def test_draft_and_retrieval_expose_query_strategy(self) -> None:
        parser = build_parser()
        draft = parser.parse_args(["run-draft", "--query-strategy", "decision_v1"])
        retrieve = parser.parse_args([
            "retrieve-public",
            "--query-strategy",
            "decision_v1",
        ])
        self.assertEqual(draft.query_strategy, "decision_v1")
        self.assertEqual(retrieve.query_strategy, "decision_v1")
        dev = parser.parse_args(["run-dev-draft", "--backend", "codex"])
        self.assertEqual(dev.backend, "codex")
        cv = parser.parse_args(["run-cv-draft", "--alpha", "1.0"])
        self.assertEqual(cv.alpha, 1.0)


if __name__ == "__main__":
    unittest.main()
