import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import build_service, create_app
from dnd_rag.adapters import FiveEToolsNormalizer
from dnd_rag.chunking import build_chunks
from dnd_rag.embedding_index import EmbeddingIndexRow, text_hash, write_embedding_index
from dnd_rag.providers import HashEmbeddingProvider
from dnd_rag.service import RagService


class CaptureLLMProvider:
    def __init__(self):
        self.calls = []

    def answer(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return "LLM grounded answer"


class DeploymentTests(unittest.TestCase):
    def test_ci_workflow_runs_deployment_readiness_and_unit_tests(self):
        workflow = Path(".github/workflows/ci.yml")

        self.assertTrue(workflow.exists(), "CI workflow should exist")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("scripts/check_deployment_readiness.sh", text)
        self.assertIn("python3 -m unittest discover -s tests -v", text)
        self.assertIn("git diff --check", text)

    def test_cloudflare_function_smoke_script_exercises_proxy_and_rate_limit(self):
        script = Path("scripts/test_cloudflare_function.mjs")

        self.assertTrue(script.exists(), "Cloudflare Function smoke script should exist")
        result = subprocess.run(["node", str(script)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Cloudflare Function smoke tests passed", result.stdout)

    def test_public_demo_smoke_can_require_full_healthz_counts(self):
        script = Path("scripts/smoke_public_demo.sh").read_text(encoding="utf-8")

        self.assertIn("EXPECT_FULL_DATA", script)
        self.assertIn("EXPECT_PRODUCTION_PROVIDERS", script)
        self.assertIn("MIN_HEALTHZ_DOCUMENTS", script)
        self.assertIn("MIN_HEALTHZ_CHUNKS", script)
        self.assertIn("MIN_HEALTHZ_EMBEDDINGS", script)
        self.assertIn("DashScopeEmbeddingProvider", script)
        self.assertIn("DeepSeekLLMProvider", script)

    def test_default_compose_defines_production_app_service(self):
        compose = Path("docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("  app:", compose)
        self.assertIn("REQUIRE_GATEWAY_TOKEN", compose)
        self.assertIn("true", compose)
        self.assertIn("EMBEDDING_INDEX_PATH", compose)
        self.assertIn("/opt/dnd-rag/storage/embedding-index/full.jsonl", compose)
        self.assertIn("--workers", compose)
        self.assertIn('"1"', compose)

    def test_create_app_requires_gateway_token_when_production_guard_is_enabled(self):
        service = RagService.from_sample_data()

        with _temporary_env(REQUIRE_GATEWAY_TOKEN="true", RAG_GATEWAY_TOKEN=""):
            with self.assertRaises(RuntimeError):
                create_app(service=service)

    def test_build_service_loads_fresh_embedding_index_and_query_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "conditionsdiseases.json").write_text(
                '{"condition":[{"name":"隐形","source":"PHB","page":291,'
                '"entries":["隐形生物的攻击检定具有优势。"]}]}',
                encoding="utf-8",
            )
            doc = FiveEToolsNormalizer().normalize_entry(
                {"name": "隐形", "source": "PHB", "page": 291, "entries": ["隐形生物的攻击检定具有优势。"]},
                "conditions",
            )
            chunk = build_chunks(doc)[0]
            index_path = Path(tmp) / "index.jsonl"
            write_embedding_index(
                index_path,
                [
                    EmbeddingIndexRow(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        embedding_text_hash=text_hash(chunk.embedding_text),
                        model="text-embedding-v4",
                        dimensions=64,
                        embedding=[1.0] + [0.0] * 63,
                    )
                ],
            )

            with _temporary_env(
                FIVEETOOLS_DATA_DIR=str(data_dir),
                EMBEDDING_INDEX_PATH=str(index_path),
                QUERY_EMBEDDING_PROVIDER="hash",
                DASHSCOPE_EMBEDDING_MODEL="text-embedding-v4",
                DASHSCOPE_EMBEDDING_DIMENSIONS="64",
            ):
                service = build_service()

        self.assertEqual(len(service.chunk_embeddings), 1)
        self.assertIsInstance(service.retriever.embedding_provider, HashEmbeddingProvider)

    def test_build_service_requires_dashscope_key_when_dashscope_query_embedding_is_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            (data_dir / "conditionsdiseases.json").write_text('{"condition":[]}', encoding="utf-8")
            index_path = Path(tmp) / "index.jsonl"
            index_path.write_text("", encoding="utf-8")

            with _temporary_env(
                FIVEETOOLS_DATA_DIR=str(data_dir),
                EMBEDDING_INDEX_PATH=str(index_path),
                QUERY_EMBEDDING_PROVIDER="dashscope",
                DASHSCOPE_API_KEY="",
            ):
                with self.assertRaises(RuntimeError):
                    build_service()

    def test_api_requires_gateway_token_but_healthz_does_not(self):
        service = RagService.from_sample_data()
        app = create_app(service=service, gateway_token="secret-token")
        client = TestClient(app)

        health = client.get("/healthz")
        unauthorized = client.post("/api/ask", json={"question": "隐身的人攻击有优势吗？"})
        authorized = client.post(
            "/api/ask",
            json={"question": "隐身的人攻击有优势吗？"},
            headers={"X-RAG-GATEWAY-TOKEN": "secret-token"},
        )

        self.assertEqual(health.status_code, 200)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)

    def test_deepseek_answer_prompt_includes_evidence_requirements_and_missing_constraints(self):
        llm = CaptureLLMProvider()
        service = _service_for_entries(
            [
                (
                    {
                        "name": "准备",
                        "source": "PHB",
                        "page": 193,
                        "entries": ["一个法术必须具有1个动作的施法时间才能被准备，且扣住该法术的魔法需要专注。"],
                    },
                    "actions",
                ),
                (
                    {
                        "name": "施法",
                        "source": "PHB",
                        "page": 192,
                        "entries": ["每个法术都有自己的施法时间。"],
                    },
                    "actions",
                ),
            ],
            llm_provider=llm,
        )

        response = service.ask("如果我这回合已经用附赠动作施法，还能用动作准备另一个法术吗？", scope="core")

        self.assertEqual(response.answer, "LLM grounded answer")
        self.assertEqual(len(llm.calls), 1)
        system_prompt, user_prompt = llm.calls[0]
        self.assertIn("只能基于 evidence pack 回答", system_prompt)
        self.assertIn("missing 的 required requirement", system_prompt)
        self.assertIn("Evidence Requirements", user_prompt)
        self.assertIn("bonus_action_spell_limit", user_prompt)
        self.assertIn("status=missing", user_prompt)


def _service_for_entries(entries, llm_provider=None):
    normalizer = FiveEToolsNormalizer()
    docs = [normalizer.normalize_entry(entry, category) for entry, category in entries]
    chunks = [chunk for doc in docs for chunk in build_chunks(doc)]
    return RagService(docs, chunks, llm_provider=llm_provider)


class _temporary_env:
    def __init__(self, **values):
        self.values = values
        self.previous = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, exc_type, exc, tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
