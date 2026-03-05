## Sensor Readings Integration

`sensor_readings` lives in the `public` schema (owned by the Shaqodoon mobile app). The flood
forecaster reads from it but never writes to it.

### Table schema

| Column | Type | Notes |
|--------|------|-------|
| `id` | integer PK | |
| `station_id` | varchar | Matches `sensor` column in `data/static/sensor-stations.csv` |
| `sensor_id` | integer | Numeric sensor index on the device |
| `sensor_meaning` | varchar | E.g. `"Rainfall"`, `"River Level"` — used to filter rows |
| `reading_ts` | timestamp | Primary time dimension for queries |
| `value` | varchar | Raw string; sentinel values (`---`, `-999.99`, `0`, …) are cleaned |
| `original_date` | date | Device-local date (informational only) |
| `original_time` | time | Device-local time (informational only) |
| `firmware` | varchar | Device firmware version |
| `ingested_at` | timestamp | When the Shaqodoon app wrote the row to the DB |

### ORM & Pandera models

Defined in `src/flood_forecaster/data_model/sensor_readings.py`:

- **`SensorReading`** — SQLAlchemy ORM mapping to `public.sensor_readings`.
- **`SensorReadingDataFrameSchema`** — Pandera schema for the raw query result (`strict=False`).
- **`SensorRainfallDataFrameSchema`** — Pandera schema for the daily-aggregated rainfall
  DataFrame (`columns: location, date, precipitation_sum, precipitation_hours`).

### Station → location mapping

Because `sensor_readings.station_id` does not directly match the pipeline's `location_name`
strings, the mapping is computed at query time using the **haversine nearest-neighbour**
algorithm (`src/flood_forecaster/utils/geo.py`):

1. Load `data/static/sensor-stations.csv` (`sensor, label, latitude, longitude, type`).
2. Load `data/static/forecast-locations.csv` (pipeline location labels with coordinates).
3. For each sensor station, find the nearest forecast location within
   `sensor_max_distance_km` (default 50 km).
4. Build a `dict[station_id → location_label]` used to annotate sensor query results.

### Inference pipeline

When `[data.sensor] use_sensor_rainfall = True` in `config.ini`, `api.infer()` calls
`load_inference_sensor_rainfall()` alongside `load_inference_weather()` and coalesces
sensor values over Open-Meteo via `DataFrame.combine_first()` (sensor data takes priority).
The feature flag is **off by default** to preserve existing behaviour.

### CLI — compare sensor vs Open-Meteo

```bash
flood-cli database-model compare-sensor-weather \
  --location lower_shabelle__afgooye \
  --date-from 2025-10-01 \
  --date-to 2025-10-31 \
  [--output comparison.csv]
```

Prints a side-by-side table of `sensor_precip_mm`, `openmeteo_precip_mm`, and `delta_mm`
for each `(location, date)` pair. Rows with no sensor reading show `N/A`.
Pass `--output <path>` to save the result as a CSV file.
