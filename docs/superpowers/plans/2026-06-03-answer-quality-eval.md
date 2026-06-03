# Answer Quality Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small-sample answer-quality A/B/C evaluator comparing closed-book DeepSeek, same-evidence DeepSeek, and product-style RAG answers.

**Architecture:** Add a focused `dnd_rag.answer_eval` module that builds evidence packs, generates three answer variants, judges them across multiple dimensions, and renders a compact Markdown report. Add a CLI command that loads existing retrieval data and embedding index, then runs the evaluator with either DeepSeek or deterministic mock providers for tests.

**Tech Stack:** Python standard library, existing `LLMProvider`, `DeepSeekLLMProvider`, `RagService`, existing JSON eval datasets, Markdown reports under `docs/evaluations/`.

---

### Task 1: Answer Eval Core

**Files:**
- Create: `dnd_rag/answer_eval.py`
- Modify: `tests/test_answer_eval.py`

- [ ] Write tests for evidence-pack creation, three answer variants, score aggregation, and Markdown rendering.
- [ ] Implement prompt builders and JSON judge parsing.
- [ ] Keep provider interactions injectable so tests use fake providers.

### Task 2: CLI Command

**Files:**
- Modify: `scripts/dnd_rag_cli.py`
- Modify: `tests/test_cli.py`

- [ ] Add `answer-eval` CLI with `--questions`, `--embedding-index`, `--limit`, `--out`, and `--mock-llm`.
- [ ] Use DeepSeek by default and mock provider only for tests/local dry runs.
- [ ] Write Markdown report to `docs/evaluations/answer-eval-*.md`.

### Task 3: Real Small-Sample Run

**Files:**
- Create/update: `docs/evaluations/answer-eval-small-sample.md`

- [ ] Run 8-question small sample with full embedding index and DeepSeek.
- [ ] Record aggregate dimension scores, win/tie/loss, memory contamination notes, and per-question review snippets.
- [ ] Run full test suite and sensitive scan before commit.
