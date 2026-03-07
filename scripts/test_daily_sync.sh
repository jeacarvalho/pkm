#!/bin/bash
# Test Daily Sync Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"

cd "$PROJECT_ROOT"

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source ".env"
    set +a
fi

export PYTHONPATH="$PROJECT_ROOT"

echo "Testing Daily Sync with limit 1..."
python3 src/topics/daily_sync.py \
    --vault-dir "$VAULT_PATH" \
    --limit 1 \
    --dry-run

echo ""
echo "Testing with actual extraction (limit 1)..."
timeout 120 python3 src/topics/daily_sync.py \
    --vault-dir "$VAULT_PATH" \
    --limit 1