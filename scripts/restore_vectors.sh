#!/bin/bash
# scripts/restore_vectors.sh
# Restaurar ChromaDB a partir de backup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

BACKUP_PATH=$1
TARGET_DIR="data/vectors/chroma_db"

if [ -z "$BACKUP_PATH" ]; then
    echo "❌ Usage: ./restore_vectors.sh <backup_path>"
    echo ""
    echo "Available backups:"
    if [ -d "data/backups" ]; then
        ls -la data/backups/
    else
        echo "No backups directory found"
    fi
    exit 1
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup path not found: $BACKUP_PATH"
    exit 1
fi

echo "⚠️  WARNING: This will OVERWRITE current ChromaDB data!"
echo "Target: $TARGET_DIR"
echo "Source: $BACKUP_PATH"
echo ""
echo "Type 'YES_RESTORE' to confirm:"
read -r confirmation

if [ "$confirmation" != "YES_RESTORE" ]; then
    echo "❌ Restore cancelled."
    exit 0
fi

# Backup current state first
echo "🔄 Creating backup of current state before restore..."
./scripts/backup_vectors.sh || true

# Restore
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -r "$BACKUP_PATH"/* "$TARGET_DIR/"

echo "✅ Restore complete from: $BACKUP_PATH"
echo "📊 Restored size: $(du -sh "$TARGET_DIR" | cut -f1)"
