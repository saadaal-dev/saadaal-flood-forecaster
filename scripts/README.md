# `scripts/`

Everything here wraps the `flood-cli` commands. Only one file sits at the root of this directory: the orchestrator the
production cron job runs. Everything else is grouped by what it is for, so it is always obvious which script is live.

This file is the folder map. For full usage, options, sample output and troubleshooting per script, see
**[docs/scripts-reference.md](../docs/scripts-reference.md)**; the "Details" column below links straight to the relevant
section. Two ready-made runbooks live there too:
[recovery after downtime](../docs/scripts-reference.md#recovery-after-system-downtime) and the
[stale forecast workflow](../docs/scripts-reference.md#typical-troubleshooting-workflow).

## Layout

| Path | What it is for |
|---|---|
| `amadeus_saadaal_flood_forecaster_resilient.sh` | **Production orchestrator.** Invoked daily at 12:00 by the container cron job (`amadeus_saadaal_flood_forecaster_cron`). |
| `ops/` | Operating a running deployment: trigger a run by hand, repair the cron file. |
| `backfill/` | Recomputing or repairing past data: batch inference, prediction catch-up, river data gap filling. |
| `diagnostics/` | Read-only inspection. These write nothing, so they are always safe to run. |
| `maintenance/` | Cleaning or resetting state. Some of these delete data. Read the header before running. |
| `legacy/` | Superseded, kept for reference. Not used by any deployment. |

## The production run

```
amadeus_saadaal_flood_forecaster_cron  ->  scripts/amadeus_saadaal_flood_forecaster_resilient.sh
```

Four phases: data ingestion, inference for the 5 stations, risk assessment, alerting. Ingestion is retried with
exponential backoff, a single station's failure does not stop the others, and the run only aborts outright when the
forecast weather is missing or too stale for predictions to mean anything. Exit codes are `0` for full success, `2` for
partial success, `1` for failure.
Details: [scripts-reference.md](../docs/scripts-reference.md#scriptsamadeus_saadaal_flood_forecaster_resilientsh).

## Contents

Where the Details column says "script header", the script's own docstring or comment block is the reference — these do
not have a section in `scripts-reference.md` yet.

### `ops/`

| Script | Purpose | Details |
|---|---|---|
| `trigger_forecast_now.sh [--resilient]` | Run the pipeline immediately instead of waiting for the next cron tick. Pass `--resilient` to reproduce production; without it you get the legacy strict orchestrator. | script header |
| `switch_to_resilient_cron.sh` | Rewrites the container's live cron file to call the resilient orchestrator. Only needed on containers built from an older image; on a current deployment it is a no-op. | script header |

### `backfill/`

| Script | Purpose | Details |
|---|---|---|
| `batch_infer_and_risk_assess.sh` | Inference plus risk assessment for every station over a date range, without alerting. | [reference](../docs/scripts-reference.md#scriptsbackfillbatch_infer_and_risk_assesssh) |
| `catchup_missing_predictions.py` | Finds every gap in `predicted_river_level`, including gaps in the middle, and fills the missing dates interactively. | [reference](../docs/scripts-reference.md#scriptsbackfillcatchup_missing_predictionspy) |
| `fill_river_data_gaps.py` | Fills gaps in `historical_river_level` from SWALIM's chart API or `public.station_river_data`. Dry run unless `--apply`. Add `--overwrite` to also replace stored readings that disagree with the source — destructive, snapshot first. | [reference](../docs/scripts-reference.md#scriptsbackfillfill_river_data_gapspy) |

### `diagnostics/`

| Script | Purpose | Details |
|---|---|---|
| `check_river_data_availability.py` | Per-station river data coverage, freshness, and a safe start date for catch-up. | [reference](../docs/scripts-reference.md#scriptsdiagnosticscheck_river_data_availabilitypy) |
| `diagnose_forecast_data.py` | Forecast weather record counts and per-location date ranges. | [reference](../docs/scripts-reference.md#scriptsdiagnosticsdiagnose_forecast_datapy) |

### `maintenance/`

| Script | Purpose | Details |
|---|---|---|
| `clear_cache.py` | Deletes the local Open-Meteo HTTP cache (`.cache*`) so the next fetch is fresh. Least invasive fix for stale forecasts. | [reference](../docs/scripts-reference.md#scriptsmaintenanceclear_cachepy) |
| `force_refresh_forecast.py` | **Destructive.** Deletes all forecast weather rows, then re-fetches. Requires typing `yes`. Last resort. | [reference](../docs/scripts-reference.md#scriptsmaintenanceforce_refresh_forecastpy) |
| `remove_duplicate_historical_weather.py` | Removes duplicate `(location_name, date)` rows. Run before applying `sql/add_historical_weather_unique_constraint.sql`. Supports `--dry-run`. | script header |

### `legacy/`

| Script | Purpose | Details |
|---|---|---|
| `amadeus_saadaal_flood_forecaster.sh` | The original fail-fast orchestrator (`set -euo pipefail`, no retries). Same pipeline as the production script, but the first failure ends the run. | [reference](../docs/scripts-reference.md#scriptslegacyamadeus_saadaal_flood_forecastersh) |

## Conventions

- The shell orchestrators take `<REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]`, in that order.
- The Python helpers resolve the repository root from their own location, so they can be run from anywhere. Commands in
  the docs are written relative to the repository root, e.g. `python scripts/diagnostics/diagnose_forecast_data.py`.
- Both orchestrators parse `.env` line by line rather than sourcing it: the file is unquoted `KEY=value` for
  python-dotenv, so `source` would word-split and execute values containing spaces, `#` or `$`.
- Database access needs `DB_HOST` and `POSTGRES_PASSWORD` in the environment. There is no default host.

## Adding a script

Put it in the folder matching its purpose, never at the root — the root is reserved for the production orchestrator.
If it is a Python helper, resolve the repository root with `Path(__file__).parents[2]` to match the others.
Add a row to the table above, and a section in
[docs/scripts-reference.md](../docs/scripts-reference.md) if it needs more than one line of explanation.
