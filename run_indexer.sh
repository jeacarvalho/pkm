#!/bin/bash
# run_indexer.sh - Safe wrapper for vault indexing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR"

echo "🚀 Starting Vault Indexer..."
echo "   Time: $(date)"
echo "   Arguments: $@"
echo ""

# Check if Ollama is running
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Install from: https://ollama.ai"
    exit 1
fi

if ! ollama list &> /dev/null; then
    echo "❌ Ollama is not running. Start with: ollama serve"
    exit 1
fi

# Check if bge-m3 model exists
if ! ollama list | grep -q bge-m3; then
    echo "❌ bge-m3 model not found. Pull with: ollama pull bge-m3"
    exit 1
fi

echo "✅ Ollama is running with bge-m3 model"

# Check disk space
if [ -d "data/vectors/chroma_db" ]; then
    AVAILABLE=$(df -m "data" | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE" -lt 5000 ]; then
        echo "⚠️  WARNING: Less than 5GB disk space available"
        echo "   Current: ${AVAILABLE}MB"
        echo "   Recommended: 5000MB+"
    fi
fi

# Run indexer with all arguments
python3 -m src.indexing.vault_indexer "$@"

echo ""
echo "✅ Indexer completed at $(date)"
echo "   Verify with: python3 scripts/verify_index.py"
