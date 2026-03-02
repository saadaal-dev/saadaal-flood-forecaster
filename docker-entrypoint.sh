#!/bin/bash
set -euo pipefail

# Export only the required environment variables for the cron job
# Avoids dumping ALL env vars (which may contain secrets) to a plain file
{
    echo "REPOSITORY_ROOT_PATH=$REPOSITORY_ROOT_PATH"
    echo "VENV_PATH=$VENV_PATH"
    echo "LOGS_PATH=$LOGS_PATH"
    echo "LOG_FILE_PATH=$LOG_FILE_PATH"
    # Database
    [ -n "${POSTGRES_PASSWORD:-}" ] && echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    # Sentry
    [ -n "${SENTRY_DSN:-}" ] && echo "SENTRY_DSN=$SENTRY_DSN"
    [ -n "${SENTRY_ENVIRONMENT:-}" ] && echo "SENTRY_ENVIRONMENT=$SENTRY_ENVIRONMENT"
    [ -n "${SENTRY_RELEASE:-}" ] && echo "SENTRY_RELEASE=$SENTRY_RELEASE"
    # Logging
    [ -n "${LOG_LEVEL:-}" ] && echo "LOG_LEVEL=$LOG_LEVEL"
    # Mailjet
    [ -n "${MAILJET_API_KEY:-}" ] && echo "MAILJET_API_KEY=$MAILJET_API_KEY"
    [ -n "${MAILJET_API_SECRET:-}" ] && echo "MAILJET_API_SECRET=$MAILJET_API_SECRET"
    # Database host override
    [ -n "${DB_HOST:-}" ] && echo "DB_HOST=$DB_HOST"
    [ -n "${DB_PORT:-}" ] && echo "DB_PORT=$DB_PORT"
    [ -n "${DB_NAME:-}" ] && echo "DB_NAME=$DB_NAME"
    [ -n "${DB_USER:-}" ] && echo "DB_USER=$DB_USER"
} > "$REPOSITORY_ROOT_PATH/.env"

# Restrict permissions on .env file (owner read/write only)
chmod 600 "$REPOSITORY_ROOT_PATH/.env"

mkdir -p "$(dirname "$LOG_FILE_PATH")"
touch "$LOG_FILE_PATH"

echo "[entrypoint] Starting cron..."
cron

echo "[entrypoint] Tail logs..."
exec tail -F "$LOG_FILE_PATH"
