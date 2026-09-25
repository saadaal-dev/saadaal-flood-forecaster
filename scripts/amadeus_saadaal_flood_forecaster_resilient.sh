#!/usr/bin/env bash
# Resilient version of the flood forecaster pipeline
# This version continues even if some steps fail, allowing graceful degradation

set -u  # Fail on unset variables
# NOTE: Removed 'set -e' and 'set -o pipefail' to allow graceful error handling

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters for monitoring
SUCCESS_COUNT=0
FAILURE_COUNT=0
SKIPPED_COUNT=0

# flood-cli commands
FETCH_RIVER_LEVEL_DATA_COMMAND="flood-cli data-ingestion fetch-river-data"
FETCH_HISTORICAL_WEATHER_DATA_COMMAND="flood-cli data-ingestion fetch-openmeteo historical"
FETCH_FORECAST_WEATHER_DATA_COMMAND="flood-cli data-ingestion fetch-openmeteo forecast"
# ML_INFER_COMMAND is built per-station in the loop
RISK_ASSESSMENT_COMMAND="flood-cli risk-assessment"
ALERT_COMMAND="flood-cli alert"

# Get the current datetime
current_datetime=$(date '+%Y-%m-%d %H:%M:%S')
echo "============================================================================"
echo "Runtime: $current_datetime"
echo "============================================================================"

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi
if [ "$#" -gt 3 ]; then
    echo "Too many arguments provided. Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi

# Check if running in Windows environment
is_windows=false
if [ "$#" -eq 2 ]; then
    echo "Running in Unix-like environment"
    is_windows=false
elif [ "$#" -eq 3 ] && [ "$3" == "--windows" ]; then
    echo "Running in Windows environment"
    is_windows=true
elif [ "$#" -eq 3 ] && [ "$3" != "--windows" ]; then
    echo "Invalid argument for Windows flag. Use --windows to indicate a Windows environment."
    exit 1
fi

REPOSITORY_ROOT_PATH=$1
echo "REPOSITORY_ROOT_PATH: $REPOSITORY_ROOT_PATH"
VENV_PATH=$2
echo "VENV_PATH: $VENV_PATH"

# Move to the repository root path
cd "$REPOSITORY_ROOT_PATH" || exit

# Activate the virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found at $VENV_PATH. Please create it first.${NC}"
    exit 1
fi
if [ "$is_windows" = true ]; then
    source "$VENV_PATH"/Scripts/activate
else
    source "$VENV_PATH"/bin/activate
fi
echo -e "${GREEN}✅ Virtual environment activated: $VIRTUAL_ENV${NC}"

