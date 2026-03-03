#!/bin/bash
# Setup cron job for daily incremental indexing at 23:59

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_CMD="python3"
INCREMENTAL_SCRIPT="$PROJECT_ROOT/src/indexing/incremental_cli.py"
LOG_FILE="$PROJECT_ROOT/data/logs/incremental_cron.log"

# Create log directory
mkdir -p "$PROJECT_ROOT/data/logs"

# Backup current crontab
crontab -l > "$PROJECT_ROOT/data/backups/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true

# Add cron job (runs at 23:59 daily)
(crontab -l 2>/dev/null | grep -v "incremental_cli.py"; echo "59 23 * * * cd $PROJECT_ROOT && export PYTHONPATH=$PROJECT_ROOT && $PYTHON_CMD $INCREMENTAL_SCRIPT >> $LOG_FILE 2>&1") | crontab -

echo "✅ Cron job installed successfully"
echo "📅 Schedule: Daily at 23:59"
echo "📝 Log file: $LOG_FILE"
echo ""
echo "To verify:"
echo "  crontab -l"
echo ""
echo "To remove:"
echo "  crontab -l | grep -v 'incremental_cli.py' | crontab -"
echo ""
echo "To test manually:"
echo "  cd $PROJECT_ROOT && export PYTHONPATH=$PROJECT_ROOT && python3 src/indexing/incremental_cli.py --verbose"
