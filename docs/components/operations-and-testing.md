# Operations and testing

## Responsibility

Operational support combines Python logging, cron output, optional Sentry reporting, database freshness checks,
diagnostic scripts, and pytest/tox validation. **OPS-001:** there is no HTTP health endpoint or metrics exporter.

## Logging and Sentry

Every CLI invocation initializes root logging using `LOG_LEVEL` (default `INFO`) and writes formatted records to stdout.
In the scheduled container, shell stdout/stderr is appended to:

```text
logs/logs_amadeus_saadaal_flood_forecaster.log
```

The entrypoint tails this file, so it also appears in container logs.

When `SENTRY_DSN` is set:

- `INFO` and above are captured as breadcrumbs.
- `ERROR` and above are sent as events.
- Trace and profile sampling rates are each `0.1`.
- `SENTRY_ENVIRONMENT` defaults to `production`; `SENTRY_RELEASE` is optional.
- Default PII transmission is disabled.

See [Sentry integration](../sentry-integration.md) for setup and event testing.

## Operational signals

| Signal               | Healthy indication                                                    | Failure indication                                              |
|----------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------|
| Container process    | Entrypoint is tailing the cron log                                    | Container exited/restarts                                       |
| Cron                 | Daily runtime banner in log                                           | No new banner after expected schedule                           |
| Resilient pipeline   | Exit `0` and zero failures in summary                                 | Exit `2` for partial success; `1` for critical/complete failure |
| Forecast freshness   | Maximum forecast date is at least today + 5 days after a failed fetch | Pipeline aborts before inference                                |
| Prediction freshness | Latest stored reference date is within 2 days                         | Alert step exits `1`                                            |
| Sentry               | Errors visible with environment/release                               | Missing DSN warning means local logging only                    |

**OPS-001:** Because cron itself does not publish an exit code externally, monitor the log summary/Sentry and
independently query source/prediction freshness.

## Diagnostics

```bash
# Follow the scheduled run
tail -F logs/logs_amadeus_saadaal_flood_forecaster.log

# Inspect forecast coverage
python scripts/diagnose_forecast_data.py

# Remove the local Open-Meteo request cache
python scripts/clear_cache.py

# Re-fetch forecast data
python scripts/force_refresh_forecast.py

# Inspect river availability and gaps
python scripts/check_river_data_availability.py
# After reviewing the script source and taking a backup
python scripts/fill_river_data_gaps.py
```

Gap filling and forced refresh can mutate data; inspect each script's help/source and take a backup before production
use. Additional commands are catalogued in [Scripts reference](../scripts-reference.md)
and [Server quick reference](../server-quick-reference.md).

## Test categories

Pytest defaults exclude both integration markers through `pyproject.toml`.

```bash
# Unit tests; default and safe without external services
uv run pytest

# A focused test
uv run pytest src/tests/unit/test_risk_assessment.py -q

# Live external API tests; historical weather also needs PostgreSQL
uv run pytest -m integration

# PostgreSQL integration tests
export POSTGRES_PASSWORD=testpassword
export DB_HOST=localhost
docker compose up -d
uv run pytest -m integration_db

# All markers, requiring all dependencies above
uv run pytest -m ''
```

Database tests skip when their expected local PostgreSQL service is unreachable. Live API tests can fail because of
upstream availability or changed remote response formats and should be interpreted separately from unit regressions.

## Repository validation

```bash
tox -e linting
tox -e yaml
tox -e detect-secrets
tox -e test-unit
```

**TEST-001:** `tox.ini` lists `test-integration` in its default environment list but does not define commands for it;
run integration categories explicitly with pytest until that tox environment is implemented.

Priorities and completion criteria for these gaps are maintained in
the [improvement backlog](../improvement-backlog.md).

## Test locations

- Unit: `src/tests/unit/`
- Integration: `src/tests/integration/`
- ML-adjacent tests also exist under `src/flood_forecaster/ml_model/test_*.py` and are collected because
  `pyproject.toml` uses `src` as its test root.
- Shared fixtures/marker support: `src/tests/conftest.py`

## Release checklist

1. Run unit tests and lint/secret checks.
2. Run relevant integration tests when ingestion or database behavior changed.
3. Build the container when lockfile, Docker, cron, or entrypoint behavior changed.
4. Verify model artifacts exist for every scheduled station/horizon/model combination.
5. Verify database schema/migrations and forecast/prediction freshness.
6. Confirm Mailjet recipient and Sentry environment before production deployment.

## Key implementation paths

- Logging/Sentry: `src/flood_forecaster/utils/logging_config.py`
- Test configuration: `pyproject.toml`, `tox.ini`, `requirements-test.txt`
- Diagnostic scripts: `scripts/`
