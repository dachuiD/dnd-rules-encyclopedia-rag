from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dnd_rag.chunking import build_chunks
from dnd_rag.embedding_index import (
    build_embedding_index,
    EmbeddingIndexRow,
    filter_fresh_rows,
    load_embedding_index,
    text_hash,
    write_embedding_index,
)
from dnd_rag.models import SearchScope
from dnd_rag.normalize import FiveEToolsNormalizer
from dnd_rag.retrieval import HybridRetriever


class EmbeddingIndexPersistenceTests(unittest.TestCase):
    def test_text_hash_is_stable_and_changes_when_text_changes(self):
        self.assertEqual(text_hash("隐形 攻击"), text_hash("隐形 攻击"))
        self.assertNotEqual(text_hash("隐形 攻击"), text_hash("专注 豁免"))

    def test_jsonl_round_trip_preserves_embedding_rows(self):
        rows = [
            EmbeddingIndexRow(
                chunk_id="chunk-a",
                document_id="doc-a",
                embedding_text_hash=text_hash("隐形"),
                model="text-embedding-v4",
                dimensions=3,
                embedding=[0.1, 0.2, 0.3],
            )
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"

            write_embedding_index(path, rows)
            loaded = load_embedding_index(path)

        self.assertEqual(loaded, rows)

    def test_filter_fresh_rows_drops_stale_model_dimension_and_hash(self):
        fresh = EmbeddingIndexRow(
            chunk_id="chunk-a",
            document_id="doc-a",
            embedding_text_hash=text_hash("隐形"),
            model="text-embedding-v4",
            dimensions=1024,
            embedding=[1.0, 0.0],
        )
        stale_model = EmbeddingIndexRow(
            chunk_id="chunk-a",
            document_id="doc-a",
            embedding_text_hash=text_hash("隐形"),
            model="old-model",
            dimensions=1024,
            embedding=[0.0, 1.0],
        )
        stale_hash = EmbeddingIndexRow(
            chunk_id="chunk-b",
            document_id="doc-b",
            embedding_text_hash="stale",
            model="text-embedding-v4",
            dimensions=1024,
            embedding=[0.0, 1.0],
        )

        rows = filter_fresh_rows(
            [fresh, stale_model, stale_hash],
            expected_hash_by_chunk={"chunk-a": text_hash("隐形"), "chunk-b": text_hash("火球术")},
            model="text-embedding-v4",
            dimensions=1024,
        )

        self.assertEqual(rows, {"chunk-a": fresh})


class FakeEmbeddingProvider:
    def __init__(self, embeddings: dict[str, list[float]], max_batch_size: int | None = None) -> None:
        self.embeddings = embeddings
        self.max_batch_size = max_batch_size
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.max_batch_size is not None and len(texts) > self.max_batch_size:
            raise ValueError("batch too large")
        self.calls.append(texts)
        return [self.embeddings[text] for text in texts]


class EmbeddingAwareRetrievalTests(unittest.TestCase):
    def test_retriever_uses_embedding_cosine_for_dense_score_when_vectors_are_available(self):
        normalizer = FiveEToolsNormalizer()
        invisible_doc = normalizer.normalize_entry(
            {
                "name": "隐形",
                "ENG_name": "Invisible",
                "source": "PHB",
                "page": 291,
                "entries": ["隐形生物进行攻击检定时具有优势。"],
            },
            "conditionsdiseases",
        )
        fireball_doc = normalizer.normalize_entry(
            {
                "name": "火球术",
                "ENG_name": "Fireball",
                "source": "PHB",
                "page": 241,
                "entries": ["目标进行敏捷豁免，失败受到火焰伤害。"],
            },
            "spells",
        )
        chunks = [build_chunks(invisible_doc)[0], build_chunks(fireball_doc)[0]]
        chunk_embeddings = {
            chunks[0].id: [1.0, 0.0, 0.0],
            chunks[1].id: [0.0, 1.0, 0.0],
        }
        provider = FakeEmbeddingProvider({"一个看不见的角色攻击": [1.0, 0.0, 0.0]})
        retriever = HybridRetriever(chunks, chunk_embeddings=chunk_embeddings, embedding_provider=provider)

        results = retriever.search("一个看不见的角色攻击", scope=SearchScope.CORE, top_k=2)

        self.assertEqual(results[0].chunk.document_id, invisible_doc.id)
        self.assertEqual(results[0].score.dense_score, 1.0)
        self.assertGreater(results[0].score.dense_score, results[1].score.dense_score)


class EmbeddingIndexBuildTests(unittest.TestCase):
    def test_build_embedding_index_batches_missing_chunks_and_reuses_fresh_cache(self):
        normalizer = FiveEToolsNormalizer()
        docs = [
            normalizer.normalize_entry(
                {
                    "name": "隐形",
                    "ENG_name": "Invisible",
                    "source": "PHB",
                    "page": 291,
                    "entries": ["隐形生物进行攻击检定时具有优势。"],
                },
                "conditionsdiseases",
            ),
            normalizer.normalize_entry(
                {
                    "name": "火球术",
                    "ENG_name": "Fireball",
                    "source": "PHB",
                    "page": 241,
                    "entries": ["目标进行敏捷豁免，失败受到火焰伤害。"],
                },
                "spells",
            ),
        ]
        chunks = [build_chunks(doc)[0] for doc in docs]
        cached = EmbeddingIndexRow(
            chunk_id=chunks[0].id,
            document_id=chunks[0].document_id,
            embedding_text_hash=text_hash(chunks[0].embedding_text),
            model="text-embedding-v4",
            dimensions=3,
            embedding=[1.0, 0.0, 0.0],
        )
        provider = FakeEmbeddingProvider({chunks[1].embedding_text: [0.0, 1.0, 0.0]})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.jsonl"
            write_embedding_index(path, [cached])

            report = build_embedding_index(
                chunks,
                provider=provider,
                out_path=path,
                limit=2,
                batch_size=1,
                model="text-embedding-v4",
                dimensions=3,
            )
            rows = load_embedding_index(path)

        self.assertEqual(report.embedded_rows, 1)
        self.assertEqual(report.cache_hits, 1)
        self.assertEqual(report.total_rows, 2)
        self.assertEqual(provider.calls, [[chunks[1].embedding_text]])
        self.assertEqual({row.chunk_id for row in rows}, {chunk.id for chunk in chunks})

    def test_build_embedding_index_default_batch_size_stays_dashscope_safe(self):
        normalizer = FiveEToolsNormalizer()
        chunks = []
        embeddings = {}
        for index in range(11):
            doc = normalizer.normalize_entry(
                {
                    "name": f"测试条目{index}",
                    "ENG_name": f"Test {index}",
                    "source": "PHB",
                    "page": index + 1,
                    "entries": [f"第{index}条测试规则。"],
                },
                "variantrules",
            )
            chunk = build_chunks(doc)[0]
            chunks.append(chunk)
            embeddings[chunk.embedding_text] = [float(index), 1.0]
        provider = FakeEmbeddingProvider(embeddings, max_batch_size=10)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.jsonl"

            report = build_embedding_index(
                chunks,
                provider=provider,
                out_path=path,
                limit=11,
                model="text-embedding-v4",
                dimensions=2,
            )

        self.assertEqual(report.embedded_rows, 11)
        self.assertEqual([len(call) for call in provider.calls], [10, 1])


if __name__ == "__main__":
    unittest.main()
