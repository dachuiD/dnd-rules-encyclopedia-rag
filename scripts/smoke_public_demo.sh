#!/usr/bin/env bash
set -euo pipefail

: "${BACKEND_ORIGIN:?Set BACKEND_ORIGIN, for example BACKEND_ORIGIN=http://1.2.3.4:8000}"
PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-}"
RAG_GATEWAY_TOKEN="${RAG_GATEWAY_TOKEN:-}"
CHECK_RATE_LIMIT="${CHECK_RATE_LIMIT:-0}"
EXPECT_FULL_DATA="${EXPECT_FULL_DATA:-0}"
EXPECT_PRODUCTION_PROVIDERS="${EXPECT_PRODUCTION_PROVIDERS:-${EXPECT_FULL_DATA}}"
MIN_HEALTHZ_DOCUMENTS="${MIN_HEALTHZ_DOCUMENTS:-5066}"
MIN_HEALTHZ_CHUNKS="${MIN_HEALTHZ_CHUNKS:-29868}"
MIN_HEALTHZ_EMBEDDINGS="${MIN_HEALTHZ_EMBEDDINGS:-29287}"
EXPECTED_QUERY_PROVIDER="${EXPECTED_QUERY_PROVIDER:-DashScopeEmbeddingProvider}"
EXPECTED_ANSWER_PROVIDER="${EXPECTED_ANSWER_PROVIDER:-DeepSeekLLMProvider}"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

json_escape() {
  python3 - "$1" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1], ensure_ascii=False))
PY
}

request_json() {
  local url="$1"
  local payload="$2"
  shift 2
  curl -sS -o "${tmp_dir}/body" -w "%{http_code}" \
    -H "Content-Type: application/json" \
    "$@" \
    -d "$payload" \
    "$url"
}

expect_status() {
  local got="$1"
  local expected="$2"
  local label="$3"
  if [[ "$got" != "$expected" ]]; then
    echo "${label}: expected HTTP ${expected}, got ${got}" >&2
    echo "Response body:" >&2
    cat "${tmp_dir}/body" >&2 || true
    exit 1
  fi
  echo "${label}: HTTP ${got}"
}

ask_payload() {
  local question="$1"
  local scope="${2:-core}"
  local escaped
  escaped="$(json_escape "$question")"
  printf '{"question":%s,"scope":"%s"}' "$escaped" "$scope"
}

check_healthz_counts() {
  if [[ "$EXPECT_FULL_DATA" != "1" ]]; then
    echo "Skipping full healthz count check because EXPECT_FULL_DATA=${EXPECT_FULL_DATA}."
    return
  fi

  python3 - "${tmp_dir}/body" "$MIN_HEALTHZ_DOCUMENTS" "$MIN_HEALTHZ_CHUNKS" "$MIN_HEALTHZ_EMBEDDINGS" <<'PY'
import json
import sys

body_path, min_documents, min_chunks, min_embeddings = sys.argv[1:5]
with open(body_path, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

checks = [
    ("documents", int(min_documents)),
    ("chunks", int(min_chunks)),
    ("embeddings", int(min_embeddings)),
]

for key, minimum in checks:
    value = int(payload.get(key, 0))
    if value < minimum:
        raise SystemExit(f"healthz {key} expected >= {minimum}, got {value}")

print(
    "backend full data healthz: "
    f"documents={payload.get('documents')} "
    f"chunks={payload.get('chunks')} "
    f"embeddings={payload.get('embeddings')}"
)
PY
}

check_healthz_providers() {
  if [[ "$EXPECT_PRODUCTION_PROVIDERS" != "1" ]]; then
    echo "Skipping production provider check because EXPECT_PRODUCTION_PROVIDERS=${EXPECT_PRODUCTION_PROVIDERS}."
    return
  fi

  python3 - "${tmp_dir}/body" "$EXPECTED_QUERY_PROVIDER" "$EXPECTED_ANSWER_PROVIDER" <<'PY'
import json
import sys

body_path, expected_query_provider, expected_answer_provider = sys.argv[1:4]
with open(body_path, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

actual_query_provider = payload.get("query_embedding_provider")
actual_answer_provider = payload.get("answer_provider")

if actual_query_provider != expected_query_provider:
    raise SystemExit(
        "healthz query_embedding_provider expected "
        f"{expected_query_provider}, got {actual_query_provider}"
    )

if actual_answer_provider != expected_answer_provider:
    raise SystemExit(
        "healthz answer_provider expected "
        f"{expected_answer_provider}, got {actual_answer_provider}"
    )

print(
    "backend production providers: "
    f"query={actual_query_provider} answer={actual_answer_provider}"
)
PY
}

echo "Checking backend health..."
health_status="$(curl -sS -o "${tmp_dir}/body" -w "%{http_code}" "${BACKEND_ORIGIN%/}/healthz")"
expect_status "$health_status" "200" "backend /healthz"
check_healthz_counts
check_healthz_providers

echo "Checking backend token protection..."
unauthorized_status="$(request_json "${BACKEND_ORIGIN%/}/api/ask" "$(ask_payload "隐身的人攻击有优势吗？")")"
expect_status "$unauthorized_status" "401" "backend /api/ask without token"

if [[ -n "$RAG_GATEWAY_TOKEN" ]]; then
  echo "Checking backend authorized smoke questions..."
  for question in \
    "隐身的人攻击有优势吗？" \
    "法师挨打后专注会立刻断吗？" \
    "法术被超魔静默施法处理后，还能被反制法术反制吗？"
  do
    status="$(request_json "${BACKEND_ORIGIN%/}/api/ask" "$(ask_payload "$question")" -H "X-RAG-GATEWAY-TOKEN: ${RAG_GATEWAY_TOKEN}")"
    expect_status "$status" "200" "backend authorized question: ${question}"
    if ! grep -q '"answer"' "${tmp_dir}/body"; then
      echo "backend authorized question did not include answer field: ${question}" >&2
      cat "${tmp_dir}/body" >&2
      exit 1
    fi
  done
else
  echo "Skipping authorized backend smoke because RAG_GATEWAY_TOKEN is empty."
fi

if [[ -n "$PUBLIC_ORIGIN" ]]; then
  echo "Checking public Pages frontend..."
  public_status="$(curl -sS -o "${tmp_dir}/body" -w "%{http_code}" "${PUBLIC_ORIGIN%/}/")"
  expect_status "$public_status" "200" "public frontend"

  echo "Checking public Pages API proxy..."
  public_api_status="$(request_json "${PUBLIC_ORIGIN%/}/api/ask" "$(ask_payload "隐身的人攻击有优势吗？")")"
  expect_status "$public_api_status" "200" "public /api/ask"

  if [[ "$CHECK_RATE_LIMIT" == "1" ]]; then
    echo "Checking public rate limit; this intentionally spends demo quota for the current IP..."
    limited_status="200"
    for _ in $(seq 1 12); do
      limited_status="$(request_json "${PUBLIC_ORIGIN%/}/api/ask" "$(ask_payload "隐身的人攻击有优势吗？")")"
    done
    expect_status "$limited_status" "429" "public rate limit"
  else
    echo "Skipping rate-limit stress check because CHECK_RATE_LIMIT=${CHECK_RATE_LIMIT}."
  fi
else
  echo "Skipping public Pages checks because PUBLIC_ORIGIN is empty."
fi

echo "Smoke test finished."
