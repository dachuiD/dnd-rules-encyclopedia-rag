# RAG vs General LLM Evaluation Protocol

Goal: show whether this product answers D&D rules questions better than a general-purpose LLM without retrieval.

The comparison should not be “which answer sounds nicer”. A good rules product must be correct, grounded, traceable, and appropriately cautious.

## Systems To Compare

| System | Description |
| --- | --- |
| General LLM | Same generation model, no retrieval evidence, asked to answer from its own knowledge. |
| RAG Answer | Same generation model, with evidence pack from our retrieval pipeline. |
| RAG With Citations | Same as RAG Answer, but evaluation also checks displayed citations and source support. |

Use the same model family when possible. Otherwise the benchmark mixes “model quality” and “retrieval product quality”.

## Question Sets

Use three groups:

1. Core rules: PHB/DMG/MM questions.
2. Full rules: expansions, feats, spells, monsters, items, races, optional features.
3. Community-real questions: paraphrased from real forum/StackExchange questions with source URLs.

The community-real group should be the main product benchmark because it contains ambiguity, colloquial phrasing, mixed terminology, and edge cases.

## Metrics

| Metric | What It Measures | Why It Matters |
| --- | --- | --- |
| Answer Correctness | Whether the final ruling is right. | Main user value. |
| Evidence Support | Whether each key claim is supported by retrieved evidence. | Prevents confident hallucination. |
| Citation Accuracy | Whether citations actually support the cited sentence. | Product trust and interview demo value. |
| Completeness | Whether the answer includes important conditions/exceptions. | Rules answers often fail by omission. |
| Abstention | Whether the system says “evidence insufficient” when needed. | Better than fabricated certainty. |
| DM-Caution | Whether table-ruling parts are separated from written rules. | Critical for D&D rules culture. |
| User Preference | Blind A/B human preference. | Captures readability and usefulness. |

## Suggested Scoring Rubric

Each answer receives 0-2 points per dimension:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Correctness | Wrong or misleading | Partly correct | Correct ruling |
| Grounding | Unsupported claims | Some support | Key claims supported |
| Citation | Missing/wrong | Partly relevant | Directly supports answer |
| Completeness | Misses core caveat | Minor omissions | Covers conditions/exceptions |
| Clarity | Hard to act on | Understandable | Direct and actionable |

Maximum: 10 points.

For interview-friendly reporting, also show win/tie/loss:

- RAG wins if it scores at least 2 points higher than General LLM.
- Tie if score difference is -1, 0, or +1.
- General LLM wins if it scores at least 2 points higher.

## Blind Review Flow

1. Select a question from the eval set.
2. Generate Answer A from General LLM without retrieval.
3. Generate Answer B from RAG with evidence.
4. Hide system identity and randomize order.
5. Reviewer scores both with the rubric.
6. Separately verify whether cited evidence supports claims.
7. Record win/tie/loss and failure reason.

Keep the original community source URL, but paraphrase the question in the dataset. Do not copy long community answers into the repo.

## LLM-as-Judge Use

LLM-as-judge can speed up triage, but should not be the final authority for rules correctness.

Use it for:

- first-pass scoring;
- finding unsupported claims;
- classifying failure reasons;
- summarizing disagreements.

Human review is required for:

- final correctness labels;
- edge-case rulings;
- citation support decisions;
- benchmark numbers used in portfolio claims.

## Report Shape

The useful report is compact:

- headline win/tie/loss;
- average rubric score by system;
- top failure categories;
- 5 good examples where RAG wins;
- 5 bad examples where RAG loses;
- next tuning actions.

Avoid long evidence dumps in the review report. Keep detailed evidence reports as debug artifacts only.

## Product Claim Template

Use careful claims:

> On a curated set of community-real D&D 5e rules questions, the RAG system improved evidence-grounded answer quality over the same model without retrieval, especially on expansion content and citation traceability.

Avoid overclaiming:

> This system is always more accurate than general LLMs.

That claim would require a larger benchmark, multiple model baselines, and independent human review.
