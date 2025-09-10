#!/bin/bash
set -euo pipefail

mkdir -p "$(dirname "$LOG_FILE_PATH")"
touch "$LOG_FILE_PATH"

echo "[entrypoint] Starting cron..."
cron

echo "[entrypoint] Tail logs..."
exec tail -F "$LOG_FILE_PATH"
