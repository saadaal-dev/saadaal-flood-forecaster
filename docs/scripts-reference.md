# Scripts Reference Guide

This document provides a comprehensive overview of all utility scripts in the `scripts/` directory. These scripts
support deployment, automation, maintenance, and troubleshooting of the Flood Forecaster system.

---

## 📋 Table of Contents

- [Directory Layout](#directory-layout)
- [Pipeline Scripts](#pipeline-scripts)
- [Maintenance & Troubleshooting Scripts](#maintenance--troubleshooting-scripts)
- [Script Usage Examples](#script-usage-examples)

---

## Directory Layout

The scripts are grouped by purpose, and the only file at the root of `scripts/` is the orchestrator the production cron
job runs. The folder map is maintained in **[scripts/README.md](../scripts/README.md#layout)** — it lives next to the
scripts so it cannot drift from them. This document is the detailed per-script reference.

Python helpers resolve the repository root from their own location, so they can be run from anywhere. Commands in this
guide are written relative to the repository root.

---

## Pipeline Scripts

### `scripts/amadeus_saadaal_flood_forecaster_resilient.sh`

**Purpose**: The production pipeline script for automated flood forecasting. This is the one the container cron job
runs.

**Description**: Orchestrates the complete pipeline — data ingestion, model inference for every configured station, risk
assessment, alert dispatch — and degrades gracefully instead of failing fast. Ingestion steps are retried with
exponential backoff, a single station's inference failure does not stop the others, and the run only aborts outright
when forecast weather is missing or too stale for predictions to mean anything.

**Usage**:

```bash
./scripts/amadeus_saadaal_flood_forecaster_resilient.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
```

**Parameters**:

- `REPOSITORY_ROOT_PATH`: Absolute path to the flood forecaster repository
- `VENV_PATH`: Path to the Python virtual environment
- `--windows` (optional): Flag to indicate Windows environment

**Key Features**:

- Activates the virtual environment and exports the variables from `.env`
- Fails immediately with an explicit message if `DB_HOST` or `POSTGRES_PASSWORD` are missing
- Retries each ingestion step up to 3 times with exponential backoff
- Continues past a failed station so the remaining stations still get predictions
- Colored output for success (green), failure (red), and warnings (yellow)
- Prints a summary of successes and failures at the end

**Exit Behavior**: `0` when everything succeeded, `2` on partial success, `1` when the run failed completely or was
aborted for missing configuration or stale forecast data.

**CRON Setup Example**:

```bash
# Run daily at 12:00 PM
0 12 * * * /root/Amadeus/saadaal-flood-forecaster/scripts/amadeus_saadaal_flood_forecaster_resilient.sh /root/Amadeus/saadaal-flood-forecaster /root/Amadeus/saadaal-flood-forecaster/.venv >> /root/Amadeus/saadaal-flood-forecaster/logs/logs_amadeus_saadaal_flood_forecaster.log 2>&1
```

---

### `scripts/legacy/amadeus_saadaal_flood_forecaster.sh`

**Purpose**: The original fail-fast orchestrator. Superseded by the resilient script above and kept for reference.

**Description**: Runs exactly the same sequence of `flood-cli` commands as the production script, but under
`set -euo pipefail` and with no retries, so the first failure ends the run. A transient Open-Meteo timeout during
ingestion therefore costs the whole day's inference, risk assessment and alerting — which is why production no longer
uses it.

**Usage**:

```bash
./scripts/legacy/amadeus_saadaal_flood_forecaster.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
```

**Parameters**: Same as the resilient script.

**Exit Behavior**: Fails fast on any error (`set -euo pipefail`)

**When to Use**: When you deliberately want the run to stop at the first error, for example while debugging a single
stage locally. For anything unattended, use the resilient script.

---

### `scripts/backfill/batch_infer_and_risk_assess.sh`

**Purpose**: Batch processing script for running inference and risk assessment across multiple stations.

**Description**: Processes all configured river stations sequentially, running ML inference and risk assessment for
each. Useful for manual batch operations or custom automation scenarios.

**Usage**:

```bash
./scripts/backfill/batch_infer_and_risk_assess.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
```

**Parameters**: Same as other automation scripts

**Configured Stations**:

- Belet Weyne
- Bulo Burti
- Jowhar
- Dollow
- Luuq

**Key Features**:

- Fetches latest weather and river data
- Runs inference for all stations in sequence
- Performs risk assessment after each inference
- Comprehensive logging of all operations

---

## Maintenance & Troubleshooting Scripts

### `scripts/backfill/catchup_missing_predictions.py`

**Purpose**: Backfill missing river level predictions when the automated pipeline has failed.

**Description**: Analyzes all configured stations (from metadata) and the `predicted_river_level` table to identify *
*ALL gaps and holes** in predictions. Prompts you to specify a start date, then automatically runs inference for all
missing dates to catch up. **Detects gaps in the middle of existing data**, not just missing dates at the end. Uses the
same `flood-cli` commands as `batch_infer_and_risk_assess.sh` but only for the specific missing date ranges per
location. **Works even for locations with no existing predictions** in the database. This is essential for maintaining
data continuity after system downtime or pipeline failures.

**Usage**:

```bash
python scripts/backfill/catchup_missing_predictions.py
```

**Where to Run**:
This script connects to the PostgreSQL database using `dbname`/`user`/`port` from `config/config.ini` and the host from
the `DB_HOST` environment variable. The host was hardcoded in `config.ini` until March 2026; it is now env-only, so
`DB_HOST` must be set wherever the script runs.
You can run it from:

- ✅ **Inside the Docker container**: Most common for production
  ```bash
  docker exec -it <container-id> bash
  cd /root/Amadeus/saadaal-flood-forecaster
  python scripts/backfill/catchup_missing_predictions.py
  ```
- ✅ **Outside the container**: If you have network access to the database server
    - Requires `POSTGRES_PASSWORD` environment variable set in `.env` file
    - Requires network connectivity to the database host (port 5432)
    - Requires `flood-cli` to be installed and in PATH

**What It Does**:

1. Loads all configured stations from metadata (not just those with existing predictions)
2. **Prompts you to select which stations to process** (can select specific stations or all)
3. **Prompts you to enter a start date** (e.g., 2024-01-01) - no hardcoded dates!
4. For each selected location, **identifies ALL missing dates in the date range** by checking what actually exists in
   the database
5. **Detects gaps/holes in the middle of existing data**, not just missing dates at the end
6. Displays a summary showing multiple gaps if they exist (e.g., "3 gaps detected: 2024-11-01 to 11-05, 2024-11-20,
   2024-12-01 to 12-03")
7. Prompts for confirmation before proceeding
8. **Runs data ingestion** (fetches historical weather, forecast weather, and river data) - just like
   `batch_infer_and_risk_assess.sh`
9. Runs ML inference for each missing date and location (uses `flood-cli ml infer`)
10. Updates risk assessments after catching up (uses `flood-cli risk-assessment`)
11. Provides detailed progress and summary statistics

**Relationship to `batch_infer_and_risk_assess.sh`**:
This script uses the **exact same approach** as the batch script:

- **Runs data ingestion first** (fetch historical weather, forecast, and river data)
- **Uses the same CLI commands** (`flood-cli ml infer` and `flood-cli risk-assessment`)

But it's smarter in how it determines what to process:

- **Prompts you for the start date** (flexible, not hardcoded)
- **Only processes missing dates** for each location (skips dates that already have predictions)
- **Works for locations without any data** (creates predictions from scratch)
- **Skips unsupported stations** automatically

**Safety Features**:

- Interactive confirmation required before processing
- Shows detailed analysis before making changes
- **Automatically detects and skips unsupported stations** (e.g., stations without trained ML models)
- Tracks success/failure counts for each location
- Validates predictions were created successfully
- Provides actionable troubleshooting guidance

**When to Use**:

- After extended system downtime (server offline, service stopped)
- When automated CRON jobs have failed for multiple days
- After fixing issues that prevented predictions from running
- To verify and fill any gaps in the prediction timeline
- During system recovery after database issues
- **When setting up predictions for new locations** that have no historical predictions yet
- **When you want to backfill from a specific date** without hardcoding it in a script
- **When you only need to catch up specific stations** (saves time by skipping others)

**Output Example**:

```
================================================================================
CATCHUP MISSING PREDICTIONS
================================================================================
Current time: 2025-12-04 14:30:00

📍 Found 5 configured stations:
   Belet Weyne, Bulo Burti, Jowhar, Dollow, Luuq

📍 Select stations to process:

   Available stations:
     1. Belet Weyne
     2. Bulo Burti
     3. Jowhar
     4. Dollow
     5. Luuq

   Options:
     - Enter numbers separated by commas (e.g., 1,3,5)
     - Enter 'all' to process all stations
     - Enter station names separated by commas

   Your selection: 1,2
   Selected: Belet Weyne, Bulo Burti

🗓️  From which date should we check for missing predictions?
   (Format: YYYY-MM-DD, e.g., 2024-01-01)
   Press Enter to use default: 2024-01-01
   Start date: 2024-11-01
   Using: 2024-11-01
   End date: 2025-12-04 (today)

Step 1: Analyzing missing predictions by location
--------------------------------------------------------------------------------
📍 Belet Weyne
   Last prediction: 2025-12-04
   Missing days: 12
   ⚠️  3 gap(s) detected:
      - 2024-11-01 to 2024-11-05 (5 days)
      - 2024-11-20 (1 day)
      - 2024-12-01 to 2024-12-03 (3 days)

📍 Bulo Burti
   Last prediction: 2025-12-04
   Missing days: 4
   Date range: 2025-12-01 to 2025-12-04

📍 Jowhar
   Last prediction: None (no predictions in DB)
   Will create predictions from: 2024-11-01
   Missing days: 34
   Date range: 2024-11-01 to 2025-12-04

...

📊 Summary: 68 missing predictions across 2 location(s)

⚠️  This will run inference for all missing dates.
   Depending on the number of missing dates, this may take a while.

Do you want to proceed? (yes/no): yes

Step 2: Fetching latest data (historical weather, forecast, river levels)
--------------------------------------------------------------------------------
Running data ingestion...
  Running: flood-cli data-ingestion fetch-openmeteo historical
  ✅ fetch-openmeteo historical completed
  Running: flood-cli data-ingestion fetch-openmeteo forecast
  ✅ fetch-openmeteo forecast completed
  Running: flood-cli data-ingestion fetch-river-data
  ✅ fetch-river-data completed

Step 3: Running inference for missing dates
--------------------------------------------------------------------------------
✓ Luuq: Up to date

📍 Belet Weyne: Checking if station is supported... ✅ Supported
   Processing 34 missing dates...
  Processing 2024-11-01... ✅
  Processing 2024-11-02... ✅
  ...
  Processing 2025-12-04... ✅
  Location summary: 34 successful, 0 failed

📍 Bardheere: Checking if station is supported... ⚠️  SKIPPED
   Reason: Invalid value: Station Bardheere not supported. Supported stations: ['Belet Weyne', 'Bulo Burti', 'Jowhar', 'Dollow', 'Luuq']
   15 dates will not be processed for this station

...

================================================================================
Step 4: Updating risk assessments
--------------------------------------------------------------------------------
✅ Risk assessments updated successfully

================================================================================
CATCHUP COMPLETE
================================================================================
Total missing predictions found: 91
Successfully processed: 88
Failed: 0
Unsupported stations (skipped): 1
   Bardheere

ℹ️  Some stations were skipped because they are not supported by the ML model:
   - Bardheere

   To support these stations, you need to:
   - Train ML models for these locations
   - Ensure model files exist in the models/ directory

✅ All supported stations have been processed successfully!
   (Some stations were skipped - see above)
================================================================================
```

**Prerequisites**:

- **Database Access**:
    - `dbname`, `user` and `port` configured in `config/config.ini`
    - `DB_HOST` and `POSTGRES_PASSWORD` environment variables set (loaded from `.env` file). There is no default host -
      a missing `DB_HOST` raises `ValueError: DB_HOST environment variable not set.`
    - Network connectivity to the database host on port `5432`
- **Environment**:
    - `flood-cli` command available in PATH (installed via `install.sh`)
    - Python virtual environment activated (if running outside container)
- **Data Requirements**:
    - Historical weather data must be available for the missing dates
  - **Historical river level data must exist in the database for the requested dates**
    - ML model files must exist for all locations (`models/` directory)

**⚠️ Important Limitation - River Data Availability**:

The script requires **historical river level data** to exist in the database for the dates you're catching up. This
means:

- ✅ **Works well for recent dates** (last few weeks/months where river data exists)
- ❌ **May fail for very old dates** (e.g., 2024-01-01) if river data wasn't collected then
- ❌ **Will fail for locations without any river data** in the database

**Why?** The ML models use historical river levels as input features. If there's no river data for a location/date,
inference cannot proceed.

**Solution if you get "Missing river level data" error**:

1. Check what river data exists:
   `SELECT DISTINCT location_name, MIN(date), MAX(date) FROM historical_river_level GROUP BY location_name;`
2. Choose a start date that's within the available river data range
3. For older dates without river data, you cannot create predictions (no input data available)

**Troubleshooting**:

**Error: "Missing river level data for locations"**

```
ValueError: Missing river level data for locations: {'Belet Weyne'}
```

**Cause**: The database doesn't have historical river level data for the location/dates you're trying to process.

**Solutions**:

1. **Check available river data** using the helper script:
   ```bash
   python scripts/diagnostics/check_river_data_availability.py
   ```
   This will show you:
    - Date range of available river data per location
    - Safe start date where all locations have data
    - Locations with limited or outdated data

   Or check directly in the database. Count distinct dates, not rows, so that coverage is not over-reported:
   ```sql
   SELECT location_name, MIN(date) as first_date, MAX(date) as last_date, COUNT(DISTINCT date) as days
   FROM flood_forecaster.historical_river_level
   GROUP BY location_name
   ORDER BY location_name;
   ```

2. **Adjust your start date**: Choose a date within the available data range
    - If river data starts at 2024-11-01, don't try to catch up from 2024-01-01
    - Use a start date that's within the MIN/MAX date range shown above

3. **Accept the limitation**: You cannot create predictions for dates/locations without river data
    - The ML model requires river levels as input
    - No river data = no predictions possible

**Other issues**:

- **Weather data missing**: `flood-cli data-ingestion fetch-openmeteo historical`
- **Model files missing**: Check `models/` directory for `Preprocessor_001-f7-Prophet_001-{Location}.json`
- **Database connectivity**: Verify `POSTGRES_PASSWORD` is set and connection works
- **Station not supported**: Script will automatically skip (see output)

---

### `scripts/backfill/fill_river_data_gaps.py`

**Purpose**: Fill gaps in `flood_forecaster.historical_river_level`, from SWALIM's chart API or from
`public.station_river_data`.

**Description**: Finds dates with no usable reading for each station inside a window, fetches what the chosen source can
supply, and inserts the missing rows. Dry run by default: nothing is written unless `--apply` is passed.

**Usage**:

```bash
# What is missing for Jowhar, up to today (writes nothing)
python scripts/backfill/fill_river_data_gaps.py --station Jowhar

# Repair a known outage window
python scripts/backfill/fill_river_data_gaps.py --station Jowhar --from 2026-05-12 --apply

# Every station, bounded window, no prompt
python scripts/backfill/fill_river_data_gaps.py --from 2026-01-01 --apply --yes

# Compare what the fallback source could offer
python scripts/backfill/fill_river_data_gaps.py --station Jowhar --source public-schema

# Backfill since May 2026 AND replace readings that disagree with the source.
# Inspect the "old -> new" list first, then apply.
python scripts/backfill/fill_river_data_gaps.py --from 2026-05-01 --overwrite
python scripts/backfill/fill_river_data_gaps.py --from 2026-05-01 --overwrite --apply
```

**Options**:

| Option | Default | Meaning |
|---|---|---|
| `--station NAME` | all mapped stations | Station to process; repeatable |
| `--from YYYY-MM-DD` | station's earliest stored row | Start of the window |
| `--to YYYY-MM-DD` | **today** | End of the window |
| `--source` | `chart-api` | `chart-api` or `public-schema` |
| `--overwrite` | off | Also replace stored readings that disagree with the source, and repair NULL-level rows in place. **Destructive** |
| `--apply` | off | Actually write; without it the run is read-only |
| `--yes` | off | Skip the confirmation prompt when applying |
| `--config PATH` | `<repo root>/config/config.ini` | Alternate configuration file |
| `--max-listed N` | 12 | How many individual dates to print per station |

**What gets written**:

Without `--overwrite` the script is insert-only. It fills dates that hold no usable reading and leaves everything else
alone, even if the source now disagrees with what is stored. Upstream corrections are not always improvements, so
rewriting stored history is not the default.

`--overwrite` adds replacement. Per date in the window:

| Stored state | Source has a reading | Action |
|---|---|---|
| no row | yes | `INSERT` |
| row with `level_m` NULL | yes | `UPDATE` that row |
| row with a different `level_m` | yes | `UPDATE` that row |
| row with the same `level_m` | yes | left alone |
| any | no | left alone, counted as "not in source" |

"Different" means the values differ by more than `LEVEL_TOLERANCE_M` (0.001 m), so floating-point representation noise
is not mistaken for a correction. The dry run prints each replacement as `date: old -> new`, so you can review exactly
what would change before passing `--apply`.

The NULL case is worth calling out. A NULL-level row holds no usable reading, so both modes repair it by filling that row
in place and neither creates a second row for the date. `historical_river_level` is unique on `(location_name, date)`
(DATA-005), so a duplicate insert is rejected by the database rather than silently accepted as it was before. Filling a
placeholder does not count as rewriting history, which is why it happens without `--overwrite`; replacing a date that
already holds a real reading still requires that flag. Against a database where duplicate rows still exist for a date,
`--overwrite` converges all of them onto the source value.

⚠️ `--overwrite` is the only mode that can destroy a reading, and the previous value is not recorded anywhere. Take a
database snapshot first (`db-snapshot/01-dump.sh`). Overwritten readings are model inputs, so any prediction already
built from them is stale: re-run `scripts/backfill/catchup_missing_predictions.py` afterwards.

**Sources**:

- **`chart-api`** (default) — SWALIM's `/rivers/graph` endpoint, addressed per station by id. Returns the current year
  plus the previous year in one call, so it can repair long gaps, and it is immune to the HTML row-position failure in
  backlog item DATA-004. Measured on 2026-09-23 it covered 134/134 days of the Jowhar outage.
- **`public-schema`** — `public.station_river_data`, joined through `river_station_metadata.swalim_internal_id`. This
  table is written by a host cron outside this project's control and is less complete: 124/134 days for the same window.
  Treat it as a fallback and a cross-check, not a primary source. See RISK-005.

**How It Works**:

1. Loads the station mapping from `river_station_metadata` (`station_name` → `swalim_internal_id`)
2. Resolves a window per station; `--to` defaults to today so trailing gaps are visible
3. Lists dates with no non-NULL `level_m` in that window
4. Fetches candidate readings from the chosen source. Under `--overwrite` this happens even when there are no gaps,
   since a fully populated window can still hold readings that disagree with the source
5. Reports gaps, what is fillable, what would be replaced, and what the source lacks
6. On `--apply`, writes everything in a single transaction: inserts carry `ON CONFLICT DO NOTHING`, and updates are
   guarded by `level_m IS DISTINCT FROM :level` so re-running writes nothing and the reported counts are rows actually
   changed rather than rows examined

**When to Use**:

- When inference fails with `Missing river level data for locations: {...}`
- When a station's predictions have stopped while others continue
- After downtime that interrupted river data collection
- To audit coverage without changing anything (the default dry run)

**Prerequisites**:

- `river_station_metadata.swalim_internal_id` populated
- `POSTGRES_PASSWORD` and `DB_HOST` set in the environment
- Network access to `frrims.faoswalim.org` for `--source chart-api`
- Read access to `public.station_river_data` for `--source public-schema`

**Output Example**:

```
==============================================================================
FILL GAPS IN HISTORICAL RIVER LEVEL DATA
==============================================================================
Source : chart-api
Window : 2026-05-12 .. 2026-09-22
Mode   : DRY RUN - nothing will be written

Stations: Jowhar
------------------------------------------------------------------------------

📍 Jowhar  (SWALIM id 6)
   window 2026-05-12 .. 2026-09-22  (134 days)
   usable readings stored: 0
   ⚠️  missing: 134 day(s)
      2026-05-12, 2026-05-13, 2026-05-14 ... 2026-09-20, 2026-09-21, 2026-09-22
   source offers 134 reading(s) in window; 134 match a gap, 0 unavailable

==============================================================================
Gaps found          : 134
To insert           : 134
==============================================================================

Dry run. Re-run with --apply to write the changes above.
```

**Output example with `--overwrite`** (a populated window holding two disagreements):

```
Writes : INSERT gaps + OVERWRITE disagreeing readings
         ⚠️  --overwrite replaces stored readings; the previous values are not kept.

📍 Jowhar  (SWALIM id 6)
   window 2026-05-01 .. 2026-09-28  (151 days)
   usable readings stored: 149
   rows with a NULL level: 1
   ⚠️  missing: 2 day(s)
      2026-07-04, 2026-08-19
   source offers 151 reading(s) in window; 2 match a gap, 0 unavailable
   → 1 to insert, 3 to overwrite
      2026-07-04: NULL -> 1.12
      2026-08-11: 0.98 -> 1.05
      2026-09-02: 1.44 -> 1.41

==============================================================================
Gaps found          : 2
To insert           : 1
To overwrite        : 3
==============================================================================
```

**Safety**:

- Read-only unless `--apply` is given, and then it still prompts unless `--yes`
- Everything runs in one transaction, so a failure leaves nothing half-applied
- Insert and update counts come from `rowcount`, so the run reports what the database actually did
- Updates carry `level_m IS DISTINCT FROM :level`, so re-running the same repair writes nothing
- Without `--overwrite` no stored reading can be modified or removed; the worst case is an extra row
- A source failure is reported per station and does not abort the other stations

**Notes**:

- Rows with a NULL `level_m` count as gaps, because the loader drops NULL levels before building features. A NULL row
  would otherwise occupy the date and keep the gap permanently unfixable. Use `--overwrite` to repair such a row in
  place instead of inserting a second row for the same date.
- Two defects were fixed on 2026-09-24. The source query ordered by a column named `date`, which does not exist on
  `public.station_river_data` (it is `reading_date`); every fetch raised, the error was swallowed, and the script filled
  nothing. Separately, the gap search was bounded by `MAX(date)`, so a station that had stopped reporting appeared
  continuous and its trailing gap was invisible.

**Troubleshooting**:

- **"No station mapping found"**: check `swalim_internal_id` in `river_station_metadata`
- **"Unknown station(s)"**: the name must match `river_station_metadata.station_name`; available names are listed
- **"no existing rows; pass --from"**: the station has no data at all, so there is no natural window start
- **Gaps exist but the source has nothing**: try the other `--source`; if both are short, the reading was never published

---


---

### `scripts/diagnostics/check_river_data_availability.py`

**Purpose**: Check what historical river level data is available in the database.

**Description**: Displays statistics about available river data per location, helping you determine valid date ranges
for the catchup script. Essential for understanding what dates you can backfill.

**Usage**:

```bash
python scripts/diagnostics/check_river_data_availability.py
```

**What It Shows**:

- Total river level records in database
- Overall date range (earliest to latest)
- Per-location statistics (first date, last date, record count)
- Safe date range where ALL locations have data
- Locations with limited data (< 30 days)
- Locations with outdated data (> 7 days old)
- Recommended start date for catchup script

**When to Use**:

- **Before running catchup script** to determine valid start date
- When getting "Missing river level data" errors
- To verify river data collection is working
- To check data freshness

**Output Example**:

```
================================================================================
HISTORICAL RIVER LEVEL DATA AVAILABILITY
================================================================================

📊 Overall Statistics
--------------------------------------------------------------------------------
Total records: 1,234
Overall date range: 2024-10-15 to 2024-12-04

📍 Data Availability by Location
--------------------------------------------------------------------------------
Location                       First Date      Last Date       Records    Days      
--------------------------------------------------------------------------------
Belet Weyne                    2024-10-15      2024-12-04      245        51        
Bulo Burti                     2024-11-01      2024-12-04      102        34        
Dollow                         2024-10-15      2024-12-04      245        51        
Jowhar                         2024-10-20      2024-12-04      140        46        
Luuq                           2024-10-15      2024-12-04      245        51        

================================================================================
RECOMMENDATIONS FOR CATCHUP SCRIPT
================================================================================

✅ Safe Date Range (all locations have data):
   Start from: 2024-11-01 or later
   Up to: 2024-12-04 (or today if more recent)

💡 Usage Example:

   python scripts/backfill/catchup_missing_predictions.py
   # When prompted, enter start date: 2024-11-01

================================================================================
```

---

### `scripts/maintenance/clear_cache.py`

**Purpose**: Clear the requests cache to force fresh API data retrieval.

**Description**: Removes cached API responses that may contain stale weather forecast data. This script solves issues
where forecast data was cached indefinitely and never refreshed.

**Usage**:

```bash
python scripts/maintenance/clear_cache.py
```

**What It Does**:

- Locates all cache files (`.cache`, `.cache.sqlite`, etc.)
- Deletes cache files and reports the size cleared
- Provides confirmation of successful cleanup

**Cache Files Removed**:

- `.cache`
- `.cache.sqlite`
- `.cache.sqlite-shm`
- `.cache.sqlite-wal`

**When to Use**:

- Before running forecast ingestion after extended downtime
- When forecast data appears outdated
- After API configuration changes
- During troubleshooting of stale data issues

**Output Example**:

```
✅ Deleted: .cache.sqlite (1,234,567 bytes)
✅ Successfully cleared 4 cache file(s)
```

---

### `scripts/diagnostics/diagnose_forecast_data.py`

**Purpose**: Diagnostic tool to analyze forecast weather data in the database.

**Description**: Provides comprehensive statistics and insights about forecast data stored in the database. Helps
identify data gaps, date range issues, and location-specific problems.

**Usage**:

```bash
python scripts/diagnostics/diagnose_forecast_data.py
```

**Information Provided**:

- Total forecast weather records
- Date range of stored forecasts
- Per-location statistics (min/max dates, record counts)
- Current system time for context
- Data freshness indicators

**Output Example**:

```
================================================================================
FORECAST WEATHER DATA DIAGNOSTICS
================================================================================
Current time: 2025-12-03 14:30:00
Total forecast weather records in database: 350
Date range in database: 2025-12-01 to 2025-12-17

Data by location:
--------------------------------------------------------------------------------
Location                                 Min Date              Max Date              Count
--------------------------------------------------------------------------------
Belet Weyne                             2025-12-01            2025-12-17            70
Bulo Burti                              2025-12-01            2025-12-17            70
...
```

**When to Use**:

- Troubleshooting missing forecast data
- Verifying successful data ingestion
- Investigating prediction failures
- Planning data refresh operations

---

### `scripts/maintenance/force_refresh_forecast.py`

**Purpose**: Force complete refresh of forecast weather data.

**Description**: Nuclear option for forecast data issues. This script completely deletes existing forecast data and
fetches fresh data from the Open-Meteo API, bypassing all caches.

**Usage**:

```bash
python scripts/maintenance/force_refresh_forecast.py
```

**⚠️ WARNING**: This script DELETES all forecast data. Use with caution in production!

**What It Does**:

1. Shows current database state
2. Clears API cache files
3. Prompts for confirmation (requires typing "yes")
4. Deletes ALL forecast weather records
5. Fetches fresh data from Open-Meteo API
6. Verifies data was written correctly
7. Displays final database state

**Safety Features**:

- Interactive confirmation required
- Shows before/after statistics
- Validates successful data retrieval
- Provides detailed error messages

**When to Use**:

- Persistent stale data issues after cache clearing
- Database corruption of forecast data
- Major API changes requiring full refresh
- After extended system downtime (weeks/months)

**Output Example**:

```
================================================================================
FORCE REFRESH FORECAST WEATHER DATA
================================================================================

Step 1: Checking current state...
  Current records: 350
  Latest date: 2025-10-11

Step 2: Clearing stale cache...
  Deleted cache file: .cache.sqlite

Step 3: Clearing existing forecast data...
  Are you sure you want to delete all forecast data? (yes/no): yes
  Deleted 350 records

Step 4: Fetching fresh forecast data from Open-Meteo API...
  Fetched 420 records
  Date range: 2025-12-03 to 2025-12-19
  Locations: ['Belet Weyne', 'Bulo Burti', 'Jowhar', 'Dollow', 'Luuq']

Step 5: Verifying data was written to database...
  Records in database: 420
  Latest date: 2025-12-19
  Unique locations: 5
  ✅ SUCCESS: Data was written to database

================================================================================
REFRESH COMPLETE
================================================================================
```

---

### `scripts/maintenance/remove_duplicate_historical_river_level.py`

**Purpose**: Collapse duplicate `(location_name, date)` rows in `flood_forecaster.historical_river_level` so that
`sql/add_historical_river_level_unique_constraint.sql` can be applied (DATA-005).

**Description**: One row survives per station per day. Retention order: a row with a non-NULL `level_m` beats a NULL one,
then the highest `id` wins, i.e. the most recently ingested.

The highest-id rule was verified rather than assumed. All nine value-conflicting pairs in the 2026-09-22 production
snapshot were arbitrated against `public.station_river_data`, and the more recently ingested value was correct in every
case — three of them correcting a whole-metre transcription error. That is also why ingestion treats a differing upstream
value as a correction and updates in place.

Pairs whose values disagree are listed individually before anything is deleted, so the only readings that change value
are visible up front. A dry run reports and writes nothing; a live run prompts for confirmation unless `--yes` is passed.

**Usage**:

```bash
# preview
python scripts/maintenance/remove_duplicate_historical_river_level.py --dry-run

# delete, with confirmation prompt
python scripts/maintenance/remove_duplicate_historical_river_level.py

# delete, non-interactive
python scripts/maintenance/remove_duplicate_historical_river_level.py --yes

# then add the constraint
psql -h <host> -U postgres -d postgres -f sql/add_historical_river_level_unique_constraint.sql
```

**Order matters**: the migration refuses to add the constraint while duplicates remain. Both the cleanup and the
migration are idempotent, so re-running either is safe.

**Before the first deployment**, use `sql/deduplicate_historical_river_level.sql` instead of this script. The constraint
has to exist before the upserting code ships, and this script ships with that code, so it is not available yet. See
[Data ingestion](components/data-ingestion.md) for the full sequence.

**Expected output** (dry run against the 2026-09-22 snapshot):

```
============================================================
DRY RUN MODE - No changes will be made to the database
============================================================
Found 962 excess row(s) across 962 duplicate (station, date) pair(s).
9 pair(s) hold conflicting values; keeping the most recently ingested:
 - Belet Weyne 2024-03-15: keeping 2.12 (range 2.12..2.13)
 - Belet Weyne 2024-03-19: keeping 2.3 (range 2.1..2.3)
 ...
Dry run: 962 row(s) would be deleted.
```

---

## Script Usage Examples

### Recovery After System Downtime

When the system has been offline and predictions are missing:

```bash
# Step 1: Check for river data gaps
python scripts/diagnostics/check_river_data_availability.py

# Step 2: Fill any gaps in river data (if gaps detected)
python scripts/backfill/fill_river_data_gaps.py

# Step 3: Ensure fresh weather data
python scripts/maintenance/clear_cache.py
flood-cli data-ingestion fetch-openmeteo historical
flood-cli data-ingestion fetch-openmeteo forecast
flood-cli data-ingestion fetch-river-data

# Step 4: Catch up missing predictions
python scripts/backfill/catchup_missing_predictions.py

# Step 5: Resume normal operations with CRON
```

### Typical Troubleshooting Workflow

When forecast data appears stale or missing:

```bash
# Step 1: Diagnose the issue
python scripts/diagnostics/diagnose_forecast_data.py

# Step 2: Try cache clearing first (least invasive)
python scripts/maintenance/clear_cache.py

# Step 3: Re-run data ingestion
flood-cli data-ingestion fetch-openmeteo forecast

# Step 4: If issue persists, force refresh (nuclear option)
python scripts/maintenance/force_refresh_forecast.py
```

### Manual Production Run

To manually run the full pipeline:

```bash
cd /path/to/saadaal-flood-forecaster
./scripts/amadeus_saadaal_flood_forecaster_resilient.sh $(pwd) $(pwd)/.venv
```

### Batch Processing for Specific Stations

```bash
cd /path/to/saadaal-flood-forecaster
./scripts/backfill/batch_infer_and_risk_assess.sh $(pwd) $(pwd)/.venv
```

---

## Best Practices

1. **Always use the resilient script in production** to handle transient failures gracefully
2. **Clear cache before major system updates** to ensure fresh data retrieval
3. **Run diagnostics before force refresh** to understand the scope of the issue
4. **Monitor CRON logs regularly** to catch issues early
5. **Use catchup script after downtime** to fill prediction gaps and maintain continuity
6. **Test scripts in development** before deploying to production
7. **Keep scripts executable**: `chmod +x scripts/*.sh`

---

## Related Documentation

- [Server Quick Reference](server-quick-reference.md)

Historical incident context (not current operating instructions):

- [Complete Deployment Guide](archive/incidents/complete-deployment-guide.md)
- [Forecast Data Issue Resolution](archive/incidents/forecast-data-issue-resolution.md)
- [Cache Issue Root Cause](archive/incidents/cache-issue-root-cause.md)

---

**Last Updated**: December 2025

