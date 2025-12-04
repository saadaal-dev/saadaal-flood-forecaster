# Scripts Reference Guide

This document provides a comprehensive overview of all utility scripts in the `scripts/` directory. These scripts
support deployment, automation, maintenance, and troubleshooting of the Flood Forecaster system.

---

## 📋 Table of Contents

- [Production Scripts](#production-scripts)
- [Maintenance & Troubleshooting Scripts](#maintenance--troubleshooting-scripts)
- [Script Usage Examples](#script-usage-examples)

---

## Production Scripts

### `amadeus_saadaal_flood_forecaster.sh`

**Purpose**: Main production pipeline script for automated flood forecasting.

**Description**: This script orchestrates the complete flood forecasting pipeline in a sequential manner. It performs
data ingestion, model inference, risk assessment, and alert dispatch. Designed to run as a CRON job for regular
automated forecasting.

**Usage**:

```bash
./scripts/amadeus_saadaal_flood_forecaster.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
```

**Parameters**:

- `REPOSITORY_ROOT_PATH`: Absolute path to the flood forecaster repository
- `VENV_PATH`: Path to the Python virtual environment
- `--windows` (optional): Flag to indicate Windows environment

**Key Features**:

- Activates virtual environment
- Loads environment variables from `.env`
- Executes data ingestion (historical, forecast, river data)
- Runs ML inference for all configured stations
- Performs risk assessment
- Dispatches alerts if needed
- Logs all operations

**CRON Setup Example**:

```bash
# Run daily at 12:00 PM
0 12 * * * /root/Amadeus/saadaal-flood-forecaster/scripts/amadeus_saadaal_flood_forecaster.sh /root/Amadeus/saadaal-flood-forecaster /root/Amadeus/saadaal-flood-forecaster/.venv >> /root/Amadeus/saadaal-flood-forecaster/logs/logs_amadeus_saadaal_flood_forecaster.log 2>&1
```

**Exit Behavior**: Fails fast on any error (`set -euo pipefail`)

---

### `amadeus_saadaal_flood_forecaster_resilient.sh`

**Purpose**: Resilient version of the main pipeline with graceful error handling.

**Description**: Similar to the main script, but implements graceful degradation. This version continues execution even
if individual steps fail, logging errors and attempting to complete as much of the pipeline as possible.

**Usage**:

```bash
./scripts/amadeus_saadaal_flood_forecaster_resilient.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
```

**Parameters**: Same as `amadeus_saadaal_flood_forecaster.sh`

**Key Features**:

- Colored output for success (green), failure (red), and warnings (yellow)
- Tracks success/failure/skipped operation counts
- Continues on errors instead of failing fast
- Provides summary report at the end
- Better suited for unreliable network conditions

**When to Use**:

- Production environments with unstable network connections
- When partial pipeline execution is acceptable
- During debugging to see all failures in one run

---

### `batch_infer_and_risk_assess.sh`

**Purpose**: Batch processing script for running inference and risk assessment across multiple stations.

**Description**: Processes all configured river stations sequentially, running ML inference and risk assessment for
each. Useful for manual batch operations or custom automation scenarios.

**Usage**:

```bash
./scripts/batch_infer_and_risk_assess.sh <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]
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

### `catchup_missing_predictions.py`

**Purpose**: Backfill missing river level predictions when the automated pipeline has failed.

**Description**: Analyzes the `predicted_river_level` table to identify gaps in predictions for each location, then
automatically runs inference for all missing dates to catch up. Uses the same `flood-cli` commands as
`batch_infer_and_risk_assess.sh` but only for the specific missing date ranges per location. This is essential for
maintaining data continuity after system downtime or pipeline failures.

**Usage**:

```bash
python scripts/catchup_missing_predictions.py
```

**Where to Run**:
This script connects to the PostgreSQL database using the configuration in `config/config.ini` (host: `68.183.13.232`).
You can run it from:

- ✅ **Inside the Docker container**: Most common for production
  ```bash
  docker exec -it <container-id> bash
  cd /root/Amadeus/saadaal-flood-forecaster
  python scripts/catchup_missing_predictions.py
  ```
- ✅ **Outside the container**: If you have network access to the database server
    - Requires `POSTGRES_PASSWORD` environment variable set in `.env` file
    - Requires network connectivity to the database host (port 5432)
    - Requires `flood-cli` to be installed and in PATH

**What It Does**:

1. Scans the database for all locations with existing predictions
2. Identifies the last prediction date for each location
3. Calculates missing dates from last prediction until today
4. Displays a summary of missing predictions by location
5. Prompts for confirmation before proceeding
6. Runs ML inference for each missing date and location (uses `flood-cli ml infer` like
   `batch_infer_and_risk_assess.sh`)
7. Updates risk assessments after catching up (uses `flood-cli risk-assessment`)
8. Provides detailed progress and summary statistics

**Relationship to `batch_infer_and_risk_assess.sh`**:
This script is smarter than running the full batch script - instead of processing ALL dates from 2024-01-01, it only
processes the specific missing dates for each location. It uses the same CLI commands but targets only the gaps.

**Safety Features**:

- Interactive confirmation required before processing
- Shows detailed analysis before making changes
- Tracks success/failure counts for each location
- Validates predictions were created successfully
- Provides actionable troubleshooting guidance

**When to Use**:

- After extended system downtime (server offline, service stopped)
- When automated CRON jobs have failed for multiple days
- After fixing issues that prevented predictions from running
- To verify and fill any gaps in the prediction timeline
- During system recovery after database issues

**Output Example**:

```
================================================================================
CATCHUP MISSING PREDICTIONS
================================================================================
Current time: 2025-12-03 14:30:00
Catching up predictions until: 2025-12-03

Step 1: Analyzing missing predictions by location
--------------------------------------------------------------------------------
Found 5 locations: Belet Weyne, Bulo Burti, Jowhar, Dollow, Luuq

📍 Belet Weyne
   Last prediction: 2025-11-28
   Missing days: 5
   Date range: 2025-11-29 to 2025-12-03

📍 Bulo Burti
   Last prediction: 2025-11-30
   Missing days: 3
   Date range: 2025-12-01 to 2025-12-03

...

📊 Summary: 18 missing predictions across 5 locations

⚠️  This will run inference for all missing dates.
   Depending on the number of missing dates, this may take a while.

Do you want to proceed? (yes/no): yes

Step 2: Running inference for missing dates
--------------------------------------------------------------------------------
📍 Belet Weyne: Processing 5 missing dates...
  Processing 2025-11-29... ✅
  Processing 2025-11-30... ✅
  Processing 2025-12-01... ✅
  Processing 2025-12-02... ✅
  Processing 2025-12-03... ✅
  Location summary: 5 successful, 0 failed

...

================================================================================
Step 3: Updating risk assessments
--------------------------------------------------------------------------------
✅ Risk assessments updated successfully

================================================================================
CATCHUP COMPLETE
================================================================================
Total missing predictions found: 18
Successfully processed: 18
Failed: 0

✅ All missing predictions have been filled successfully!
================================================================================
```

**Prerequisites**:

- **Database Access**:
    - Database connection configured in `config/config.ini`
    - `POSTGRES_PASSWORD` environment variable set (loaded from `.env` file)
    - Network connectivity to database host (default: `68.183.13.232:5432`)
- **Environment**:
    - `flood-cli` command available in PATH (installed via `install.sh`)
    - Python virtual environment activated (if running outside container)
- **Data Requirements**:
    - Historical weather data must be available for the missing dates
    - ML model files must exist for all locations (`models/` directory)

**Troubleshooting**:
If some predictions fail, you may need to:

- Ensure historical weather data exists: `flood-cli data-ingestion fetch-openmeteo historical`
- Verify model files exist in the `models/` directory
- Check database connectivity and permissions
- Review error messages for specific issues

---

### `clear_cache.py`

**Purpose**: Clear the requests cache to force fresh API data retrieval.

**Description**: Removes cached API responses that may contain stale weather forecast data. This script solves issues
where forecast data was cached indefinitely and never refreshed.

**Usage**:

```bash
python scripts/clear_cache.py
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

### `diagnose_forecast_data.py`

**Purpose**: Diagnostic tool to analyze forecast weather data in the database.

**Description**: Provides comprehensive statistics and insights about forecast data stored in the database. Helps
identify data gaps, date range issues, and location-specific problems.

**Usage**:

```bash
python scripts/diagnose_forecast_data.py
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

### `force_refresh_forecast.py`

**Purpose**: Force complete refresh of forecast weather data.

**Description**: Nuclear option for forecast data issues. This script completely deletes existing forecast data and
fetches fresh data from the Open-Meteo API, bypassing all caches.

**Usage**:

```bash
python scripts/force_refresh_forecast.py
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

## Script Usage Examples

### Recovery After System Downtime

When the system has been offline and predictions are missing:

```bash
# Step 1: Ensure fresh weather data
python scripts/clear_cache.py
flood-cli data-ingestion fetch-openmeteo historical
flood-cli data-ingestion fetch-openmeteo forecast
flood-cli data-ingestion fetch-river-data

# Step 2: Catch up missing predictions
python scripts/catchup_missing_predictions.py

# Step 3: Resume normal operations with CRON
```

### Typical Troubleshooting Workflow

When forecast data appears stale or missing:

```bash
# Step 1: Diagnose the issue
python scripts/diagnose_forecast_data.py

# Step 2: Try cache clearing first (least invasive)
python scripts/clear_cache.py

# Step 3: Re-run data ingestion
flood-cli data-ingestion fetch-openmeteo forecast

# Step 4: If issue persists, force refresh (nuclear option)
python scripts/force_refresh_forecast.py
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
./scripts/batch_infer_and_risk_assess.sh $(pwd) $(pwd)/.venv
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

- [Complete Deployment Guide](COMPLETE_DEPLOYMENT_GUIDE.md)
- [Server Quick Reference](SERVER_QUICK_REFERENCE.md)
- [Forecast Data Issue Resolution](FORECAST_DATA_ISSUE_RESOLUTION.md)
- [Cache Issue Root Cause](CACHE_ISSUE_ROOT_CAUSE.md)

---

**Last Updated**: December 2025

