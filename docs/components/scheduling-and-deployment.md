# Scheduling and deployment

## Responsibility

The deployment layer installs a Python environment, starts cron, runs the batch stages in order, persists logs, and
keeps the application container alive. It does not run PostgreSQL inside the application image.

## Production schedule

The tracked `amadeus_saadaal_flood_forecaster_cron` contains:

```cron
0 12 * * * root bash <repo>/scripts/amadeus_saadaal_flood_forecaster_resilient.sh <repo> <venv> >> <log> 2>&1
```

This runs daily at 12:00 in the container timezone (normally UTC unless deployment configuration changes it). The Docker
build substitutes the repository, virtual-environment, and log paths and installs the rendered file in `/etc/cron.d/`.

## Pipeline orchestration

The resilient production script executes:

1. Fetch historical Open-Meteo weather.
2. Fetch forecast Open-Meteo weather and verify freshness if the fetch fails.
3. Fetch latest SWALIM river levels.
4. Infer horizon-seven `Prophet_001` predictions for Belet Weyne, Bulo Burti, Jowhar, Dollow, and Luuq.
5. Assign risk levels.
6. Send a full-risk alert when required.

The original `amadeus_saadaal_flood_forecaster.sh` is fail-fast (`set -euo pipefail`). The tracked cron uses the
resilient variant, which retries ingestion, isolates per-station inference failures, and continues to later stages where
possible.

| Resilient exit | Meaning                                                              |
|----------------|----------------------------------------------------------------------|
| `0`            | Every counted task succeeded                                         |
| `2`            | Partial success; at least one task succeeded and at least one failed |
| `1`            | Invalid setup, critical stale forecast, or complete failure          |

## Container lifecycle

`Dockerfile`:

- Starts from `python:3.12`.
- Installs cron, build tools, Git, curl, and certificates.
- Installs `uv`, creates `.venv`, and runs `uv sync --locked --no-dev --no-editable`.
- Copies and renders the cron definition.
- Uses `docker-entrypoint.sh` as entrypoint.

At startup, the entrypoint snapshots an explicit allowlist of environment variables to root `.env` (mode `0600`),
creates the log file, starts cron, and runs `tail -F` on the log as PID 1. This makes cron output visible through
container logs. The snapshot exists because cron jobs do not inherit the container's runtime environment.

Required deployment values:

```text
DB_HOST
POSTGRES_PASSWORD
MAILJET_API_KEY
MAILJET_API_SECRET
```

Optional: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `LOG_LEVEL`, `CONTACT_LIST_ID`.

Only allowlisted variables reach `.env`, and only if they are actually set in the container. The allowlist lives in
`docker-entrypoint.sh` and must be kept in sync with the variables read via `os.getenv()` in the codebase - a variable
that is missing from the allowlist, or missing from the deployment config, is invisible to the pipeline.

`DB_HOST` and `POSTGRES_PASSWORD` are validated at startup: the entrypoint prints the names it captured and an explicit
error block if either is missing, and the pipeline script aborts immediately rather than retrying doomed commands.
Startup log lines to check after a deploy:

```text
[entrypoint] Captured into .env: DB_HOST POSTGRES_PASSWORD ...
```

## PostgreSQL deployment modes

### Local development

```bash
export POSTGRES_PASSWORD=testpassword
docker compose up -d
export DB_HOST=localhost
```

`docker-compose.yml` runs only PostgreSQL 15 and initializes the application tables from `database_bootstrap.sql`. It
does not build/run the Python application, install indexes/views, or define a durable named volume.

### Deployed container

The application connects to the PostgreSQL host supplied in `DB_HOST`. Ensure network access to port `5432`, initialize
schema `flood_forecaster`, and apply any required indexes/views separately.

## Build and manual execution

Build the same image used by container deployment:

```bash
docker build -t saadaal-flood-forecaster .
```

Run the resilient pipeline from an installed checkout without waiting for cron:

```bash
bash scripts/amadeus_saadaal_flood_forecaster_resilient.sh \
  "$(pwd)" "$(pwd)/.venv"
```

This performs external requests, database writes, and potentially sends an alert.

## Operational verification

```bash
# In the application container
cat /etc/cron.d/amadeus_saadaal_flood_forecaster_cron
pgrep -a cron
tail -F logs/logs_amadeus_saadaal_flood_forecaster.log

# Verify database reachability from an environment with psql
psql -h "$DB_HOST" -U postgres -d postgres -c 'SELECT 1;'
```

CapRover-specific steps are in [Container deployment](../container-deployment-guide.md); script behavior is detailed
in [Scripts reference](../scripts-reference.md).

## Key implementation paths

- Image: `Dockerfile`
- Entrypoint: `docker-entrypoint.sh`
- Schedule: `amadeus_saadaal_flood_forecaster_cron`
- Production orchestrator: `scripts/amadeus_saadaal_flood_forecaster_resilient.sh`
- Strict orchestrator: `scripts/amadeus_saadaal_flood_forecaster.sh`
- Local PostgreSQL: `docker-compose.yml`
