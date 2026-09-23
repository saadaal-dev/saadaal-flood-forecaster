#!/bin/bash
# Switch the cron job to use the resilient script
# Run this inside the container to update the cron configuration
#
# Usage (from inside container):
#   bash /root/Amadeus/saadaal-flood-forecaster/scripts/switch_to_resilient_cron.sh
#
# Usage (from host):
#   docker exec <container-id> bash /root/Amadeus/saadaal-flood-forecaster/scripts/switch_to_resilient_cron.sh

set -euo pipefail

CRON_FILE="/etc/cron.d/amadeus_saadaal_flood_forecaster_cron"

echo "========================================================================"
echo "SWITCHING CRON TO RESILIENT SCRIPT"
echo "========================================================================"
echo ""

# Check if cron file exists
if [ ! -f "$CRON_FILE" ]; then
    echo "❌ ERROR: Cron file not found at $CRON_FILE"
    exit 1
fi

echo "Current cron configuration:"
echo "---"
cat "$CRON_FILE"
echo "---"
echo ""

# Backup the current cron file
BACKUP_FILE="${CRON_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CRON_FILE" "$BACKUP_FILE"
echo "✅ Backed up current cron to: $BACKUP_FILE"
echo ""

# Replace amadeus_saadaal_flood_forecaster.sh with amadeus_saadaal_flood_forecaster_resilient.sh
sed -i 's/amadeus_saadaal_flood_forecaster\.sh/amadeus_saadaal_flood_forecaster_resilient.sh/g' "$CRON_FILE"

echo "New cron configuration:"
echo "---"
cat "$CRON_FILE"
echo "---"
echo ""

# Reload cron (the file in /etc/cron.d/ is automatically picked up, but restart to be sure)
echo "Reloading cron daemon..."
# Kill and restart cron to pick up changes
pkill cron || true
sleep 1
cron
echo "✅ Cron daemon restarted"
echo ""

echo "========================================================================"
echo "CRON SWITCHED TO RESILIENT SCRIPT"
echo "========================================================================"
echo ""
echo "The cron job will now use: amadeus_saadaal_flood_forecaster_resilient.sh"
echo ""
echo "To verify:"
echo "  cat $CRON_FILE"
echo ""
echo "To revert (use backup):"
echo "  cp $BACKUP_FILE $CRON_FILE"
echo "  pkill cron && cron"
echo ""
echo "========================================================================"

