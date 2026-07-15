import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alqac2026.cli import command_validate_submission
from alqac2026.retrieval.cache import JsonRetrievalCache
from alqac2026.schemas import CasePrediction, LawArticle, LawEvidence, RunManifest
from alqac2026.submission.builder import (
    build_submission,
    file_sha256,
    write_official_artifacts,
)
from alqac2026.submission.validator import validate_submission


class SubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.cache = JsonRetrievalCache(Path(self.temp.name) / "cache")
        self.cache.store("c1", "q", {"results": [
            {"score": 1.0, "text": "evidence one", "chunk_id": "chunk-c1"}
        ]})
        self.cache.store("c2", "q", {"results": [
            {"score": 1.0, "text": "evidence two", "chunk_id": "chunk-c2"}
        ]})
        self.laws = [LawArticle("LAW", 1, "article")]
        self.expected = {"c1", "c2"}
        self.manifest = RunManifest("run-1", "deterministic_v0")
        self.rows = [
            {"case_id": "c1", "prediction": "A_WIN", "case_evidence": ["chunk-c1"], "law_evidence": [{"law_id": "LAW", "aid": 1}]},
            {"case_id": "c2", "prediction": "B_WIN", "case_evidence": ["chunk-c2"], "law_evidence": []},
        ]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _validate(self, rows: object, backend: str = "deterministic_v0"):
        return validate_submission(
            rows,
            expected_case_ids=self.expected,
            law_corpus=self.laws,
            cache=self.cache,
            manifest=RunManifest("run", backend),
        )

    def test_valid_fixture_and_official_builder(self) -> None:
        report = self._validate(self.rows)
        self.assertTrue(report.valid, report.errors)
        predictions = [
            CasePrediction("c1", "A_WIN", ("chunk-c1",), (LawEvidence("LAW", 1),)),
            CasePrediction("c2", "B_WIN", ("chunk-c2",), ()),
        ]
        self.assertEqual(build_submission(
            predictions,
            expected_case_ids=self.expected,
            law_corpus=self.laws,
            cache=self.cache,
            manifest=self.manifest,
        ), self.rows)

    def test_proprietary_and_unknown_backends_are_blocked(self) -> None:
        for backend in ("codex_cli", "claude_cli", "made_up"):
            with self.subTest(backend=backend):
                report = self._validate(self.rows, backend)
                self.assertFalse(report.valid)
                self.assertTrue(any("not eligible" in error for error in report.errors))

    def test_evidence_must_exist_in_raw_cache_for_same_case(self) -> None:
        wrong_case = [dict(row) for row in self.rows]
        wrong_case[0]["case_evidence"] = ["chunk-c2"]
        report = self._validate(wrong_case)
        self.assertFalse(report.valid)
        self.assertTrue(any("absent from its raw cache" in error for error in report.errors))

    def test_invalid_shape_ids_labels_and_law_pairs_are_rejected(self) -> None:
        fixtures = [
            {"not": "array"},
            [self.rows[0]],
            [self.rows[0], self.rows[0]],
            [dict(self.rows[0], extra=True), self.rows[1]],
            [dict(self.rows[0], prediction="INVALID"), self.rows[1]],
            [dict(self.rows[0], case_evidence=["chunk-c1", "chunk-c1"]), self.rows[1]],
            [dict(self.rows[0], law_evidence=[{"law_id": "UNKNOWN", "aid": 99}]), self.rows[1]],
        ]
        for rows in fixtures:
            with self.subTest(rows=rows):
                self.assertFalse(self._validate(rows).valid)

    def test_official_artifact_hash_and_cli_provenance_are_enforced(self) -> None:
        project = Path(self.temp.name) / "project"
        public_dir = project / "data" / "public"
        public_dir.mkdir(parents=True)
        (public_dir / "ALQAC2026_public_test.json").write_text(
            json.dumps([
                {"case_id": "c1", "case_query": "query one"},
                {"case_id": "c2", "case_query": "query two"},
            ]),
            encoding="utf-8",
        )
        (public_dir / "corpus_law_pub.json").write_text(
            json.dumps([{"law_id": "LAW", "content": [
                {"aid": 1, "content_Article": "article"}
            ]}]),
            encoding="utf-8",
        )
        cli_cache = JsonRetrievalCache(project / "data" / "retrieval-cache")
        cli_cache.store("c1", "q", {"results": [
            {"score": 1.0, "text": "evidence one", "chunk_id": "chunk-c1"}
        ]})
        cli_cache.store("c2", "q", {"results": [
            {"score": 1.0, "text": "evidence two", "chunk_id": "chunk-c2"}
        ]})
        submission = project / "submissions" / "submission.json"
        output, manifest_path, artifact = write_official_artifacts(
            submission, self.rows, self.manifest
        )

        self.assertEqual(output, submission)
        self.assertTrue(manifest_path.exists())
        self.assertEqual(artifact["artifact"]["submission_sha256"], file_sha256(submission))
        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8")), artifact
        )
        args = argparse.Namespace(
            project_root=str(project), input=str(submission), manifest=None
        )
        with patch("builtins.print"):
            self.assertEqual(command_validate_submission(args), 0)

        submission.write_text(submission.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            command_validate_submission(args)


if __name__ == "__main__":
    unittest.main()
