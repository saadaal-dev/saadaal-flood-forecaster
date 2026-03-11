# Saadaal Flood Forecaster — Pipeline Overview

## How the pipeline works

The pipeline runs on a **daily cron schedule** and has 4 sequential phases.

---

## Phase 1 — Data Ingestion

Two independent data sources are fetched and stored in PostgreSQL:

### 1a. River Level Data (SWALIM HTML scrape)

- CLI command: `flood-cli data-ingestion fetch-river-data` — **runs automatically every day**
- Source: **SWALIM website** (`https://frrims.faoswalim.org/rivers/levels`) — HTML table scrape
- Returns **only the most recent reading per station** (1 row × 5 stations): Belet Weyne, Bulo Burti, Jowhar, Dollow,
  Luuq
- ⚠️ **Known issue**: if SWALIM hasn't updated the page yet, or the cron misses a run, that day's reading is *
  *permanently lost** — there is no backfill from this source
- Data is stored in `flood_forecaster.historical_river_level` (deduplication by `location_name + date`)

### 1b. Weather Data (Open-Meteo)

- Source: **Open-Meteo API**
- Two types fetched:
    - **Historical weather** (`fetch-openmeteo historical`): past observed daily precipitation for each station location
    - **Forecast weather** (`fetch-openmeteo forecast`): 16-day ahead daily forecast — **CRITICAL**: if stale (< 5 days
      ahead), pipeline aborts
- Variables: `precipitation_sum`, `precipitation_hours`, `temperature_2m_max/min`, etc.
- Stored in `flood_forecaster.historical_weather` and `flood_forecaster.forecast_weather`

---

## Phase 2 — ML Inference

Run **per station** using model `Prophet_001` with `forecast_days=7`.

### Preprocessing (`preprocess_diff`)

Builds a feature matrix by combining:

- **River lag features**: river levels at lags [1, 3, 7, 14] days ago
- **Weather lag features**: precipitation at lags [1, 3, 7, 14] days ago
- **Weather forecast features**: precipitation forecasts for [today, +2, +6] days ahead
- **Seasonal features**: `month_sin/cos`, `dayofyear_sin/cos`
- **Target (y)**: `level_diff = level__m - lag1_level__m` (day-over-day change)

### Inference

- Model loaded from `models/Prophet_001/`
- Predicts the **river level 7 days ahead** for each station
- Results stored via **UPSERT** in `flood_forecaster.predicted_river_level` (constraint:
  `location_name + date + ml_model_name`)

---

## Phase 3 — Risk Assessment

For each station, compares the predicted `level_m` against **static thresholds** (loaded from
`data/static/river_stations_metadata.csv`):

| Risk Level | Condition                                       |
|------------|-------------------------------------------------|
| `low`      | `level_m < moderate_threshold`                  |
| `moderate` | `moderate_threshold ≤ level_m < high_threshold` |
| `high`     | `high_threshold ≤ level_m < full_threshold`     |
| `full`     | `level_m ≥ full_threshold`                      |

Updates the `risk_level` column on `predicted_river_level` rows.

---

## Phase 4 — Alerting

- Queries the latest predictions + risk levels
- Renders an **HTML email** from a template (`alert_template.html`)
- Sends via **Mailjet API** to configured recipients

---

