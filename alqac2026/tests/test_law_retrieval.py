import unittest

from alqac2026.law.index import LawIndex
from alqac2026.law.retriever import retrieve_law_evidence
from alqac2026.schemas import LawArticle


class LawRetrievalTests(unittest.TestCase):
    def test_bm25_ranks_relevant_article_and_is_deterministic(self) -> None:
        index = LawIndex([
            LawArticle("CIVIL", 2, "hop dong vay tai san tra no ngan hang"),
            LawArticle("CIVIL", 1, "quyen so huu tai san dat dai"),
            LawArticle("PROC", 3, "thu tuc xet xu phuc tham"),
        ])
        hits = index.search("hop dong vay tra no", top_k=2)
        self.assertEqual((hits[0].article.law_id, hits[0].article.aid), ("CIVIL", 2))
        self.assertGreater(hits[0].score, 0)
        self.assertEqual(index.search("zzzz qqqq"), [])
        evidence = retrieve_law_evidence(index, "hop dong vay", top_k=2)
        self.assertEqual(evidence[0].aid, 2)
        self.assertEqual(len({(item.law_id, item.aid) for item in evidence}), len(evidence))

    def test_bm25_rejects_empty_index_and_nonpositive_top_k(self) -> None:
        with self.assertRaises(ValueError):
            LawIndex([])
        index = LawIndex([LawArticle("LAW", 1, "alpha beta")])
        for top_k in (0, -1):
            with self.subTest(top_k=top_k), self.assertRaises(ValueError):
                index.search("alpha", top_k=top_k)


if __name__ == "__main__":
    unittest.main()
