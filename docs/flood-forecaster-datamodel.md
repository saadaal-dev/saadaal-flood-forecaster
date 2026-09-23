# Flood forecaster data model

The application owns five tables in PostgreSQL schema `flood_forecaster`. **DB-003:** relationships below are conceptual
joins; `sql/database_bootstrap.sql` defines uniqueness constraints but no foreign keys.

```mermaid
erDiagram
    FORECAST_WEATHER {
        serial id PK
        varchar location_name UK
        timestamp date UK
        float temperature_2m_max
        float temperature_2m_min
        float precipitation_sum
        float rain_sum
        float precipitation_hours
        float precipitation_probability_max
        float wind_speed_10m_max
    }
    HISTORICAL_RIVER_LEVEL {
        serial id PK
        varchar location_name
        date date
        float level_m
    }
    HISTORICAL_WEATHER {
        serial id PK
        varchar location_name UK
        timestamp date UK
        float temperature_2m_max
        float temperature_2m_min
        float precipitation_sum
        float rain_sum
        float precipitation_hours
    }
    PREDICTED_RIVER_LEVEL {
        serial id PK
        varchar location_name UK
        date date UK
        float level_m
        varchar station_number
        varchar ml_model_name UK
        int forecast_days
        varchar risk_level
        timestamp created_at
        timestamp updated_at
    }
    RIVER_STATION_METADATA {
        varchar station_number
        varchar station_name UK
        varchar river_name
        varchar region
        varchar status
        date first_date
        float latitude
        float longitude
        float moderate_flood_risk_m
        float high_flood_risk_m
        float bankfull_m
        float maximum_depth_m
        float maximum_width_m
        float maximum_flow_m
        float elevation
        int swalim_internal_id
    }

    RIVER_STATION_METADATA ||..o{ HISTORICAL_RIVER_LEVEL : "station name"
    RIVER_STATION_METADATA ||..o{ PREDICTED_RIVER_LEVEL : "station name"
    HISTORICAL_RIVER_LEVEL }o..o{ PREDICTED_RIVER_LEVEL : "river lag features"
    HISTORICAL_WEATHER }o..o{ PREDICTED_RIVER_LEVEL : "past weather features"
    FORECAST_WEATHER }o..o{ PREDICTED_RIVER_LEVEL : "future weather features"
```

## Constraints and semantics

- `historical_weather`: unique `(location_name, date)`.
- `forecast_weather`: unique `(location_name, date)`.
- `predicted_river_level`: unique `(location_name, date, ml_model_name)`.
- `river_station_metadata`: unique `station_name`.
- **DATA-005:** `historical_river_level` has no uniqueness constraint; ingestion prevents duplicates in application
  code.
- **RISK-002:** `predicted_river_level.date` is the inference reference date. The target date is
  `date + forecast_days - 1`.
- Risk labels are lowercase `low`, `moderate`, `high`, or `full`.
- Optional IoT data is externally owned in `public.sensor_readings`, not this schema.

See [Database and data model](components/database.md) for lifecycle, ownership, views, and setup commands.
Implementation plans and completion criteria are maintained in the [improvement backlog](improvement-backlog.md).
