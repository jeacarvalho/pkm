# Sprint Dependencies - Obsidian RAG

**Last Updated:** 2026-03-02  
**Status:** Active

---

## Dependency Graph

```
Sprint 00 (Docs) ✅
       ↓
Sprint 01 (Vault Indexing) ✅ COMPLETE (10144 chunks, 3570 notes)
       ↓
Sprint 02 (PDF Ingestion) ✅ COMPLETE
       ↓
Sprint 03 (Retrieval) ✅ COMPLETE
       ↓
Sprint 04 (Validation) ✅ COMPLETE
       ↓
Sprint 05 (Output) ✅ COMPLETE
```

## Current Status (2026-03-03)

| Sprint | Progress | Status | Next Action |
|--------|----------|--------|-------------|
| Sprint 01 | 10144 chunks (3570 notes) | ✅ COMPLETE | Ready for production |
| Sprint 02 | Code + Tests ready | ✅ COMPLETE | Ready |
| Sprint 03 | Pipeline implemented | ✅ COMPLETE | Full vault coverage |
| Sprint 04 | Complete | ✅ COMPLETE | Working |
| Sprint 05 | Complete | ✅ COMPLETE | Validated end-to-end |

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Can run parallel / No dependencies |
| 🔄 | In Progress |
| ⏸️ | Blocked (waiting for dependencies) |
| → | Sequential dependency |
| ↘ | Parallel possible |

---

## ✅ Full Index Status

**All Sprints Operational with Complete Coverage:**
- Retrieval: 10144 chunks indexed (100% coverage)
- Validation: Matches from all 3570 notes
- Output: Full vault connections available

**Test Validation:**
- PDF Tested: "A Educação Para Além do Capital" (Mészáros)
- Result: 5 validated matches (92% confidence)
- Sample Match: "2001robinson-Out of Our Minds"

---

## Parallel Execution Strategy

| Sprint | Can Run Parallel? | Blocks | Blocked By | Notes |
|--------|-------------------|--------|------------|-------|
| Sprint 00 | N/A (first) | Sprint 01 | — | Documentation complete |
| Sprint 01 | N/A | Sprint 03 | — | Hardware-bound (Ollama) |
| Sprint 02 | ✅ YES | Sprint 03 | — | Independent of ChromaDB |
| Sprint 03 | ❌ NO | Sprint 04 | Sprint 01 + 02 | Needs populated vectors |
| Sprint 04 | ❌ NO | Sprint 05 | Sprint 03 | Needs retrieval pipeline |
| Sprint 05 | ❌ NO | — | Sprint 04 | Final output generation |

### Current Strategy
**Sprint 02 starts while Sprint 01 completes in background**

**Rationale:**
- Sprint 01 is hardware-bound (Ollama embeddings on CPU)
- Sprint 02 processes PDFs and doesn't need ChromaDB
- This saves ~4-6 hours of idle time

---

## Dependency Rules

### Rule 1: Sprint 02 Can Start Anytime
- PDF processing is independent of vault indexing
- Translation (Gemini API) doesn't depend on embeddings
- No shared state until Sprint 03

### Rule 2: Sprint 03 Requires Both Sprint 01 + 02
- Needs ChromaDB populated with vault notes (Sprint 01)
- Needs PDF chunks processed and translated (Sprint 02)
- Re-ranker needs both sources available

### Rule 3: Sprint 04 Depends on Sprint 03
- Validation needs retrieval results
- Ollama must compare book chunks with vault notes
- Can't validate without matches to validate

### Rule 4: Sprint 05 Depends on Sprint 04
- Output generation needs validated matches
- Markdown links need approved connections
- Final deliverable requires all previous steps

---

## Hardware Considerations

| Component | Hardware Demand | Mitigation |
|-----------|-----------------|------------|
| Ollama Embeddings (Sprint 01) | **HIGH** (CPU/GPU) | Run in background, batch processing |
| Gemini Translation (Sprint 02) | **LOW** (API) | No local hardware impact |
| Re-Ranker (Sprint 03) | **MEDIUM** (CPU) | Process in batches |
| Ollama Validation (Sprint 04) | **MEDIUM** (CPU/GPU) | Limit concurrent requests |
| Markdown Output (Sprint 05) | **LOW** (I/O) | Minimal hardware requirements |

