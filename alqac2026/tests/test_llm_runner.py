import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alqac2026.reasoning.llm_runner import (
    ClaudeCliRunner,
    CodexCliRunner,
    DeterministicRunner,
    backend_is_submission_eligible,
)
from alqac2026.schemas import PrivateCase


PREDICTION = {
    "prediction": "A_WIN",
    "confidence": 0.75,
    "rationale": "mocked structured result",
}


class LlmRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_deterministic_runner_metadata_is_submission_eligible(self) -> None:
        runner = DeterministicRunner()
        self.assertEqual(runner.metadata.backend_id, "deterministic_v1")
        self.assertTrue(runner.metadata.eligible_for_submission)
        self.assertTrue(backend_is_submission_eligible(runner.metadata.backend_id))
        result = runner.predict(PrivateCase("c1", "hop dong vay tra no"), [])
        self.assertEqual(result.prediction, "A_WIN")

    def test_codex_runner_parses_last_message_and_marks_proprietary(self) -> None:
        prompt = "private case prompt"
        schema = self.root / "schema.json"
        schema.write_text("{}", encoding="utf-8")

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            output_index = args.index("--output-last-message") + 1
            Path(args[output_index]).write_text(json.dumps(PREDICTION), encoding="utf-8")
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["input"], prompt)
            return subprocess.CompletedProcess(args, 0, stdout="ignored", stderr="")

        runner = CodexCliRunner(model_id="codex-test", version="1.2.3")
        with patch("alqac2026.reasoning.llm_runner.subprocess.run", side_effect=fake_run) as mocked:
            result = runner.run(
                prompt,
                schema_path=schema,
                isolated_cwd=self.root / "isolated-codex",
            )

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(result.prediction.prediction, "A_WIN")
        self.assertEqual(result.raw_envelope, PREDICTION)
        self.assertEqual(result.metadata.backend_id, "codex_cli")
        self.assertEqual(result.metadata.model_id, "codex-test")
        self.assertFalse(result.metadata.eligible_for_submission)
        self.assertFalse(backend_is_submission_eligible(result.backend_id))
        self.assertEqual(result.metadata.prompt_hash, hashlib.sha256(prompt.encode()).hexdigest())

    def test_claude_runner_parses_envelope_and_marks_proprietary(self) -> None:
        prompt = "private case prompt"
        envelope = {"structured_output": PREDICTION, "session_id": "mock-session"}
        completed = subprocess.CompletedProcess(
            ["claude"], 0, stdout=json.dumps(envelope), stderr=""
        )
        runner = ClaudeCliRunner(model_id="claude-test", version="4.5")

        with patch(
            "alqac2026.reasoning.llm_runner.subprocess.run", return_value=completed
        ) as mocked:
            result = runner.run(
                prompt,
                json_schema={"type": "object"},
                isolated_cwd=self.root / "isolated-claude",
            )

        args = mocked.call_args.args[0]
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", args)
        self.assertFalse(mocked.call_args.kwargs["shell"])
        self.assertEqual(result.raw_envelope, envelope)
        self.assertEqual(result.prediction.prediction, "A_WIN")
        self.assertEqual(result.metadata.backend_id, "claude_cli")
        self.assertFalse(result.metadata.eligible_for_submission)
        self.assertFalse(backend_is_submission_eligible(result.backend_id))
        self.assertEqual(result.metadata.prompt_hash, hashlib.sha256(prompt.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
