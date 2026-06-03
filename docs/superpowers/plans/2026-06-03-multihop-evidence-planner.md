# Multihop Evidence Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a general multi-hop evidence planner for compound D&D ruling questions so answers require all necessary rule evidence, not just the highest-scoring single chunk.

**Architecture:** Keep `HybridRetriever` as the single-query retrieval engine. Add a small `dnd_rag.planner` module that analyzes a question, creates reusable evidence requirements from entity/category/mechanic signals, runs requirement-level retrieval through the existing retriever, and merges evidence by coverage. `RagService` consumes the merged evidence and exposes requirement coverage for product explanation and evaluation.

**Tech Stack:** Python standard library, existing dataclasses, existing `HybridRetriever`, existing unittest suite, Markdown reports under `docs/evaluations/`.

---

### Task 1: Query Analysis And Requirement Types

**Files:**
- Create: `dnd_rag/planner.py`
- Modify: `tests/test_multihop_planner.py`

- [ ] Write tests showing that compound questions produce multiple requirements by type, not by hard-coded question id.
- [ ] Define `QueryAnalysis`, `EvidenceRequirement`, `RequirementEvidence`, and `MultiHopPlan` dataclasses.
- [ ] Implement rule-based signals for explicit entities, category mentions, and mechanics.

### Task 2: Requirement-Level Retrieval

**Files:**
- Modify: `dnd_rag/planner.py`
- Modify: `tests/test_multihop_planner.py`

- [ ] Write tests for `魔法物品 + 反制法术`, `微妙法术 + 反制法术`, and `盲视 + 隐形` style questions.
- [ ] Run each requirement as its own query against `HybridRetriever`.
- [ ] Mark a requirement covered when top evidence matches its expected title/category/terms.
- [ ] Merge evidence so each covered requirement contributes at least one visible chunk before filling remaining slots by score.

### Task 3: Service Integration

**Files:**
- Modify: `dnd_rag/service.py`
- Modify: `dnd_rag/models.py`
- Modify: `tests/test_audit_and_service.py`

- [ ] Add requirement coverage fields to `AskResponse`.
- [ ] Route `RagService.ask()` through the planner and keep the old single-query path for simple questions.
- [ ] Add answer caveats when required evidence is missing.
- [ ] Keep citations and related entries derived from the merged evidence.

### Task 4: Multi-Hop Evaluation Notes

**Files:**
- Create: `docs/evaluations/multihop-retrieval-optimization.md`
- Modify: `docs/evaluations/retrieval-regression-notes.md`

- [ ] Record the problem, abstraction, implementation, representative cases, and next metrics.
- [ ] Explain `Requirement Coverage@K` and `Complete Case Rate` in Chinese.
- [ ] Keep the report concise enough for product-resume review.

### Task 5: Verification And Commit

**Files:**
- Modify: relevant files from Tasks 1-4.

- [ ] Run targeted planner and service tests.
- [ ] Run full unit test suite.
- [ ] Run `git diff --check`.
- [ ] Run sensitive information scan.
- [ ] Commit and push with a message describing multi-hop evidence planning.
