#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${ECS_HOST:?Set ECS_HOST, for example ECS_HOST=1.2.3.4}"
ECS_USER="${ECS_USER:-root}"
ECS_BASE_DIR="${ECS_BASE_DIR:-/opt/dnd-rag}"
ECS_APP_DIR="${ECS_APP_DIR:-${ECS_BASE_DIR}/app}"
LOCAL_DATA_DIR="${LOCAL_DATA_DIR:-${ROOT_DIR}/data/fvtt-cn-5etools/data}"
LOCAL_INDEX_PATH="${LOCAL_INDEX_PATH:-${ROOT_DIR}/storage/embedding-index/full.jsonl}"
SYNC_DATA="${SYNC_DATA:-1}"
SYNC_INDEX="${SYNC_INDEX:-1}"
START_APP="${START_APP:-1}"
SSH_OPTS="${SSH_OPTS:-}"

remote="${ECS_USER}@${ECS_HOST}"

require_path() {
  local path="$1"
  local label="$2"
  if [[ ! -e "$path" ]]; then
    echo "Missing ${label}: ${path}" >&2
    exit 1
  fi
}

ssh_remote() {
  # shellcheck disable=SC2086
  ssh ${SSH_OPTS} "$remote" "$@"
}

rsync_remote() {
  # shellcheck disable=SC2086
  rsync -az --delete -e "ssh ${SSH_OPTS}" "$@"
}

require_path "${ROOT_DIR}/Dockerfile" "Dockerfile"
require_path "${ROOT_DIR}/docker-compose.prod.yml" "production compose file"

if [[ "$SYNC_DATA" == "1" ]]; then
  require_path "$LOCAL_DATA_DIR" "authorized 5e.tools data directory"
fi

if [[ "$SYNC_INDEX" == "1" ]]; then
  require_path "$LOCAL_INDEX_PATH" "full embedding index"
fi

echo "Creating ECS directories on ${remote}..."
ssh_remote "mkdir -p '${ECS_APP_DIR}' '${ECS_BASE_DIR}/data/fvtt-cn-5etools/data' '${ECS_BASE_DIR}/storage/embedding-index'"

echo "Syncing app code to ${remote}:${ECS_APP_DIR}/ ..."
rsync_remote \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".env" \
  --exclude ".env.*" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  --exclude "data" \
  --exclude "storage" \
  --exclude "reports" \
  "${ROOT_DIR}/" "${remote}:${ECS_APP_DIR}/"

if [[ "$SYNC_DATA" == "1" ]]; then
  echo "Syncing authorized data to ECS..."
  rsync_remote "${LOCAL_DATA_DIR}/" "${remote}:${ECS_BASE_DIR}/data/fvtt-cn-5etools/data/"
else
  echo "Skipping data sync because SYNC_DATA=${SYNC_DATA}."
fi

if [[ "$SYNC_INDEX" == "1" ]]; then
  echo "Syncing full embedding index to ECS..."
  rsync_remote "$LOCAL_INDEX_PATH" "${remote}:${ECS_BASE_DIR}/storage/embedding-index/full.jsonl"
else
  echo "Skipping embedding index sync because SYNC_INDEX=${SYNC_INDEX}."
fi

if [[ "$START_APP" == "1" ]]; then
  echo "Building and starting FastAPI app on ECS..."
  ssh_remote "cd '${ECS_APP_DIR}' && docker compose -f docker-compose.prod.yml up -d --build app"
  echo "Recent app logs:"
  ssh_remote "cd '${ECS_APP_DIR}' && docker compose -f docker-compose.prod.yml logs --tail 40 app"
else
  echo "Skipping app start because START_APP=${START_APP}."
fi

cat <<EOF

Deployment sync finished.

Required ECS env file:
  ${ECS_BASE_DIR}/.env.production

Useful checks:
  curl http://${ECS_HOST}:8000/healthz
  BACKEND_ORIGIN=http://${ECS_HOST}:8000 RAG_GATEWAY_TOKEN=... scripts/smoke_public_demo.sh
EOF
