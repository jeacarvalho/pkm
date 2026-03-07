#!/bin/bash
# Daily Sync Script for Topic Classification v2.1
# Runs once per day (at night) to process new and modified notes

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="$PROJECT_ROOT/data/logs/topics/daily_sync"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Create log directory
mkdir -p "$LOG_DIR"

# Log file for this run
LOG_FILE="$LOG_DIR/daily_sync_${TIMESTAMP}.log"

echo "==========================================" | tee -a "$LOG_FILE"
echo "Daily Sync v2.1 - $(date)" | tee -a "$LOG_FILE"
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

# Run daily sync
echo "Starting daily sync..." | tee -a "$LOG_FILE"
python3 src/topics/daily_sync.py \
    --vault-dir "$VAULT_PATH" \
    --limit 2 \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Daily Sync completed with exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Send notification (optional - uncomment if you have notify-send)
# if [ $EXIT_CODE -eq 0 ]; then
#     notify-send "Daily Sync Completed" "Topic classification sync completed successfully."
# else
#     notify-send "Daily Sync Failed" "Topic classification sync failed. Check logs."
# fi

exit $EXIT_CODE