import unittest

from alqac2026.law.index import LawIndex
from alqac2026.law.retriever import resolve_law_citations, retrieve_law_evidence
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

    def test_direct_citation_is_resolved_before_bm25(self) -> None:
        index = LawIndex([
            LawArticle("91/2015/QH13", 100, "phạm vi điều chỉnh"),
            LawArticle("91/2015/QH13", 101, "nguyên tắc áp dụng"),
            LawArticle("91/2015/QH13", 102, "quyền dân sự"),
            LawArticle("92/2015/QH13", 200, "phạm vi tố tụng"),
        ])
        citations = resolve_law_citations(
            index, "Căn cứ Điều 2 Bộ luật Dân sự năm 2015 để giải quyết."
        )
        self.assertEqual([(item.law_id, item.aid) for item in citations], [
            ("91/2015/QH13", 101)
        ])
        evidence = retrieve_law_evidence(
            index,
            "Căn cứ Điều 2 Bộ luật Dân sự năm 2015; nội dung tố tụng.",
            top_k=2,
        )
        self.assertEqual((evidence[0].law_id, evidence[0].aid), ("91/2015/QH13", 101))
        self.assertEqual(len({(item.law_id, item.aid) for item in evidence}), 2)


if __name__ == "__main__":
    unittest.main()
