import json
import tempfile
import time
import unittest
from pathlib import Path

from alqac2026.retrieval.budget import BudgetExceeded, CallLedger, GlobalRateLimiter


class BudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_ledger_reserves_before_call_and_counts_all_attempts(self) -> None:
        path = self.root / "ledger.json"
        ledger = CallLedger(path, max_calls_per_case=2)
        first = ledger.reserve("c1", " Query! ")
        ledger.finish(first, "unknown_delivery")
        second = ledger.reserve("c1", "query two")
        ledger.finish(second, "completed")
        self.assertEqual(ledger.count("c1"), 2)
        with self.assertRaises(BudgetExceeded):
            ledger.reserve("c1", "third")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([item["status"] for item in payload["attempts"]], ["unknown_delivery", "completed"])

    def test_ledger_rejects_bad_limit_unknown_attempt_and_corruption(self) -> None:
        for invalid_cap in (0, 3, 999):
            with self.subTest(invalid_cap=invalid_cap), self.assertRaises(ValueError):
                CallLedger(self.root / "x.json", max_calls_per_case=invalid_cap)
        ledger = CallLedger(self.root / "ledger.json")
        with self.assertRaises(ValueError):
            ledger.finish("missing", "completed")
        (self.root / "ledger.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            ledger.count("c1")

    def test_rate_limiter_zero_interval_persists_global_state(self) -> None:
        state = self.root / "rate.json"
        limiter = GlobalRateLimiter(state, min_interval_s=0)
        limiter.wait_turn()
        first = json.loads(state.read_text(encoding="utf-8"))["last_attempt_epoch"]
        limiter.wait_turn()
        second = json.loads(state.read_text(encoding="utf-8"))["last_attempt_epoch"]
        self.assertGreaterEqual(second, first)
        with self.assertRaises(ValueError):
            GlobalRateLimiter(state, min_interval_s=-1)

    def test_rate_limiter_positive_interval_waits(self) -> None:
        limiter = GlobalRateLimiter(self.root / "rate-positive.json", min_interval_s=0.05)
        limiter.wait_turn()
        started = time.monotonic()
        limiter.wait_turn()
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 0.04)


if __name__ == "__main__":
    unittest.main()
