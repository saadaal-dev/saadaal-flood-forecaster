#!/bin/bash
# Manual trigger script for the flood forecaster pipeline
# Use this to test the pipeline without waiting for the cron schedule
#
# Usage (from container):
#   bash /root/Amadeus/saadaal-flood-forecaster/scripts/ops/trigger_forecast_now.sh [--resilient]
#
# Usage (from host using docker exec):
#   docker exec <container-id> bash /root/Amadeus/saadaal-flood-forecaster/scripts/ops/trigger_forecast_now.sh [--resilient]
#
# Options:
#   --resilient    Use the resilient version (continues on errors)
#
# NOTE: without --resilient this runs the legacy strict orchestrator
# (scripts/legacy/amadeus_saadaal_flood_forecaster.sh), which is NOT what the
# production cron job runs. Pass --resilient to reproduce production behaviour.

set -euo pipefail

# Default paths (can be overridden by environment variables)
REPOSITORY_ROOT_PATH="${REPOSITORY_ROOT_PATH:-/root/Amadeus/saadaal-flood-forecaster}"
VENV_PATH="${VENV_PATH:-$REPOSITORY_ROOT_PATH/.venv}"

# Determine which script to use. Paths are relative to scripts/: the production
# orchestrator sits at the root of scripts/, the strict one under scripts/legacy/.
SCRIPT_REL_PATH="legacy/amadeus_saadaal_flood_forecaster.sh"
if [[ "${1:-}" == "--resilient" ]]; then
    SCRIPT_REL_PATH="amadeus_saadaal_flood_forecaster_resilient.sh"
    echo "Using RESILIENT version (continues on errors)"
fi

echo "========================================================================"
echo "MANUAL TRIGGER: Flood Forecaster Pipeline"
echo "========================================================================"
echo "Repository: $REPOSITORY_ROOT_PATH"
echo "VirtualEnv: $VENV_PATH"
echo "Script: scripts/$SCRIPT_REL_PATH"
echo "Time: $(date)"
echo "========================================================================"
echo ""

# Run the main pipeline script
bash "$REPOSITORY_ROOT_PATH/scripts/$SCRIPT_REL_PATH" \
    "$REPOSITORY_ROOT_PATH" \
    "$VENV_PATH"

echo ""
echo "========================================================================"
echo "MANUAL TRIGGER COMPLETE"
echo "========================================================================"