### Optimization Strategies

1. **Sprint 01 (Embeddings)**
   - Run overnight or in background
   - Use `--folder` flag to index subsets during development
   - Consider GPU if available

2. **Sprint 02 (PDF)**
   - Can run immediately (no hardware bottlenecks)
   - API rate limits are the only constraint
   - Process multiple PDFs in parallel

3. **Sprint 03 (Retrieval)**
   - Wait for Sprint 01 completion
   - ChromaDB queries are fast (< 100ms)
   - Re-ranking is the slowest step

4. **Sprint 04 (Validation)**
   - Ollama calls are the bottleneck
   - Can batch validate multiple matches
   - Consider parallel Ollama instances

---

## Risk Mitigation

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Sprint 01 fails mid-way | High | Can restart with `--clean`, no data loss | ✅ |
| **Accidental data deletion** | **CRITICAL** | **Backup before `--clean`, confirmation required** | ✅ |
| Hardware overheating | Medium | Add delays, monitor temperatures | ✅ |
| Ollama crashes | Medium | Implement retry logic with backoff | ✅ |
| **ChromaDB version mismatch** | **CRITICAL** | **Use system Python with ChromaDB 1.5.1** | ✅ **NEW** |
| JSON parsing errors in Ollama | Medium | Simplified prompt, no markdown | ✅ |
| Sprint 02 takes longer | Low | Doesn't block Sprint 01 | ✅ |
| Sprint 03 needs both | Medium | Clear acceptance criteria for 01+02 | ✅ |

## Recovery Time Estimates

| Operation | Time | When to Use |
|-----------|------|-------------|
| Restore from backup | 5-10 min | After accidental delete |
| Partial re-index (--folder) | 1-2 hours | Development/testing |
| Partial re-index (--limit 100) | 5-10 min | Quick tests |
| Full re-index | 10-12 hours | Last resort |

---

## Execution Timeline (Estimated)

```
Day 1 (Today)
├── Sprint 01: Start indexing in background
├── Sprint 02: Start PDF processing
└── Status: Both running in parallel

Day 1-2
├── Sprint 01: Continue indexing (~6-10 hours total)
├── Sprint 02: Complete PDF processing (~2-3 hours)
└── Status: Sprint 02 done, Sprint 01 ongoing

Day 2
├── Sprint 01: Complete
├── Sprint 03: Start retrieval & re-ranking
└── Status: Sprint 03 in progress

Day 2-3
├── Sprint 03: Complete (~4-6 hours)
├── Sprint 04: Start validation
└── Status: Sprint 04 in progress

Day 3
├── Sprint 04: Complete (~3-4 hours)
├── Sprint 05: Start output generation
└── Status: Sprint 05 in progress

Day 3-4
├── Sprint 05: Complete (~2-3 hours)
└── Status: ALL SPRINTS COMPLETE ✅
```

**Total Project Time:** ~3-4 days (with parallel execution)
**Sequential Time:** ~5-7 days (without parallel execution)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-01 | Run Sprint 01 + 02 in parallel | Sprint 01 hardware-bound, Sprint 02 independent |
| 2026-03-01 | Sprint 03 waits for both 01 + 02 | Needs both data sources for retrieval |
| 2026-03-01 | Sprint 04+05 sequential | Each depends on previous output |

---

## Current Status

| Sprint | Status | Notes |
|--------|--------|-------|
| Sprint 01 | ✅ COMPLETE | 10144 chunks (3570 notes) |
| Sprint 02 | ✅ COMPLETE | Working |
| Sprint 03 | ✅ COMPLETE | Working |
| Sprint 04 | ✅ COMPLETE | Working |
| Sprint 05 | ✅ COMPLETE | Working |

---

## Quick Reference

### Verify Index
```bash
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 scripts/verify_index.py
```

### Start Sprint 01 (Background)
```bash
nohup ./run_indexer.sh --clean > data/logs/indexing.out 2>&1 &
echo $! > data/logs/indexer.pid
```

### Start Sprint 02
```bash
# IMPORTANT: Use system Python (not Poetry)
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.ingestion.pdf_processor --book /path/to/book.pdf
```

### Check Dependencies
```bash
# Verify Sprint 01 complete
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.indexing.vault_indexer --stats

# Verify Sprint 02 complete
ls -la data/processed/
```
