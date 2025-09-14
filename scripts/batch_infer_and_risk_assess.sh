#!/usr/bin/env bash
set -euo pipefail

# Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi
if [ "$#" -gt 3 ]; then
    echo "Too many arguments provided. Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi

REPOSITORY_ROOT_PATH=$1
VENV_PATH=$2
IS_WINDOWS=false
if [ "$#" -eq 3 ]; then
    if [ "$3" == "--windows" ]; then
        IS_WINDOWS=true
    else
        echo "Invalid argument for Windows flag. Use --windows to indicate a Windows environment."
        exit 1
    fi
fi

echo "REPOSITORY_ROOT_PATH: $REPOSITORY_ROOT_PATH"
echo "VENV_PATH: $VENV_PATH"
echo "IS_WINDOWS: $IS_WINDOWS"

cd "$REPOSITORY_ROOT_PATH"

if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH. Please create it first."
    exit 1
fi
if [ "$IS_WINDOWS" = true ]; then
    source "$VENV_PATH"/Scripts/activate
else
    source "$VENV_PATH"/bin/activate
fi
echo "Virtual environment activated $VIRTUAL_ENV"

# Load .env variables
source "$REPOSITORY_ROOT_PATH/.env"

# List of stations
STATIONS=("Belet Weyne" "Bulo Burti" "Jowhar" "Dollow" "Luuq")

# Run data processing command once
DATA_PROCESSING_COMMAND="flood-cli data-ingestion fetch-openmeteo historical && flood-cli data-ingestion fetch-openmeteo forecast && flood-cli data-ingestion fetch-river-data"
echo "Running data processing command..."
eval "$DATA_PROCESSING_COMMAND"

START_DATE="2024-01-01"
echo "Starting batch inference for all stations from $START_DATE to today..."

END_DATE=$(date '+%Y-%m-%d')
CURRENT_DATE="$START_DATE"

while [[ "$CURRENT_DATE" < "$END_DATE" || "$CURRENT_DATE" == "$END_DATE" ]]; do
    echo "Processing date: $CURRENT_DATE"
    for STATION in "${STATIONS[@]}"; do
        INFER_CMD="flood-cli ml infer -f 7 -m Prophet_001 -o database -d \"$CURRENT_DATE\" \"$STATION\""
        echo "Running: $INFER_CMD"
        eval "$INFER_CMD"
    done
    # Increment date
    CURRENT_DATE=$(date -j -f "%Y-%m-%d" -v+1d "$CURRENT_DATE" "+%Y-%m-%d" 2>/dev/null || date -d "$CURRENT_DATE + 1 day" "+%Y-%m-%d")
done

echo "All inference complete. Running risk assessment..."
flood-cli risk-assessment

echo "Batch inference and risk assessment completed."
