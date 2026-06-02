# D&D 规则百科全书 RAG

一个中文 D&D 规则百科 RAG Demo：问答为主，百科条目页辅助。项目重点不是“接一个大模型”，而是把复杂规则资料做成可规范化、可检索、可引用、可评测的知识产品。

## 核心卖点

- 数据规范化：将 5e.tools 中文结构化数据转成统一 `RuleDocument`、`RuleChunk`、`Citation`。
- 自适应 chunk：规则章节、状态、法术等关键类别采用父子双层 chunk。
- 可解释检索：向量、关键词、标题/别名、父子扩展，多路召回后透明加权。
- 双模式体验：核心规则偏规则裁判，全量偏百科探索。
- 评测闭环：支持 golden set、Recall@K、MRR、消融实验。

## 当前实现状态

已实现：

- 样例 5e.tools 中文数据加载。
- 数据体检报告。
- 5e.tools 标记清洗与关系抽取。
- 规则文档规范化。
- 自适应 + 关键双层 chunk。
- 本地透明 hybrid retrieval。
- 问答 API 与前端。
- 检索解释面板。
- 评测脚本。
- Postgres + pgvector schema。

保留为生产替换点：

- `DeepSeekLLMProvider`
- `DashScopeEmbeddingProvider`
- Postgres/pgvector 持久化写入

默认本地 demo 使用样例数据和确定性本地逻辑，方便没有 API Key 时演示。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m unittest discover -s tests -v
uvicorn app:app --reload --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

如果要接授权全量数据：

```bash
FIVEETOOLS_DATA_DIR=/path/to/fvtt-cn/5etools/data
uvicorn app:app --reload --port 8000
```

## CLI

生成数据体检报告：

```bash
python3 scripts/dnd_rag_cli.py audit --data-dir sample_data/5etools --out reports/data-audit.md
```

本地问答：

```bash
python3 scripts/dnd_rag_cli.py ask "隐身的人攻击有优势吗？" --scope core
```

运行检索评测：

```bash
python3 scripts/dnd_rag_cli.py eval --questions eval/golden_sample.json --out reports/retrieval-eval.json
```

构建百炼真实 embedding 小样本索引：

```bash
python3 scripts/dnd_rag_cli.py embed-sample \
  --scope core \
  --limit 300 \
  --batch-size 20 \
  --out storage/embedding-index/sample.jsonl
```

`--limit 0` 表示不限制数量，可用于构建完整核心规则索引：

```bash
python3 scripts/dnd_rag_cli.py embed-sample \
  --data-dir data/fvtt-cn-5etools/data \
  --scope core \
  --limit 0 \
  --batch-size 20 \
  --max-segment-chars 4000 \
  --out storage/embedding-index/core.jsonl
```

构建 V1 全量索引：

```bash
python3 scripts/dnd_rag_cli.py embed-sample \
  --data-dir data/fvtt-cn-5etools/data \
  --scope full \
  --limit 0 \
  --batch-size 20 \
  --max-segment-chars 4000 \
  --out storage/embedding-index/full.jsonl
```

用真实 embedding 索引跑同一套检索评测：

```bash
python3 scripts/dnd_rag_cli.py eval \
  --questions eval/golden_sample.json \
  --embedding-index storage/embedding-index/sample.jsonl \
  --out reports/retrieval-eval-embedding.json
```

生成可归档的 Markdown 评测报告：

```bash
python3 scripts/dnd_rag_cli.py eval-report \
  --data-dir data/fvtt-cn-5etools/data \
  --questions eval/golden_v1.json \
  --embedding-index storage/embedding-index/core.jsonl \
  --out docs/evaluations/retrieval-eval-v1-core-embedding.md
```

全量索引评测归档：

```bash
python3 scripts/dnd_rag_cli.py eval-report \
  --data-dir data/fvtt-cn-5etools/data \
  --questions eval/golden_v1.json \
  --embedding-index storage/embedding-index/full.jsonl \
  --out docs/evaluations/retrieval-eval-v1-full-embedding.md
```

