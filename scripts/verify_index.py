#!/usr/bin/env python3
"""Verify ChromaDB index status and health."""

import sys
from pathlib import Path


def get_directory_size(path: Path) -> str:
    """Get human-readable directory size."""
    import subprocess

    try:
        result = subprocess.run(
            ["du", "-sh", str(path)],
            capture_output=True,
            text=True,
        )
        return result.stdout.split()[0]
    except Exception:
        return "Unknown"


def verify_index() -> bool:
    """Check index health and statistics."""
    chroma_dir = Path("data/vectors/chroma_db")
    backup_dir = Path("data/backups")

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         ChromaDB Index Verification                      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Check ChromaDB directory
    if not chroma_dir.exists():
        print("❌ ChromaDB directory NOT FOUND")
        print("   Run: ./run_indexer.sh --clean")
        return False

    print(f"✅ ChromaDB directory: {chroma_dir}")
    print(f"   Size: {get_directory_size(chroma_dir)}")

    # Check backups
    if backup_dir.exists():
        backups = list(backup_dir.glob("vectors_*"))
        if backups:
            print(f"✅ Backups available: {len(backups)}")
            for b in sorted(backups)[-3:]:
                print(f"   - {b.name} ({get_directory_size(b)})")
        else:
            print("⚠️  No backups found in data/backups/")
    else:
        print("⚠️  No backups directory found")

    # Try to connect and count
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.get_collection("obsidian_notes")
        count = collection.count()

        print(f"✅ Collection 'obsidian_notes': {count} chunks")
        print(f"   Expected: ~10144 chunks (3570 notes)")

        if count < 1000:
            print("⚠️  WARNING: Index seems incomplete!")
            print("   Full re-index recommended")
        elif count >= 10000:
            print("✅ Index appears complete!")
        else:
            print("⚠️  Index is partial (expected ~10144)")

        return True

    except Exception as e:
        print(f"❌ Error connecting to ChromaDB: {e}")
        return False


if __name__ == "__main__":
    success = verify_index()
    sys.exit(0 if success else 1)
