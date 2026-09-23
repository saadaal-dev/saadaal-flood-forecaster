#!/bin/bash
set -euo pipefail

# The cron jobs run with a minimal environment (cron does not inherit the
# container's runtime environment), so the pipeline needs the required
# variables persisted to a .env file that the scripts source and that
# python-dotenv (load_dotenv) reads directly.
#
# We deliberately snapshot ONLY the variables the application actually uses,
# rather than dumping the whole environment with `printenv`. Dumping
# everything persisted unrelated secrets to disk and broadened access beyond
# what the pipeline needs.
ENV_FILE="$REPOSITORY_ROOT_PATH/.env"

# Keep in sync with the variables read via os.getenv() in the codebase.
ENV_ALLOWLIST=(
  DB_HOST
  POSTGRES_PASSWORD
  SENTRY_DSN
  SENTRY_ENVIRONMENT
  SENTRY_RELEASE
  LOG_LEVEL
  MAILJET_API_KEY
  MAILJET_API_SECRET
  CONTACT_LIST_ID
)

# Create the file with restrictive permissions from the start (umask 077 -> 0600).
umask 077
: > "$ENV_FILE"

for _var in "${ENV_ALLOWLIST[@]}"; do
  # Only write variables that are actually set.
  if [ -n "${!_var:-}" ]; then
    # Emit the same unquoted KEY=value form that `printenv` produced, so the
    # file parses identically with python-dotenv (load_dotenv), which is the
    # authoritative consumer. We intentionally do NOT add shell quoting: bash
    # `source` and python-dotenv disagree on escape semantics, and quoting to
    # satisfy `source` breaks python-dotenv parsing. This preserves the
    # original, working behaviour while restricting the file to the allowlist.
    printf '%s=%s\n' "$_var" "${!_var}" >> "$ENV_FILE"
  fi
done
chmod 600 "$ENV_FILE"

mkdir -p "$(dirname "$LOG_FILE_PATH")"
touch "$LOG_FILE_PATH"

echo "[entrypoint] Starting cron..."
cron

echo "[entrypoint] Tail logs..."
exec tail -F "$LOG_FILE_PATH"
