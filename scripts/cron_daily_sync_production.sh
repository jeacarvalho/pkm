#!/bin/bash
# Cron Job Script for Daily Sync v2.1
# Executa o sistema de sincronização diária às 2:00 AM

set -e  # Exit on error
set -u  # Treat unset variables as error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PRODUCTION_SCRIPT="$SCRIPT_DIR/production_daily_sync.sh"
LOG_DIR="$PROJECT_ROOT/data/logs/cron"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/cron_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Cron Job: Daily Sync v2.1"
echo "Start Time: $(date)"
echo "=========================================="

# Check if production script exists
if [ ! -f "$PRODUCTION_SCRIPT" ]; then
    echo "ERROR: Production script not found: $PRODUCTION_SCRIPT"
    exit 1
fi

# Make sure script is executable
chmod +x "$PRODUCTION_SCRIPT"

# Run production script
echo "Running production daily sync..."
"$PRODUCTION_SCRIPT"

EXIT_CODE=$?

echo "=========================================="
echo "Cron Job Completed"
echo "End Time: $(date)"
echo "Exit Code: $EXIT_CODE"
echo "=========================================="

# Cleanup old logs (keep last 7 days)
find "$LOG_DIR" -name "cron_*.log" -mtime +7 -delete 2>/dev/null || true

exit $EXIT_CODE