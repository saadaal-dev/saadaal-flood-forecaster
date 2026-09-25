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

# Variables the pipeline cannot run without. Anything else is optional.
ENV_REQUIRED=(
  DB_HOST
  POSTGRES_PASSWORD
)

captured=()
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
    captured+=("$_var")
  fi
done
chmod 600 "$ENV_FILE"

# Report which allowlisted variables made it into the snapshot. Names only -
# never values - so container logs stay safe to share.
echo "[entrypoint] Captured into .env: ${captured[*]:-<none>}"

# Fail loudly *now* if a required variable is missing. Without this the
# container starts happily and the failure only surfaces when cron fires,
# as an opaque "DB_HOST environment variable not set." traceback.
missing=()
for _var in "${ENV_REQUIRED[@]}"; do
  if [ -z "${!_var:-}" ]; then
    missing+=("$_var")
  fi
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "[entrypoint] ============================================================"
  echo "[entrypoint] ERROR: required environment variable(s) not set in this"
  echo "[entrypoint]        container: ${missing[*]}"
  echo "[entrypoint]"
  echo "[entrypoint] Every database operation will fail until these are set."
  echo "[entrypoint] Set them in the CapRover app config (App Configs ->"
  echo "[entrypoint] Environmental Variables), save & update, then re-run the"
  echo "[entrypoint] pipeline with scripts/trigger_forecast_now.sh --resilient."
  echo "[entrypoint] ============================================================"
fi

mkdir -p "$(dirname "$LOG_FILE_PATH")"
touch "$LOG_FILE_PATH"

echo "[entrypoint] Starting cron..."
cron

echo "[entrypoint] Tail logs..."
exec tail -F "$LOG_FILE_PATH"
