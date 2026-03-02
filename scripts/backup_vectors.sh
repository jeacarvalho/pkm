#!/bin/bash
# scripts/backup_vectors.sh
# Backup automático do ChromaDB antes de operações destrutivas

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

SOURCE_DIR="data/vectors/chroma_db"
BACKUP_DIR="data/backups"
MAX_BACKUPS=3

echo "🔄 Starting ChromaDB backup..."

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/vectors_$TIMESTAMP"

if [ -d "$SOURCE_DIR" ] && [ "$(ls -A $SOURCE_DIR 2>/dev/null)" ]; then
    mkdir -p "$BACKUP_PATH"
    cp -r "$SOURCE_DIR"/* "$BACKUP_PATH/"
    echo "✅ Backup created: $BACKUP_PATH"
    
    # Cleanup old backups (keep last MAX_BACKUPS)
    cd "$BACKUP_DIR"
    ls -dt vectors_*/ 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -rf
    echo "🧹 Old backups cleaned (keeping last $MAX_BACKUPS)"
else
    echo "⚠️  Source directory is empty. No backup needed."
fi

echo "📊 Backup size: $(du -sh "$BACKUP_PATH" 2>/dev/null | cut -f1 || echo 'N/A')"
