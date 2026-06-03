#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT_ASSETS="${STRICT_ASSETS:-0}"
RUN_TESTS="${RUN_TESTS:-0}"
LOCAL_DATA_DIR="${LOCAL_DATA_DIR:-${ROOT_DIR}/data/fvtt-cn-5etools/data}"
LOCAL_INDEX_PATH="${LOCAL_INDEX_PATH:-${ROOT_DIR}/storage/embedding-index/full.jsonl}"
MIN_FULL_INDEX_ROWS="${MIN_FULL_INDEX_ROWS:-25000}"

pass() {
  printf 'ok - %s\n' "$1"
}

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

require_file() {
  local path="$1"
  local label="$2"
  [[ -f "$path" ]] || fail "missing ${label}: ${path}"
  pass "${label}"
}

require_dir() {
  local path="$1"
  local label="$2"
  [[ -d "$path" ]] || fail "missing ${label}: ${path}"
  pass "${label}"
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail "missing command: ${command_name}"
  pass "command ${command_name}"
}

check_no_secret_patterns() {
  local api_key_pattern
  local password_pattern
  local known_dashscope_fragment
  local known_deepseek_fragment
  local pattern
  api_key_pattern='s''k-[A-Za-z0-9_-]{16,}'
  password_pattern='D''xh[0-9A-Za-z]+'
  known_dashscope_fragment='dd6cba8563be4''df'
  known_deepseek_fragment='3f244e55''d690'
  pattern="(${api_key_pattern}|${password_pattern}|${known_dashscope_fragment}|${known_deepseek_fragment})"

  if rg -n --hidden \
    --glob '!data/**' \
    --glob '!storage/**' \
    --glob '!reports/**' \
    --glob '!.git/**' \
    --glob '!.venv/**' \
    "$pattern" \
    "$ROOT_DIR" >/tmp/dnd-rag-secret-scan.txt; then
    cat /tmp/dnd-rag-secret-scan.txt >&2
    fail "possible secret-like value found"
  fi
  pass "secret scan"
}

check_static_assets() {
  require_file "${ROOT_DIR}/static/index.html" "static/index.html"
  require_file "${ROOT_DIR}/static/app.js" "static/app.js"
  require_file "${ROOT_DIR}/static/styles.css" "static/styles.css"
  require_file "${ROOT_DIR}/functions/api/[[path]].js" "Cloudflare Pages Function"
}

check_config_files() {
  require_file "${ROOT_DIR}/Dockerfile" "Dockerfile"
  require_file "${ROOT_DIR}/docker-compose.yml" "default compose file"
  require_file "${ROOT_DIR}/docker-compose.prod.yml" "production compose file"
  require_file "${ROOT_DIR}/wrangler.toml" "Wrangler Pages config"
  require_file "${ROOT_DIR}/.env.example" "environment template"

  grep -q '^  app:' "${ROOT_DIR}/docker-compose.yml" || fail "docker-compose.yml must define app service"
  grep -q -- '--workers' "${ROOT_DIR}/docker-compose.yml" || fail "docker-compose.yml app service must pin uvicorn workers"
  grep -q 'EMBEDDING_INDEX_PATH.*full.jsonl' "${ROOT_DIR}/docker-compose.yml" || fail "docker-compose.yml must point app to full embedding index"
  pass "default compose app service"

  grep -q 'pages_build_output_dir = "static"' "${ROOT_DIR}/wrangler.toml" || fail "wrangler.toml must set pages_build_output_dir to static"
  pass "Wrangler build output"

  grep -q 'RAG_GATEWAY_TOKEN=replace-with' "${ROOT_DIR}/.env.example" || fail ".env.example must document RAG_GATEWAY_TOKEN"
  grep -q 'QUERY_EMBEDDING_PROVIDER=dashscope' "${ROOT_DIR}/.env.example" || fail ".env.example must document DashScope query embedding"
  pass "production env template"
}

check_script_syntax() {
  bash -n "${ROOT_DIR}/scripts/deploy_ecs.sh"
  bash -n "${ROOT_DIR}/scripts/smoke_public_demo.sh"
  bash -n "${ROOT_DIR}/scripts/check_deployment_readiness.sh"
  node --check "${ROOT_DIR}/functions/api/[[path]].js" >/dev/null
  node --check "${ROOT_DIR}/scripts/test_cloudflare_function.mjs" >/dev/null
  pass "deployment script syntax"
}

check_cloudflare_function_behavior() {
  node "${ROOT_DIR}/scripts/test_cloudflare_function.mjs" >/dev/null
  pass "Cloudflare Function smoke behavior"
}

check_full_assets() {
  require_dir "$LOCAL_DATA_DIR" "authorized full data directory"
  require_file "$LOCAL_INDEX_PATH" "full embedding index"

  local rows
  rows="$(wc -l < "$LOCAL_INDEX_PATH" | tr -d ' ')"
  if [[ "$rows" -lt "$MIN_FULL_INDEX_ROWS" ]]; then
    fail "full embedding index has ${rows} rows, expected at least ${MIN_FULL_INDEX_ROWS}"
  fi
  pass "full embedding index row count ${rows}"
}

require_command rg
require_command node
require_command bash
check_static_assets
check_config_files
check_script_syntax
check_cloudflare_function_behavior
git -C "$ROOT_DIR" diff --check
pass "git diff whitespace check"
check_no_secret_patterns

if [[ "$STRICT_ASSETS" == "1" ]]; then
  check_full_assets
else
  echo "skip - full data and full.jsonl asset check; set STRICT_ASSETS=1 to require them"
fi

if [[ "$RUN_TESTS" == "1" ]]; then
  "${ROOT_DIR}/.venv/bin/python" -m unittest discover -s tests -v
  pass "Python unit tests"
else
  echo "skip - Python unit tests; set RUN_TESTS=1 to run them"
fi

echo "Deployment readiness checks finished."
