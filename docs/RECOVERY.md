# Recovery Procedures - Obsidian RAG

**Created:** 2026-03-02  
**Reason:** ChromaDB accidental deletion incident

---

## ⚠️ CRITICAL: ChromaDB Version Issue

**Problem:** Poetry has ChromaDB 0.4.24, but system Python has 1.5.1. They are incompatible!

**Solution:** Always use system Python (not Poetry) for this project:

```bash
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -c "import chromadb; print(chromadb.__version__)"  # Should be 1.5.1
```

---

## 🚨 Emergency: ChromaDB Deleted

### Option 1: Restore from Backup (FASTEST)

```bash
# 1. List available backups
ls -la data/backups/

# 2. Restore from latest backup
./scripts/restore_vectors.sh data/backups/vectors_20260302_120000

# 3. Verify restoration
python3 scripts/verify_index.py
```

**Time:** 5-10 minutes  
**Data Loss:** None (if backup exists)

### Option 2: Partial Re-Index (FOR TESTING)

```bash
# IMPORTANT: Use system Python, not Poetry!
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm

# Index just one folder for development
python3 -m src.indexing.vault_indexer --folder "30 LIDERANCA" --no-confirm

# Or limit to 100 notes
python3 -m src.indexing.vault_indexer --limit 100 --no-confirm
```

**Time:** 5-60 minutes  
**Use Case:** Continue development while full index rebuilds

### Option 3: Full Re-Index (LAST RESORT)

```bash
# IMPORTANT: Use system Python, not Poetry!
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm

# Start in background (overnight)
nohup python3 -m src.indexing.vault_indexer --clean --no-confirm > data/logs/indexing.out 2>&1 &
echo $! > data/logs/indexer.pid

# Monitor progress
tail -f data/logs/indexing.log

# Check progress (if available)
python3 -m src.indexing.vault_indexer --stats
```

**Time:** 10-12 hours (3570 notes, CPU-only)  
**Mitigation:** Run overnight or in background

---

## 📊 Estimated Re-build Times

| Component | Count | Time | Can Partial? |
|-----------|-------|------|--------------|
| Sprint 01 (Vault) | 3570 notes | 10-12h | ✅ Yes (--folder, --limit) |
| Sprint 02 (PDF) | 1 book | 30-60min | ✅ Yes (single book) |
| Sprint 03 (Retrieval) | N/A | No rebuild | N/A |
| Sprint 04 (Validation) | N/A | No rebuild | N/A |
| Sprint 05 (Output) | N/A | No rebuild | N/A |

---

## 🛡️ Prevention Measures

### Automatic Safeguards (Implemented)

- [x] `scripts/backup_vectors.sh` - Automatic backup before delete
- [x] `scripts/restore_vectors.sh` - Restore from backup
- [x] Confirmation prompt for `--clean` (YES_DELETE required)
- [x] `--folder` flag for partial indexing
- [x] `--limit` flag for testing
- [x] `docs/RECOVERY.md` - Recovery procedures
- [x] `scripts/verify_index.py` - Index health check

### Manual Checks (Required)

- [ ] Verify backup exists before `--clean`
- [ ] Check disk space before re-index
- [ ] Monitor Ollama during long operations
- [ ] Keep `data/logs/indexer.pid` for background jobs

---

## 📞 Contact & Escalation

If recovery fails:
1. Check `data/logs/indexing.log` for errors
2. Verify Ollama is running: `ollama list`
3. Check disk space: `df -h`
4. Review `docs/02_CURRENT_STATUS.md` for last known state
