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


if __name__ == "__main__":
    unittest.main()