# Load .env variables.
#
# We deliberately do NOT `source` the file: it is written in unquoted
# KEY=value form for python-dotenv, and `source` would word-split and execute
# values containing spaces, '#' or '$' (e.g. a password like "p@ss w#rd" would
# try to run `w#rd` as a command). Parsing line by line and exporting is both
# safe and, unlike `source`, actually puts the values in the *environment* so
# child processes such as flood-cli inherit them instead of relying on
# python-dotenv finding this file on its own.
if [ -f "$REPOSITORY_ROOT_PATH/.env" ]; then
    while IFS='=' read -r _key _value || [ -n "$_key" ]; do
        # Skip blanks and comments.
        case "$_key" in
            ''|'#'*) continue ;;
        esac
        _key="${_key#"${_key%%[![:space:]]*}"}"   # trim leading whitespace
        _key="${_key%"${_key##*[![:space:]]}"}"   # trim trailing whitespace
        [ -z "$_key" ] && continue
        export "$_key=$_value"
    done < "$REPOSITORY_ROOT_PATH/.env"
    unset _key _value
else
    echo -e "${YELLOW}⚠️  No .env file at $REPOSITORY_ROOT_PATH/.env${NC}"
fi

# Fail fast on missing database credentials. Without this the pipeline burns
# ~2 minutes on 6 doomed retries and then reports a misleading
# "stale forecast data" abort, which hides the real cause.
MISSING_ENV=()
for _required in DB_HOST POSTGRES_PASSWORD; do
    [ -z "${!_required:-}" ] && MISSING_ENV+=("$_required")
done
if [ "${#MISSING_ENV[@]}" -gt 0 ]; then
    echo -e "${RED}❌ CONFIGURATION ERROR: missing required environment variable(s): ${MISSING_ENV[*]}${NC}"
    echo -e "${RED}   Every database read and write will fail, so the pipeline cannot run.${NC}"
    echo -e "${RED}   Set them in the deployment environment (CapRover: App Configs ->${NC}"
    echo -e "${RED}   Environmental Variables), redeploy/restart the app, and re-run.${NC}"
    echo "============================================================================"
    echo "❌ PIPELINE ABORTED DUE TO INCOMPLETE CONFIGURATION"
    echo "============================================================================"
    exit 1
fi

# Function to retry command with exponential backoff
retry_command() {
    local cmd="$1"
    local description="$2"
    local max_attempts=3
    local attempt=1
    local wait_time=5

    echo ""
    echo "────────────────────────────────────────────────────────────────────────────"
    echo "📋 Task: $description"
    echo "────────────────────────────────────────────────────────────────────────────"

    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Attempt $attempt/$max_attempts: $cmd"
        if eval "$cmd" 2>&1; then
            echo -e "${GREEN}✅ SUCCESS${NC}"
            ((SUCCESS_COUNT++))
            return 0
        else
            local exit_code=$?
            echo -e "${RED}❌ FAILED (exit code: $exit_code)${NC}"
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${YELLOW}⏳ Waiting ${wait_time}s before retry...${NC}"
                sleep $wait_time
                wait_time=$((wait_time * 2))  # Exponential backoff
            fi
            ((attempt++))
        fi
    done

    echo -e "${RED}❌ All $max_attempts attempts failed${NC}"
    ((FAILURE_COUNT++))
    return 1
}

# Function to run command once (no retry)
run_command() {
    local cmd="$1"
    local description="$2"

    echo ""
    echo "────────────────────────────────────────────────────────────────────────────"
    echo "📋 Task: $description"
    echo "────────────────────────────────────────────────────────────────────────────"
    echo "Running: $cmd"

    if eval "$cmd" 2>&1; then
        echo -e "${GREEN}✅ SUCCESS${NC}"
        ((SUCCESS_COUNT++))
        return 0
    else
        local exit_code=$?
        echo -e "${RED}❌ FAILED (exit code: $exit_code)${NC}"
        ((FAILURE_COUNT++))
        return 1
    fi
}

# Function to check forecast data freshness
check_forecast_freshness() {
    python << 'EOF'
import sys
from datetime import datetime, timedelta
try:
    from sqlalchemy import select, func
    from flood_forecaster.utils.configuration import Config
    from flood_forecaster.utils.database_helper import DatabaseConnection
    from flood_forecaster.data_model.weather import ForecastWeather

    config = Config("config/config.ini")
    db = DatabaseConnection(config)

    with db.engine.connect() as conn:
        stmt = select(func.max(ForecastWeather.date))
        max_date = conn.execute(stmt).scalar()

        if max_date is None:
            print("⚠️  No forecast data in database")
            sys.exit(1)

        # Convert to date if it's a datetime
        if hasattr(max_date, 'date'):
            max_date = max_date.date()

        # Check if forecast extends at least 5 days into future
        min_required = datetime.now().date() + timedelta(days=5)
        if max_date < min_required:
            print(f"⚠️  Forecast data too stale: {max_date} (need at least {min_required})")
            sys.exit(1)

        print(f"✅ Forecast data is fresh: {max_date}")
        sys.exit(0)
except Exception as e:
    print(f"❌ Error checking forecast freshness: {e}")
    sys.exit(1)
EOF
}

echo ""
echo "============================================================================"
echo "🚀 PHASE 1: DATA INGESTION"
echo "============================================================================"

# Historical weather (retry with backoff)
retry_command "$FETCH_HISTORICAL_WEATHER_DATA_COMMAND" "Fetch historical weather data" || {
    echo -e "${YELLOW}⚠️  Historical weather fetch failed, will use existing data${NC}"
}

# Forecast weather (retry with backoff) - CRITICAL
if ! retry_command "$FETCH_FORECAST_WEATHER_DATA_COMMAND" "Fetch forecast weather data"; then
    echo -e "${YELLOW}⚠️  Forecast weather fetch failed, checking existing data...${NC}"
    if check_forecast_freshness; then
        echo -e "${GREEN}✅ Existing forecast data is sufficient for predictions${NC}"
    else
        echo -e "${RED}❌ CRITICAL: Forecast data is too stale or missing${NC}"
        echo -e "${RED}   Cannot proceed with inference - predictions would be meaningless${NC}"
        echo ""
        echo "============================================================================"
        echo "❌ PIPELINE ABORTED DUE TO STALE FORECAST DATA"
        echo "============================================================================"
        echo "Summary: $SUCCESS_COUNT successes, $FAILURE_COUNT failures"
        exit 1
    fi
fi

# River data (retry with backoff)
retry_command "$FETCH_RIVER_LEVEL_DATA_COMMAND" "Fetch river level data" || {
    echo -e "${YELLOW}⚠️  River data fetch failed, will use existing data${NC}"
}

echo ""
echo "============================================================================"
echo "🔮 PHASE 2: INFERENCE (5 stations)"
echo "============================================================================"

# List of stations for inference
STATIONS=("Belet Weyne" "Bulo Burti" "Jowhar" "Dollow" "Luuq")

for STATION in "${STATIONS[@]}"; do
    ML_INFER_COMMAND="flood-cli ml infer -f 7 -m Prophet_001 -o database \"$STATION\""
    run_command "$ML_INFER_COMMAND" "Inference for $STATION" || {
        echo -e "${YELLOW}⚠️  Inference failed for $STATION, continuing with other stations${NC}"
    }
done

echo ""
echo "============================================================================"
echo "📊 PHASE 3: RISK ASSESSMENT"
echo "============================================================================"

run_command "$RISK_ASSESSMENT_COMMAND" "Risk assessment for all stations" || {
    echo -e "${YELLOW}⚠️  Risk assessment failed, alerts may not be accurate${NC}"
}

echo ""
echo "============================================================================"
echo "🔔 PHASE 4: ALERTING"
echo "============================================================================"

run_command "$ALERT_COMMAND" "Send alerts" || {
    echo -e "${YELLOW}⚠️  Alert sending failed${NC}"
}

echo ""
echo "============================================================================"
echo "📈 PIPELINE SUMMARY"
echo "============================================================================"
echo "✅ Successes: $SUCCESS_COUNT"
echo "❌ Failures:  $FAILURE_COUNT"
echo "⏭️  Skipped:   $SKIPPED_COUNT"
echo ""

# Determine exit code based on results
if [ $FAILURE_COUNT -eq 0 ]; then
    echo -e "${GREEN}🎉 All tasks completed successfully!${NC}"
    exit 0
elif [ $SUCCESS_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Pipeline completed with some failures (partial success)${NC}"
    exit 2  # Non-zero but different from complete failure
else
    echo -e "${RED}❌ Pipeline failed completely${NC}"
    exit 1
fi

