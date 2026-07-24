#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${AI_HEALTH_PROJECT_DIR:-$HOME/workbench/AH_web_development_assignment}"
WORKER_PYTHON="${AI_HEALTH_WORKER_PYTHON:-$HOME/.venvs/ai-health-worker/bin/python}"

cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
    echo "Worker environment file is missing: $PROJECT_DIR/.env" >&2
    exit 1
fi

if [[ ! -x "$WORKER_PYTHON" ]]; then
    echo "Worker Python is missing: $WORKER_PYTHON" >&2
    exit 1
fi

set -a
source .env
set +a

# The deployed API, MySQL, Redis, media files, and worker all run on this Mac.
export DB_HOST="${WORKER_DB_HOST:-localhost}"
export REDIS_HOST="${WORKER_REDIS_HOST:-localhost}"
export REDIS_PORT="${WORKER_REDIS_PORT:-6379}"
export MEDIA_ROOT="${WORKER_MEDIA_ROOT:-$PROJECT_DIR/media}"

exec "$WORKER_PYTHON" -u -m worker.main
