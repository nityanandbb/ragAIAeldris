#!/usr/bin/env bash
# chmod +x scripts/wait_for_healthy.sh
set -euo pipefail
BASE_URL="${API_BASE_URL:-http://52.221.197.158:8000}"
until curl -sS "${BASE_URL}/openapi.json" >/dev/null; do
  echo "Waiting for API at ${BASE_URL} ..."
  sleep 2
done
echo "API is reachable."
