# 公开 Demo 部署手册：Cloudflare Pages + 阿里云 ECS

## 目标架构

```text
Browser
-> Cloudflare Pages static frontend
-> Cloudflare Pages Function /api/*
-> Aliyun ECS FastAPI :8000
-> local full data + storage/embedding-index/full.jsonl
-> DashScope query embedding + DeepSeek answer generation
```

首版使用 Cloudflare 默认 `pages.dev` 域名，不配置自定义域名。

## 部署前检查

先在本地跑仓库级 readiness：

```bash
scripts/check_deployment_readiness.sh
```

真正准备上传全量数据和全量索引前，开启严格资产检查：

```bash
STRICT_ASSETS=1 scripts/check_deployment_readiness.sh
```

严格检查会确认：

- 授权数据目录存在。
- `storage/embedding-index/full.jsonl` 存在。
- 全量索引行数不少于默认阈值 `25000`。
- 部署脚本、Cloudflare Function、静态前端、Docker/Compose 配置都存在。
- 仓库内没有明显真实 key 形态的敏感值。

GitHub Actions 会自动运行仓库级 readiness、Cloudflare Function smoke、单元测试和空白检查。严格资产检查不在 CI 中运行，因为授权数据和 embedding index 不提交 Git。

## ECS 规格

推荐起步规格：

- 2 vCPU
- 8GB RAM
- 40GB SSD
- Ubuntu 22.04 LTS
- Docker + Docker Compose plugin

本地全量加载实测峰值 RSS 约 4.4GB。FastAPI 只跑 1 worker，避免每个 worker 复制一份全量索引。

## ECS 目录

固定目录：

```text
/opt/dnd-rag/app
/opt/dnd-rag/data/fvtt-cn-5etools/data
/opt/dnd-rag/storage/embedding-index/full.jsonl
/opt/dnd-rag/.env.production
```

上传代码：

```bash
rsync -av --exclude .git --exclude .venv --exclude data --exclude storage --exclude reports ./ root@ECS_IP:/opt/dnd-rag/app/
```

上传授权数据和全量索引：

```bash
rsync -av data/fvtt-cn-5etools/data/ root@ECS_IP:/opt/dnd-rag/data/fvtt-cn-5etools/data/
rsync -av storage/embedding-index/full.jsonl root@ECS_IP:/opt/dnd-rag/storage/embedding-index/full.jsonl
```

也可以使用仓库内脚本完成同步和启动：

```bash
ECS_HOST=ECS_IP \
ECS_USER=root \
scripts/deploy_ecs.sh
```

脚本默认会同步应用代码、授权数据、全量 embedding index，并在 ECS 上执行：

```bash
docker compose up -d --build app
```

如果数据或索引已经在 ECS 上，可跳过对应同步：

```bash
ECS_HOST=ECS_IP SYNC_DATA=0 SYNC_INDEX=0 scripts/deploy_ecs.sh
```

## ECS 环境变量

在 ECS 写入 `/opt/dnd-rag/.env.production`：

```bash
FIVEETOOLS_DATA_DIR=/opt/dnd-rag/data/fvtt-cn-5etools/data
EMBEDDING_INDEX_PATH=/opt/dnd-rag/storage/embedding-index/full.jsonl
QUERY_EMBEDDING_PROVIDER=dashscope

ANSWER_PROVIDER=deepseek
DEEPSEEK_API_KEY=replace-with-production-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions

DASHSCOPE_API_KEY=replace-with-production-key
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSIONS=1024
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings

RAG_GATEWAY_TOKEN=replace-with-long-random-token
REQUIRE_GATEWAY_TOKEN=true
```

`RAG_GATEWAY_TOKEN` 必须和 Cloudflare Pages Function 的环境变量一致。生产环境保持 `REQUIRE_GATEWAY_TOKEN=true`，这样如果漏配 token，FastAPI 会直接启动失败，而不是以开放 API 的状态运行。

## ECS 安全组

安全组只需要开放：

- SSH：`22/tcp`，建议限制为自己的办公/家庭 IP。
- FastAPI 后端：`8000/tcp`，公开访问也可以，因为 `/api/*` 仍要求 `X-RAG-GATEWAY-TOKEN`。

不要开放数据库端口。当前首版不在 ECS 对外暴露 Postgres/pgvector。

## 启动后端

```bash
cd /opt/dnd-rag/app
docker compose up -d --build app
docker compose logs -f app
```

如需在非 ECS 机器上预览 compose 配置，可临时覆盖 env 文件路径：

```bash
RAG_ENV_FILE=.env.example docker compose config
```

健康检查：

```bash
curl http://ECS_IP:8000/healthz
```

业务 API 必须被 token 保护：

```bash
curl -i http://ECS_IP:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"隐身的人攻击有优势吗？"}'
```

预期返回 `401`。

带 token smoke test：

```bash
curl http://ECS_IP:8000/api/ask \
  -H 'Content-Type: application/json' \
  -H 'X-RAG-GATEWAY-TOKEN: replace-with-long-random-token' \
  -d '{"question":"法师挨打后专注会立刻断吗？","scope":"core"}'
```

或使用脚本一次性检查健康状态、token 保护和 3 个真实问题：

```bash
BACKEND_ORIGIN=http://ECS_IP:8000 \
RAG_GATEWAY_TOKEN=replace-with-long-random-token \
scripts/smoke_public_demo.sh
```

## Cloudflare Pages

Pages 项目设置：

- Build command: 留空
- Build output directory: `static`
- Functions directory: `functions`

仓库也提供了 `wrangler.toml`：

```toml
pages_build_output_dir = "static"
```

如果使用 Wrangler CLI，可从仓库根目录部署 Pages：

```bash
npx wrangler pages deploy
```

Pages Function 环境变量：

```text
BACKEND_ORIGIN=http://ECS_IP:8000
RAG_GATEWAY_TOKEN=replace-with-long-random-token
```

创建 KV namespace 并绑定到 Pages Functions：

```text
Binding name: RATE_LIMIT_KV
```

限流默认：

- 10 requests / minute / IP
- 100 requests / day / IP
- 单问题 500 字

## Cloudflare Smoke Test

部署成功后访问：

```text
https://PROJECT.pages.dev
```

测试问题：

```text
隐身的人攻击有优势吗？
法师挨打后专注会立刻断吗？
法术被超魔静默施法处理后，还能被反制法术反制吗？
```

验收点：

- 页面能打开。
- `/api/ask` 返回 DeepSeek 生成答案。
- 返回中包含引用、证据、相关条目和 evidence requirements。
- 高频请求触发 `429`。
- 直接访问 ECS `/api/ask` 无 token 返回 `401`。

Pages 发布后可以继续复用 smoke 脚本：

```bash
BACKEND_ORIGIN=http://ECS_IP:8000 \
PUBLIC_ORIGIN=https://PROJECT.pages.dev \
RAG_GATEWAY_TOKEN=replace-with-long-random-token \
scripts/smoke_public_demo.sh
```

如需实际验证限流，加上 `CHECK_RATE_LIMIT=1`。这个检查会消耗当前 IP 的公开 demo 配额，建议只在最终验收时跑一次。

## 成本和扩容

如果 8GB ECS 出现 OOM 或启动不稳定：

- 优先升到 4 vCPU / 16GB。
- 不增加 uvicorn worker 数。
- 后续再迁移 pgvector 或专用向量库，降低 Python 进程常驻内存。
