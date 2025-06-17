#!/usr/bin/env bash
set -euo pipefail

# Get the current datetime
current_datetime=$(date '+%Y-%m-%d %H:%M:%S')

# Echo the current datetime for logs
echo "Runtime: $current_datetime"

# Check if REPOSITORY_ROOT_PATH is passed as an argument
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <REPOSITORY_ROOT_PATH> <VENV_PATH>"
    exit 1
fi

REPOSITORY_ROOT_PATH=$1
echo "REPOSITORY_ROOT_PATH: $REPOSITORY_ROOT_PATH"
VENV_PATH=$2
echo "VENV_PATH: $VENV_PATH"

# Move to the repository root path
cd "$REPOSITORY_ROOT_PATH"

# Activate the virtual environment
source "$VENV_PATH"/bin/activate
echo "Virtual environment activated $VIRTUAL_ENV"

# Load .env variables
source "$REPOSITORY_ROOT_PATH/.env"

DATA_PROCESSING_COMMAND=$"echo 'Put here the data processing command'"
INFERENCE_COMMAND=$"echo 'Put here the inference command'"
RISK_ASSESSMENT_COMMAND=$"PYTHONPATH=. ${VENV_PATH}/bin/python3 ${REPOSITORY_ROOT_PATH}/src/flood_forecaster/risk_assessment/risk_assessment.py"
ALERT_COMMAND=$"echo 'Put here the alert command'"

# List of commands to run (edit as needed)
COMMANDS=(
    "python3 --version"
    "which python3"
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