import unittest

from alqac2026.reasoning.evidence_selector import (
    rank_chunks_for_evidence,
    select_case_evidence,
)
from alqac2026.schemas import RetrievedChunk


class EvidenceSelectorTests(unittest.TestCase):
    def test_court_decision_outranks_high_score_party_description(self) -> None:
        chunks = [
            RetrievedChunk(99.0, "Nguyên đơn trình bày và yêu cầu trả nợ.", "party"),
            RetrievedChunk(3.0, "QUYẾT ĐỊNH: Chấp nhận một phần yêu cầu khởi kiện.", "decision"),
        ]
        ranked = rank_chunks_for_evidence(chunks)
        self.assertEqual([chunk.chunk_id for chunk in ranked], ["decision", "party"])
        self.assertEqual(select_case_evidence(chunks, max_items=1), ("decision",))


if __name__ == "__main__":
    unittest.main()
