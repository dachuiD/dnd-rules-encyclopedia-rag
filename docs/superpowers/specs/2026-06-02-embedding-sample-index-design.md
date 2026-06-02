# Embedding Sample Index Design

## Goal

Build a small, real embedding index loop for the D&D rules RAG: normalize data, build chunks, call DashScope `text-embedding-v4`, persist a local JSONL index, and use those vectors for transparent dense retrieval.

## Scope

V1 covers a 200-500 chunk sample and keeps Postgres/pgvector as the next migration target. The local index is a reproducible artifact for debugging, evaluation, and portfolio demonstration. It is ignored by Git because it may contain licensed source-derived text and paid API outputs.

## Index Format

Each JSONL row stores:

- `chunk_id`
- `document_id`
- `embedding_text_hash`
- `model`
- `dimensions`
- `embedding`

The row does not need to duplicate full chunk text because chunks are rebuilt from the source adapter during retrieval. Cache hits are keyed by chunk id, model, dimensions, and text hash.

## Retrieval Design

The existing `HybridRetriever` remains the central ranking component. A new embedding-aware path injects query and chunk vector cosine similarity as the `dense_score`, while lexical, alias, title, source, structure, parent-child expansion, and reasons stay explainable.

## CLI Experience

`python3 scripts/dnd_rag_cli.py embed-sample --limit 300 --out storage/embedding-index/sample.jsonl`

The command prints document count, chunk count, embedded row count, model, dimensions, cache hit count, and output path. It reads `.env` for local API keys.

## Evaluation

The existing retrieval eval command should accept an optional `--embedding-index` path. This lets the same golden set compare local transparent retrieval against real embedding retrieval without changing frontend behavior.

## Risks

Embedding calls cost money and may hit rate limits, so the CLI should default to a small sample and batch requests. The local index must stay out of Git. If the source data changes, text hashes invalidate stale rows instead of silently reusing the wrong vector.