生成更适合人工审阅的摘要评测报告：

```bash
python3 scripts/dnd_rag_cli.py eval-summary \
  --data-dir data/fvtt-cn-5etools/data \
  --questions eval/golden_full_seed.json \
  --embedding-index storage/embedding-index/full.jsonl \
  --out docs/evaluations/retrieval-eval-full-seed-summary.md
```

生成 Token Hybrid vs Embedding Hybrid 的摘要对比报告：

```bash
python3 scripts/dnd_rag_cli.py eval-summary \
  --data-dir data/fvtt-cn-5etools/data \
  --questions eval/golden_full_seed.json \
  --embedding-index storage/embedding-index/full.jsonl \
  --compare-baseline \
  --out docs/evaluations/retrieval-eval-full-seed-comparison.md
```

`storage/` 默认不进入 Git。这里面会保存模型输出向量，也可能间接暴露授权数据的语义内容，只适合本地调试和评测。

`reports/` 默认不进入 Git，用于保存本地原始运行结果；`docs/evaluations/` 用于保存筛选后的可读评测归档，包含题目、参考答案、来源证据、分数解释和对比结论。

## 数据边界

V1 的两个检索范围：

- 核心规则：PHB、DMG、MM。
- 全量：核心规则 + 扩展规则/百科实体。

V1 排除：

- 冒险正文。
- Roll20 模块资产。
- 明显工具型/生成型数据。

这个取舍是为了避免“更多数据导致更差回答”，让规则百科问答保持可解释和低噪声。

## API Key

本项目启动时会读取仓库根目录的 `.env`。真实密钥只放 `.env` 或系统环境变量，不写入代码、README、测试、提交记录。

生成模型：

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-v4-flash
```

Embedding：

```bash
DASHSCOPE_API_KEY=...
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSIONS=1024
```

当前 Web Demo 默认不强制调用外部模型；生产接入时可把 `DeepSeekLLMProvider` 和 `DashScopeEmbeddingProvider` 接入索引构建与回答生成链路。

建议先用 `DASHSCOPE_EMBEDDING_DIMENSIONS=1024` 建 200-500 个 chunk 的小样本索引，跑检索评测后再对比 2048 维度。这样简历里可以讲清楚“性能、成本、召回质量”的取舍，而不是盲目上最大配置。

## Embedding 小样本闭环

当前已经支持一个轻量但真实的 embedding 闭环：

```text
Adapter -> Normalize -> Chunk -> DashScope text-embedding-v4 -> JSONL Index -> Hybrid Retrieval -> Eval
```

本地索引每行保存 `chunk_id`、`document_id`、模型名、维度、`embedding_text` 的 hash 和向量。检索时会重新从数据源构建 chunk，并用 hash 判断缓存是否仍然可用；如果文本、模型或维度变了，旧向量不会被静默复用。

超长 chunk 不会被跳过或截断。索引构建会按 `--max-segment-chars` 二次切分，分别 embedding 后做向量平均，最终仍保存为原 chunk 的一条索引记录。批量请求默认从 `20` 开始，如果供应商接口拒绝大批量，会自动二分降级为更小批次。

这个设计暂时不替代 pgvector，而是作为验证层：先用核心规则索引对比 baseline 与真实 embedding，再决定是否全量建索引和迁移到 Postgres。

## Git 与安全

- `.env`、真实 `data/`、索引缓存和本地数据库文件不会进入 Git。
- 如果 API Key、GitHub 密码或授权数据曾经出现在聊天、日志或提交历史里，应立即在对应平台重置。
- GitHub 推送建议使用 SSH key 或 fine-grained personal access token，不使用账号密码。

## 数据库

启动 Postgres + pgvector：

```bash
docker compose up -d postgres
```

schema 位于：

```text
db/schema.sql
```

第一版代码先用内存索引跑通产品闭环；Postgres schema 已按最终表结构准备好，后续可加入 repository 层持久化。
