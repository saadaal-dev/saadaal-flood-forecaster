#!/usr/bin/env bash
set -euo pipefail

# Get the current datetime
current_datetime=$(date '+%Y-%m-%d %H:%M:%S')

# Echo the current datetime for logs
echo "Runtime: $current_datetime"

# Check if REPOSITORY_ROOT_PATH is passed as an argument
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi
if [ "$#" -gt 3 ]; then
    echo "Too many arguments provided. Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH> [--windows]"
    exit 1
fi

# Check if the script is running in a Windows environment (based on input flag)
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
cd "$REPOSITORY_ROOT_PATH"

# Activate the virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH. Please create it first."
    exit 1
fi
if [ "$is_windows" = true ]; then
    source "$VENV_PATH"/Scripts/activate
else
    source "$VENV_PATH"/bin/activate
fi
echo "Virtual environment activated $VIRTUAL_ENV"

# # Load .env variables
# source "$REPOSITORY_ROOT_PATH/.env"

DATA_PROCESSING_COMMAND="flood-cli data-ingestion fetch-openmeteo historical && flood-cli data-ingestion fetch-openmeteo forecast && flood-cli data-ingestion fetch-river-data"
INFERENCE_COMMAND="flood-cli ml infer -f 7 -m Prophet_001 -o database \"Dollow\""
RISK_ASSESSMENT_COMMAND="flood-cli risk-assessment"
ALERT_COMMAND=$"echo 'Put here the alert command'"

# List of commands to run (edit as needed)
COMMANDS=(
    "python --version"
    "which python"
    "$DATA_PROCESSING_COMMAND"
    "$INFERENCE_COMMAND"
    "$RISK_ASSESSMENT_COMMAND"
    "$ALERT_COMMAND"
)

for cmd in "${COMMANDS[@]}"; do
    echo "Running: $cmd"
    eval "$cmd"
done

echo "All commands executed successfully."
