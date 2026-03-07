#!/bin/bash
# Cron job script for Daily Sync v2.1
# Runs once per day at 2:00 AM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="$PROJECT_ROOT/data/logs/topics/daily_sync"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Create log directory
mkdir -p "$LOG_DIR"

# Log file for this run
LOG_FILE="$LOG_DIR/cron_daily_sync_${TIMESTAMP}.log"

echo "==========================================" | tee -a "$LOG_FILE"
echo "Cron Daily Sync v2.1 - $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found at $PROJECT_ROOT/.env" | tee -a "$LOG_FILE"
    exit 1
fi

# Load environment variables
set -a
source ".env"
set +a

# Check if vault exists
if [ ! -d "$VAULT_PATH" ]; then
    echo "ERROR: Vault not found at $VAULT_PATH" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Project root: $PROJECT_ROOT" | tee -a "$LOG_FILE"
echo "Vault path: $VAULT_PATH" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run daily sync (no limit, actual processing)
echo "Starting daily sync (cron job)..." | tee -a "$LOG_FILE"
python3 src/topics/daily_sync.py \
    --vault-dir "$VAULT_PATH" \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Cron Daily Sync completed with exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Send email notification if configured
if [ -n "$CRON_NOTIFICATION_EMAIL" ]; then
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Daily Sync completed successfully at $(date)" | mail -s "Daily Sync Success" "$CRON_NOTIFICATION_EMAIL"
    else
        echo "Daily Sync failed with exit code $EXIT_CODE at $(date)" | mail -s "Daily Sync Failed" "$CRON_NOTIFICATION_EMAIL"
    fi
fi

exit $EXIT_CODE