from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from dnd_rag.settings import load_env_file
from dnd_rag.providers import DashScopeEmbeddingProvider


class SettingsTests(unittest.TestCase):
    def test_load_env_file_sets_missing_values_without_overriding_existing_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "DASHSCOPE_API_KEY=local-dashscope-key",
                        "DEEPSEEK_API_KEY=local-deepseek-key",
                        "DASHSCOPE_EMBEDDING_DIMENSIONS=1024",
                    ]
                ),
                encoding="utf-8",
            )
            old_dashscope = os.environ.get("DASHSCOPE_API_KEY")
            old_deepseek = os.environ.get("DEEPSEEK_API_KEY")
            old_dims = os.environ.get("DASHSCOPE_EMBEDDING_DIMENSIONS")
            os.environ["DASHSCOPE_API_KEY"] = "existing-key"
            os.environ.pop("DEEPSEEK_API_KEY", None)
            os.environ.pop("DASHSCOPE_EMBEDDING_DIMENSIONS", None)

            try:
                loaded = load_env_file(env_file)

                self.assertEqual(loaded, 2)
                self.assertEqual(os.environ["DASHSCOPE_API_KEY"], "existing-key")
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "local-deepseek-key")
                self.assertEqual(os.environ["DASHSCOPE_EMBEDDING_DIMENSIONS"], "1024")
            finally:
                _restore_env("DASHSCOPE_API_KEY", old_dashscope)
                _restore_env("DEEPSEEK_API_KEY", old_deepseek)
                _restore_env("DASHSCOPE_EMBEDDING_DIMENSIONS", old_dims)

    def test_dashscope_embedding_dimensions_can_be_configured_from_env(self):
        old_key = os.environ.get("DASHSCOPE_API_KEY")
        old_dims = os.environ.get("DASHSCOPE_EMBEDDING_DIMENSIONS")
        old_model = os.environ.get("DASHSCOPE_EMBEDDING_MODEL")
        os.environ["DASHSCOPE_API_KEY"] = "test-key"
        os.environ["DASHSCOPE_EMBEDDING_DIMENSIONS"] = "2048"
        os.environ["DASHSCOPE_EMBEDDING_MODEL"] = "text-embedding-v4"

        try:
            provider = DashScopeEmbeddingProvider()

            self.assertEqual(provider.dimensions, 2048)
            self.assertEqual(provider.model, "text-embedding-v4")
        finally:
            _restore_env("DASHSCOPE_API_KEY", old_key)
            _restore_env("DASHSCOPE_EMBEDDING_DIMENSIONS", old_dims)
            _restore_env("DASHSCOPE_EMBEDDING_MODEL", old_model)


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
