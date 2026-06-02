# Embedding Sample Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real DashScope embedding sample index that can be built, cached, loaded, and used by retrieval eval.

**Architecture:** Create a focused `dnd_rag.embedding_index` module for JSONL persistence, cache keys, cosine scoring, and sample index building. Extend `HybridRetriever` with optional embedding vectors so dense scoring can switch from token overlap to vector cosine without changing the rest of the ranking pipeline. Extend CLI with `embed-sample` and `eval --embedding-index`.

**Tech Stack:** Python standard library, existing provider abstractions, `unittest`, JSONL files ignored by Git.

---

### Task 1: Local Embedding Index Persistence

**Files:**
- Create: `dnd_rag/embedding_index.py`
- Test: `tests/test_embedding_index.py`

- [ ] Write failing tests for text hash stability, JSONL round-trip, and stale row filtering by model/dimensions/hash.
- [ ] Run `python -m unittest tests/test_embedding_index.py -v` and confirm import/function failures.
- [ ] Implement `EmbeddingIndexRow`, `text_hash`, `write_embedding_index`, `load_embedding_index`, and `filter_fresh_rows`.
- [ ] Run the focused test and confirm it passes.

### Task 2: Embedding-Aware Retriever

**Files:**
- Modify: `dnd_rag/retrieval.py`
- Test: `tests/test_embedding_index.py`

- [ ] Write a failing test that passes chunk vectors and a query embedding provider, then asserts dense score ranks the semantically matching chunk first.
- [ ] Run the focused test and confirm it fails because `HybridRetriever` has no embedding-aware path.
- [ ] Add optional `chunk_embeddings` and `embedding_provider` constructor arguments and compute dense cosine when available.
- [ ] Run the focused test and existing retrieval tests.

### Task 3: Sample Index Builder and CLI

**Files:**
- Modify: `dnd_rag/embedding_index.py`
- Modify: `scripts/dnd_rag_cli.py`
- Test: `tests/test_embedding_index.py`

- [ ] Write failing tests for batched sample index building with cache reuse.
- [ ] Implement `build_embedding_index` with limit, batch size, cache hit counting, and provider injection.
- [ ] Add `embed-sample` CLI command.
- [ ] Extend `eval` with `--embedding-index` for vector-backed retrieval eval.
- [ ] Run unit tests, compile check, one local hash-provider `embed-sample` smoke test, and one real DashScope small smoke test if keys are present.

### Task 4: Documentation and Commit

**Files:**
- Modify: `README.md`

- [ ] Document `embed-sample`, `eval --embedding-index`, and why `storage/` is ignored.
- [ ] Run final verification.
- [ ] Commit and push the feature branch.
