#!/bin/bash
# Manual trigger script for the flood forecaster pipeline
# Use this to test the pipeline without waiting for the cron schedule
#
# Usage (from container):
#   bash /root/Amadeus/saadaal-flood-forecaster/scripts/trigger_forecast_now.sh [--resilient]
#
# Usage (from host using docker exec):
#   docker exec <container-id> bash /root/Amadeus/saadaal-flood-forecaster/scripts/trigger_forecast_now.sh [--resilient]
#
# Options:
#   --resilient    Use the resilient version (continues on errors)

set -euo pipefail

# Default paths (can be overridden by environment variables)
REPOSITORY_ROOT_PATH="${REPOSITORY_ROOT_PATH:-/root/Amadeus/saadaal-flood-forecaster}"
VENV_PATH="${VENV_PATH:-$REPOSITORY_ROOT_PATH/.venv}"

# Determine which script to use
SCRIPT_NAME="amadeus_saadaal_flood_forecaster.sh"
if [[ "${1:-}" == "--resilient" ]]; then
    SCRIPT_NAME="amadeus_saadaal_flood_forecaster_resilient.sh"
    echo "Using RESILIENT version (continues on errors)"
fi

echo "========================================================================"
echo "MANUAL TRIGGER: Flood Forecaster Pipeline"
echo "========================================================================"
echo "Repository: $REPOSITORY_ROOT_PATH"
echo "VirtualEnv: $VENV_PATH"
echo "Script: $SCRIPT_NAME"
echo "Time: $(date)"
echo "========================================================================"
echo ""

# Run the main pipeline script
bash "$REPOSITORY_ROOT_PATH/scripts/$SCRIPT_NAME" \
    "$REPOSITORY_ROOT_PATH" \
    "$VENV_PATH"

echo ""
echo "========================================================================"
echo "MANUAL TRIGGER COMPLETE"
echo "========================================================================"

