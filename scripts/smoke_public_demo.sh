#!/usr/bin/env bash
set -euo pipefail

: "${BACKEND_ORIGIN:?Set BACKEND_ORIGIN, for example BACKEND_ORIGIN=http://1.2.3.4:8000}"
PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-}"
RAG_GATEWAY_TOKEN="${RAG_GATEWAY_TOKEN:-}"
CHECK_RATE_LIMIT="${CHECK_RATE_LIMIT:-0}"

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

echo "Checking backend health..."
health_status="$(curl -sS -o "${tmp_dir}/body" -w "%{http_code}" "${BACKEND_ORIGIN%/}/healthz")"
expect_status "$health_status" "200" "backend /healthz"

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
