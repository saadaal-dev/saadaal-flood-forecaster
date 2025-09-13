#!/bin/bash
set -euo pipefail

# Save all environment variables to a .env file
printenv > "$REPOSITORY_ROOT_PATH/.env"

mkdir -p "$(dirname "$LOG_FILE_PATH")"
touch "$LOG_FILE_PATH"

echo "[entrypoint] Starting cron..."
cron

echo "[entrypoint] Tail logs..."
exec tail -F "$LOG_FILE_PATH"
