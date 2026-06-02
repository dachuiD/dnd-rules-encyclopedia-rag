import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_eval_report_command_writes_markdown_audit_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "eval-report.md"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/dnd_rag_cli.py",
                    "eval-report",
                    "--data-dir",
                    "sample_data/5etools",
                    "--questions",
                    "eval/golden_sample.json",
                    "--out",
                    str(out),
                    "--evidence-limit",
                    "1",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = out.read_text(encoding="utf-8")
            self.assertIn("Retrieval Eval", markdown)
            self.assertIn("Recall@8", markdown)
            self.assertIn("core-invisible-attack", markdown)
            self.assertIn("Top 证据", markdown)

    def test_eval_summary_command_writes_compact_review_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "eval-summary.md"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/dnd_rag_cli.py",
                    "eval-summary",
                    "--data-dir",
                    "sample_data/5etools",
                    "--questions",
                    "eval/golden_sample.json",
                    "--out",
                    str(out),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = out.read_text(encoding="utf-8")
            self.assertIn("Retrieval Eval Summary", markdown)
            self.assertIn("Review Table", markdown)
            self.assertIn("Top1", markdown)
            self.assertNotIn("Top 证据", markdown)

    def test_eval_summary_command_can_compare_against_token_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "eval-summary-compare.md"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/dnd_rag_cli.py",
                    "eval-summary",
                    "--data-dir",
                    "sample_data/5etools",
                    "--questions",
                    "eval/golden_sample.json",
                    "--out",
                    str(out),
                    "--compare-baseline",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = out.read_text(encoding="utf-8")
            self.assertIn("Token Hybrid", markdown)
            self.assertIn("Embedding Hybrid", markdown)
            self.assertIn("Delta", markdown)
            self.assertIn("Changed Questions", markdown)


if __name__ == "__main__":
    unittest.main()
