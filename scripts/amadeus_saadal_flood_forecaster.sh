#!/usr/bin/env bash
set -euo pipefail

# Define script directory
SCRIPT_DIR="$(pwd)"

export PYTHONPATH=.

DATA_PROCESSING_COMMAND=$"echo 'Put here the data processing command'"
INFERENCE_COMMAND=$"echo 'Put here the inference command'"
RISK_ASSESSMENT_COMMAND=$"python ${SCRIPT_DIR}/src/flood_forecaster/risk_assessment/risk_assessment.py"
ALERT_COMMAND=$"echo 'Put here the alert command'"

# List of commands to run (edit as needed)
COMMANDS=(
    "$DATA_PROCESSING_COMMAND"
    "$INFERENCE_COMMAND"
    "$RISK_ASSESSMENT_COMMAND"
    "$ALERT_COMMAND"
)

for cmd in "${COMMANDS[@]}"; do
    echo "Running: $cmd"
    eval "$cmd"
    echo "Command completed successfully."
done

echo "All commands executed successfully."