## Full Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CRON TRIGGER (daily)                                 │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │         PHASE 1: DATA INGESTION     │
              └─────────────────┬──────────────────┘
                                │
           ┌────────────────────┼───────────────────────┐
           │                    │                        │
           ▼                    ▼                        ▼
  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐
  │  SWALIM         │  │  Open-Meteo      │  │  Open-Meteo        │
  │  River Levels   │  │  Historical Wx   │  │  Forecast Wx       │
  │                 │  │                  │  │  (16-day ahead)    │
  │ HTML scrape     │  │ • precipitation  │  │ • precipitation    │
  │ (latest 1 row   │  │ • temperature    │  │ • temperature      │
  │  per station)   │  │                  │  │ ⚠️ CRITICAL: if   │
  │                 │  │                  │  │   stale → ABORT   │
  └────────┬────────┘  └────────┬─────────┘  └─────────┬──────────┘
           │                    │                        │
           ▼                    ▼                        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                      PostgreSQL Database                        │
  │                                                                 │
  │  flood_forecaster.historical_river_level                        │
  │  flood_forecaster.historical_weather                            │
  │  flood_forecaster.forecast_weather                              │
  └────────────────────────────┬────────────────────────────────────┘
                               │
              ┌────────────────▼───────────────────┐
              │       PHASE 2: ML INFERENCE         │
              │   (per station × 5 stations)        │
              └────────────────┬───────────────────┘
                               │
           ┌───────────────────┼──────────────────────┐
           │                   │                       │
           ▼                   ▼                       ▼
  ┌─────────────────┐ ┌─────────────────┐   ┌──────────────────────┐
  │ Preprocess      │ │ Load Model      │   │ Store Prediction     │
  │                 │ │                 │   │                      │
  │ • River lags    │ │ Prophet_001     │   │ predicted_river_level│
  │   [1,3,7,14d]   │ │ (from /models/) │   │ (UPSERT by location  │
  │ • Weather lags  │ │                 │   │  + date + model)     │
  │   [1,3,7,14d]   │ │ → predict 7d   │   │                      │
  │ • Wx forecast   │ │   ahead         │   │ level_m, forecast_   │
  │   [today,+2,+6] │ │                 │   │ days=7               │
  │ • Seasonal feats│ └────────┬────────┘   └──────────────────────┘
  └─────────────────┘          │
                               └──────────────────────────────┐
                                                              │
              ┌───────────────────────────────────────────────▼──┐
              │           PHASE 3: RISK ASSESSMENT               │
              │                                                   │
              │  Per station, compare predicted level_m vs        │
              │  static thresholds (from CSV):                    │
              │                                                   │
              │    level_m < moderate_threshold  → "low"          │
              │    level_m < high_threshold      → "moderate"     │
              │    level_m < full_threshold      → "high"         │
              │    level_m ≥ full_threshold      → "full"         │
              │                                                   │
              │  UPDATE predicted_river_level.risk_level          │
              └───────────────────────┬───────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────┐
              │             PHASE 4: ALERTING                     │
              │                                                   │
              │  Query predicted_river_level + risk_level         │
              │  → Render HTML email (alert_template.html)        │
              │  → Send via Mailjet API                           │
              └───────────────────────────────────────────────────┘
```

---

## SWALIM Data Issue — Root Cause

These issues affect the **daily HTML scrape** (`fetch-river-data`) which is the only river data source that runs
automatically.

### Issue 1 — Scrape returns only 1 row per station

`fetch_latest_river_data` scrapes the summary table (`df.head(7)`) — **only the latest observation per station**. If the
cron misses a run, or SWALIM's website hasn't updated yet, that day is **permanently skipped** with no warning.

### Issue 2 — Leap year edge case (chart API)

When using the chart API for manual backfills, dates like `29-02` in a non-leap year are silently `continue`d (skipped).
No warning is emitted.

### Impact on the ML model

The `preprocess_diff` function uses river lags [1, 3, 7, 14 days]. Any gap in `historical_river_level` produces `NaN`
lag features, which can cause inference failures or degrade prediction quality for affected stations.

---

## Manual River Data Tools (not part of the daily pipeline)

When the daily scrape misses days or the DB has gaps, three CLI commands and a dedicated script exist to repair them.
They are **never called by the cron**.

See **[SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md)** for full details on:

- `backfill_river_data_from_swalim.py` — interactive script that fetches the full history from the SWALIM chart API and
  loads it into the DB
- `fill_river_data_gaps.py` — fills gaps from the internal `public.station_river_data` table (faster, no external call)
- `check_river_data_availability.py` — shows current data coverage and recommends a safe catchup start date
- Typical gap-filling workflow (check → fill → verify → catchup)

