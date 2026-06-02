# Evaluation Archives

This directory stores human-readable evaluation artifacts that are safe and useful to commit.

Use it for:

- Golden-set summaries with concrete questions and reference answers.
- Retrieval evidence tables with citation labels, chunk metadata, score parts, and match reasons.
- Baseline versus embedding comparisons that show improvements, regressions, and misses.

Do not use it for:

- Raw embedding vectors.
- Full local data dumps.
- API keys, `.env` files, or provider responses that may expose credentials.

The raw JSON outputs under `reports/` are local debugging artifacts and are ignored by Git. Commit only curated Markdown reports that help explain the system behavior.
