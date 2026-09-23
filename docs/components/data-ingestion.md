# Data ingestion

## Responsibility

The ingestion component acquires daily weather and river-level inputs, normalizes them into Pandas data frames/ORM
objects, and persists them to PostgreSQL or CSV. It does not train models or calculate flood risk.

## Inputs and outputs

| Source                   | Input scope                                                        | Transformation                                                                           | Destination                                                    |
|--------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Open-Meteo archive API   | Locations in `data/static/forecast-locations.csv`                  | Parse daily temperature, precipitation, rain, and precipitation hours                    | `flood_forecaster.historical_weather`                          |
| Open-Meteo forecast API  | Same configured locations; requests 16 forecast days               | Parse historical fields plus precipitation probability and maximum wind speed            | `flood_forecaster.forecast_weather`                            |
| SWALIM levels page       | First seven HTML table rows, filtered to names in station metadata | Parse observed level and `DD-MM-YYYY` date                                               | `flood_forecaster.historical_river_level`                      |
| SNRFA/SWALIM CSV exports | One station per command                                            | Normalize columns and reconcile by station/date                                          | `flood_forecaster.historical_river_level`                      |
| SWALIM chart endpoint    | One station per command                                            | Convert chart JSON to a CSV-compatible frame                                             | Output CSV; not inserted by this command                       |
| Shaqodoon sensors        | `public.sensor_readings`                                           | Clean and aggregate rainfall by day, then map sensor station to nearest weather location | Read directly during inference; source table is never modified |

## Weather flow

1. `create_openmeteo_client()` builds a `requests-cache` client backed by `.cache`, with a one-hour expiry and five HTTP
   retries.
2. Location labels/coordinates are loaded from the configured weather-location CSV.
3. One multi-location API request is parsed into daily records.
4. Forecast and historical records are upserted on `(location_name, date)` when database persistence is enabled.
5. Historical ingestion runs duplicate cleanup after the fetch; `--dry-run` reports duplicates without deleting them.

Set `[data.ingestion] use_database = False` to write timestamped CSV files below `[openmeteo] store_base_path`. This
switch is separate from `[data] data_source`, which controls where modelling loaders read data.

## River flow

The daily command scrapes the SWALIM HTML table and inserts only station/date combinations not already present. When an
existing value differs, it logs a warning but does not update the stored row. Historical backfill can use SNRFA/SWALIM
CSV exports or the SWALIM chart helper commands.

Unlike weather tables, `historical_river_level` has no database unique constraint in the bootstrap schema. Normal
ingestion prevents duplicates in application code, but direct inserts do not.

### Historical river-gap recovery

Prediction catch-up requires continuous river-level inputs. For deployments that also expose
`public.station_river_data`, the maintenance scripts can recover missing dates by mapping
`river_station_metadata.swalim_internal_id` to the source table's `station_id`:

```bash
# Inspect available ranges and gaps
python scripts/check_river_data_availability.py

# After reviewing the script source, run it interactively
python scripts/fill_river_data_gaps.py

# Verify continuity before generating missing predictions
python scripts/check_river_data_availability.py
python scripts/catchup_missing_predictions.py
```

Gap filling reads `public.station_river_data` and inserts missing rows into `flood_forecaster.historical_river_level`.
It requires populated `swalim_internal_id` values and database permission to read the external source table. Source data
may not cover every requested date, so use the verified common date range when running prediction catch-up. These
scripts mutate production data; inspect their output and take an appropriate backup first.

## Optional sensor rainfall

Sensor data is an inference-time overlay, not part of the daily ingestion phase. When
`[data.sensor] use_sensor_rainfall = True`:

1. Rows matching the configured rainfall meaning are read from `public.sensor_readings`.
2. Invalid raw strings are removed and readings are aggregated by calendar day.
3. Sensor station coordinates from `data/static/sensor-stations.csv` are mapped to the nearest configured forecast
   location within `sensor_max_distance_km`.
4. **SENS-002:** The inference loader completes the sensor date window using forward-fill and then zero-fill before
   sensor values take priority in the merge. Only an entirely empty sensor result leaves Open-Meteo unchanged.

See the [field sensors quick guide](../sensors-quick-guide.md) for current locations and production status,
and [field sensor data integration](../sensor-readings-integration.md) for schema, cleaning, comparison, and
limitations.

## Failure behavior

- API/library exceptions propagate from weather commands so the orchestrator can retry them.
- The SWALIM latest-level fetch catches request failures and returns an empty list; the command reports that no new data
  was fetched.
- Production retries each ingestion command up to three times. Historical weather and river failures fall back to stored
  data.
- Forecast failure is critical unless the maximum stored forecast date is at least five days after the current date.
- **SEC-001:** Open-Meteo and SWALIM requests currently disable TLS certificate verification.

Priorities and completion criteria for these gaps are maintained in
the [improvement backlog](../improvement-backlog.md).

## Useful commands

```bash
flood-cli data-ingestion fetch-openmeteo historical
flood-cli data-ingestion fetch-openmeteo forecast
flood-cli data-ingestion fetch-river-data
python scripts/diagnose_forecast_data.py
python scripts/clear_cache.py
```

## Key implementation paths

- Weather: `src/flood_forecaster/data_ingestion/openmeteo/`
- River data: `src/flood_forecaster/data_ingestion/swalim/river_level_api.py`
- Database/CSV loaders: `src/flood_forecaster/data_ingestion/load.py`
- Sensor model and mapping: `src/flood_forecaster/data_model/sensor_readings.py`, `src/flood_forecaster/utils/geo.py`
