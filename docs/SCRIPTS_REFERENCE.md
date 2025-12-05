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

**Description**: Analyzes all configured stations (from metadata) and the `predicted_river_level` table to identify *
*ALL gaps and holes** in predictions. Prompts you to specify a start date, then automatically runs inference for all
missing dates to catch up. **Detects gaps in the middle of existing data**, not just missing dates at the end. Uses the
same `flood-cli` commands as `batch_infer_and_risk_assess.sh` but only for the specific missing date ranges per
location. **Works even for locations with no existing predictions** in the database. This is essential for maintaining
data continuity after system downtime or pipeline failures.

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
    - Database connection configured in `config/config.ini`
    - `POSTGRES_PASSWORD` environment variable set (loaded from `.env` file)
    - Network connectivity to database host (default: `68.183.13.232:5432`)
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
   python scripts/check_river_data_availability.py
   ```
   This will show you:
    - Date range of available river data per location
    - Safe start date where all locations have data
    - Locations with limited or outdated data

   Or check directly in the database:
   ```sql
   SELECT location_name, MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as records
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

### `fill_river_data_gaps.py`

**Purpose**: Fill gaps in historical river level data using the public.station_river_data table.

**Description**: Identifies gaps in the `flood_forecaster.historical_river_level` table and fills them by fetching data
from `public.station_river_data` using the station mapping in `river_station_metadata`. This solves the critical issue
where data gaps prevent catchup predictions from working.

**Usage**:

```bash
python scripts/fill_river_data_gaps.py
```

**How It Works**:

1. Loads station mapping from `river_station_metadata` (station_name → swalim_internal_id)
2. For each station, identifies date gaps in `historical_river_level`
3. Fetches missing data from `public.station_river_data` using the SWALIM ID
4. Inserts missing records into `historical_river_level`
5. Reports success/failure statistics

**What It Shows**:

- Station mapping (name to SWALIM ID)
- Existing data range per station
- Number of gaps detected
- Records fetched from source table
- Records successfully inserted
- Records still missing (if source doesn't have them)

**When to Use**:

- **When catchup fails with "Missing river level data" error**
- After identifying gaps with `check_river_data_availability.py`
- To backfill historical data from the public schema
- After system downtime that caused data collection gaps

**Prerequisites**:

- `public.station_river_data` table must exist and contain historical data
- `river_station_metadata.swalim_internal_id` must be populated
- Database connection with access to both schemas

**Output Example**:

```
================================================================================
FILL GAPS IN HISTORICAL RIVER LEVEL DATA
================================================================================

Step 1: Loading station mapping
--------------------------------------------------------------------------------
Found 5 stations with SWALIM IDs:
  - Belet Weyne: SWALIM ID 123
  - Bulo Burti: SWALIM ID 124
  - Dollow: SWALIM ID 125
  - Jowhar: SWALIM ID 126
  - Luuq: SWALIM ID 127

Step 2: Analyzing data gaps
--------------------------------------------------------------------------------
📍 Belet Weyne
   Date range: 2025-09-15 to 2025-12-04
   Existing records: 3
   Expected records: 81
   ⚠️  Gaps detected: 78 missing days
   Missing dates: 78
      First: 2025-09-16
      Last: 2025-12-03

📍 Bulo Burti
   Date range: 2025-09-15 to 2025-12-04
   Existing records: 3
   Expected records: 81
   ⚠️  Gaps detected: 78 missing days

📊 Total gaps found: 156 missing days across 2 stations

⚠️  This will fetch data from public.station_river_data and fill the gaps.

Do you want to proceed? (yes/no): yes

Step 3: Filling gaps from public.station_river_data
--------------------------------------------------------------------------------
📍 Belet Weyne (SWALIM ID: 123)
   Fetching data for 78 missing dates...
   Found 78 records in source table
   Inserting 78 records...
   ✅ Successfully inserted 78 records

📍 Bulo Burti (SWALIM ID: 124)
   Fetching data for 78 missing dates...
   Found 78 records in source table
   Inserting 78 records...
   ✅ Successfully inserted 78 records

================================================================================
GAP FILLING COMPLETE
================================================================================
Total gaps found: 156
Successfully filled: 156
Still missing (no source data): 0

✅ Gaps have been filled! Run check_river_data_availability.py to verify.

Next steps:
  1. Verify gaps are filled: python scripts/check_river_data_availability.py
  2. Run catchup: python scripts/catchup_missing_predictions.py
================================================================================
```

**Safety Features**:

- Shows analysis before making changes
- Requires "yes" confirmation before filling
- Uses `ON CONFLICT DO NOTHING` to avoid duplicates
- Reports detailed statistics
- Continues on individual errors

**Troubleshooting**:

- **"No station mapping found"**: Check that `swalim_internal_id` is populated in `river_station_metadata`
- **"No data found in public.station_river_data"**: The source table may not have data for those dates/stations
- **"Error querying public.station_river_data"**: Check table exists and you have access permissions

---

### `check_river_data_availability.py`

**Purpose**: Check what historical river level data is available in the database.

**Description**: Displays statistics about available river data per location, helping you determine valid date ranges
for the catchup script. Essential for understanding what dates you can backfill.

**Usage**:

```bash
python scripts/check_river_data_availability.py
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

   python scripts/catchup_missing_predictions.py
   # When prompted, enter start date: 2024-11-01

================================================================================
```

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
# Step 1: Check for river data gaps
python scripts/check_river_data_availability.py

# Step 2: Fill any gaps in river data (if gaps detected)
python scripts/fill_river_data_gaps.py

# Step 3: Ensure fresh weather data
python scripts/clear_cache.py
flood-cli data-ingestion fetch-openmeteo historical
flood-cli data-ingestion fetch-openmeteo forecast
flood-cli data-ingestion fetch-river-data

# Step 4: Catch up missing predictions
python scripts/catchup_missing_predictions.py

# Step 5: Resume normal operations with CRON
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

