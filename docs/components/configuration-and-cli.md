# Configuration and CLI

## Responsibility

`flood-cli` is the common entry point for ingestion, database inspection, model development/inference, risk assessment,
and alerts. `config/config.ini` supplies non-secret defaults; environment variables supply credentials, host-specific
settings, and observability settings.

## Configuration sources

| Source                             | Used for                                                                                                                                            |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `config/config.ini`                | Data paths/source, API URLs, database name/user/port, lag windows, model defaults/artifact paths, sensor feature flag, and Mailjet sender/recipient |
| `data/static/station-mapping.json` | Forecast station to upstream-river and weather-location mapping                                                                                     |
| `data/static/station-metadata.csv` | Station coordinates and moderate/high/full thresholds                                                                                               |
| Environment or root `.env`         | Database host/password, Mailjet credentials, Sentry, and log level                                                                                  |

`Config` uses extended INI interpolation, so values such as `${data:data_path}` are resolved at load time. Most commands
accept a custom configuration path, but `risk-assessment` and `alert` currently load `config/config.ini` directly.

### Required environment variables

| Variable             | Required when          | Meaning                                      |
|----------------------|------------------------|----------------------------------------------|
| `DB_HOST`            | Any database operation | PostgreSQL hostname or IP                    |
| `POSTGRES_PASSWORD`  | Any database operation | Password for `[data.database] user`          |
| `MAILJET_API_KEY`    | Sending alerts         | Mailjet API key                              |
| `MAILJET_API_SECRET` | Sending alerts         | Mailjet API secret                           |
| `SENTRY_DSN`         | Optional               | Enables Sentry                               |
| `SENTRY_ENVIRONMENT` | Optional               | Sentry environment; defaults to `production` |
| `SENTRY_RELEASE`     | Optional               | Release attached to Sentry events            |
| `LOG_LEVEL`          | Optional               | Python log level; defaults to `INFO`         |

Do not commit `.env`. The Docker entrypoint writes all container environment variables to the root `.env` so cron can
load them.

## Important settings

| Section/key                         | Current default         | Effect                                                                      |
|-------------------------------------|-------------------------|-----------------------------------------------------------------------------|
| `[data] data_source`                | `database`              | Chooses database or CSV loaders for modelling/inference                     |
| `[data.ingestion] use_database`     | `True`                  | Persists fetched weather to PostgreSQL rather than CSV                      |
| `[model] weather_lag_days`          | `[1,3,7,14,30,0,-2,-6]` | Weather feature offsets; zero/negative offsets consume forecast weather     |
| `[model] river_station_lag_days`    | `[1,3,7,14,30]`         | River-level feature offsets                                                 |
| `[model] forecast_days`             | `1`                     | Default model horizon when CLI `-f` is omitted; `1` means the reference day |
| `[model] model_type`                | `XGBoost_001`           | Default for manual model commands when `-m` is omitted                      |
| `[data.sensor] use_sensor_rainfall` | `False`                 | Enables optional IoT rainfall during inference                              |

The scheduled scripts override the model defaults with `-f 7 -m Prophet_001`.

## CLI map

Install the package, activate its environment, then inspect authoritative options with:

```bash
flood-cli --help
flood-cli <group> --help
flood-cli <group> <command> --help
```

### Ingestion

```text
flood-cli data-ingestion fetch-openmeteo {historical|forecast} [-c FILE] [--dry-run]
flood-cli data-ingestion fetch-river-data [-c FILE]
flood-cli data-ingestion fetch-river-data-from-csv STATION [--snrfa-file FILE] [--swalim-file FILE] [-c FILE]
flood-cli data-ingestion fetch-river-data-from-chart-api STATION [-o FILE] [-c FILE]
flood-cli data-ingestion show-latest-swalim-river-csv STATION [-c FILE]
flood-cli data-ingestion show-latest-snrfa-river-csv STATION [-c FILE]
flood-cli data-ingestion remove-duplicates-historical-weather [--dry-run] [-c FILE]
```

`load-csv` is exposed but remains a placeholder and does not load data. `--empty-table` is exposed by `fetch-openmeteo`
but is not currently passed to the fetch implementation.

### Model lifecycle and inference

```text
flood-cli ml preprocess STATION [CONFIG_PATH] [-f DAYS]
flood-cli ml analyze [CONFIG_PATH] [-f DAYS]
flood-cli ml split STATION [CONFIG_PATH] [-f DAYS]
flood-cli ml train STATION [CONFIG_PATH] [-f DAYS] [-m MODEL]
flood-cli ml eval STATION [CONFIG_PATH] [-f DAYS] [-m MODEL]
flood-cli ml build-model STATION [CONFIG_PATH] [-f DAYS] [-m MODEL]
flood-cli ml infer STATION [CONFIG_PATH] [-f DAYS] [-d YYYY-MM-DD] [-m MODEL] [-o stdout|database]
flood-cli ml bulk-infer [STATION ...] [-f DAYS ...] [-m MODEL ...] [-c FILE] [-o stdout|database]
flood-cli ml list-model-types
flood-cli ml list-stations [-c FILE]
flood-cli ml list-models [-c FILE]
```

Supported model types are `RandomForestRegressor_001`, `XGBoost_001`, and `Prophet_001`. A model artifact is horizon-
and station-specific; inference fails when its matching artifact is absent.

### Database utilities

```text
flood-cli database-model list-db-schemas [-c FILE]
flood-cli database-model list-tables-from-schema -s SCHEMA [-c FILE]
flood-cli database-model fetch-table-to-csv -s SCHEMA -t TABLE -d DIRECTORY [--force-overwrite] [-p ROWS] [-w SQL] [-c FILE]
flood-cli database-model validate-table-data [-s SCHEMA] [-t TABLE] [-c FILE]
flood-cli database-model validate-sensor-readings [-s SCHEMA] [-t TABLE] [-c FILE]
flood-cli database-model compare-sensor-weather -l LOCATION... --date-from YYYY-MM-DD --date-to YYYY-MM-DD [-o FILE] [-c FILE]
```

`fetch-table-to-csv --where` inserts operator-provided SQL into a query. Use it only with trusted input.

### Operational stages

```text
flood-cli risk-assessment
flood-cli alert
```

These are normally called by the scheduled pipeline. Running `alert` can send a real email when full-risk rows exist.

## Key implementation paths

- CLI registration: `src/flood_forecaster_cli/main.py`
- Commands: `src/flood_forecaster_cli/commands/`
- Configuration loader: `src/flood_forecaster/utils/configuration.py`
- Defaults: `config/config.ini`
