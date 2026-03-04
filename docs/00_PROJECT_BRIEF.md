---

## 📄 `docs/00_PROJECT_BRIEF.md`

```markdown
# Project Brief: Obsidian RAG Connector

**Status:** Sprint 00 - Documentation Complete ✅  
**Last Updated:** 2026-02-28  
**Next Phase:** Sprint 01 - Vault Re-Indexing  
**Agent Context:** OpenCode (minima-m2,5-free)

---

## Quick Start for New Agents

```bash
# 1. Pull required models (embedding via Ollama, validation via Gemini API)
ollama pull bge-m3
# Validation uses Gemini API (gemini-2.5-flash-lite)

# 2. Install Python dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your VAULT_PATH and API keys

# 4. Run Sprint 01 (Vault Indexing)
# IMPORTANT: Use system Python (not Poetry) due to ChromaDB version incompatibility
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.indexing.vault_indexer --folder "30 LIDERANCA"

# 5. Run tests
python3 -m pytest tests/unit/ -v
```

---

## Objective

Build a Retrieval-Augmented Generation (RAG) pipeline that connects PDF books to an existing Obsidian vault (3000+ notes). The system must:

1. **Ingest** PDF books (chunking, translation if needed)
2. **Retrieve** semantically similar notes from the vault
3. **Re-Rank** candidates to eliminate false positives
4. **Validate** matches with Gemini (semantic curation)
5. **Output** validated connections as Obsidian Markdown

**Critical Rule:** No match is considered valid without explicit Ollama approval after reading both the book chunk and the note content.

---

## Tech Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Language | Python 3.10+ | ✅ |
| Package Manager | Poetry (for deps) / System Python (for run) | ⚠️ Use PYTHONPATH |
| Embedding Model | Ollama `bge-m3` | ✅ |
| Re-Ranker | HuggingFace `bge-reranker-v2-m3` | ✅ |
| Vector Store | ChromaDB 1.5.1 (System Python) | ✅ |
| Translation | Google Gemini 1.5 Flash | ✅ |
| Validation LLM | Gemini `gemini-2.5-flash-lite` | ✅ |
| PDF Parsing | PyMuPDF (fitz) | ✅ |
| Testing | Pytest | ⏭️ |
| Containerization | Docker (optional for Ollama) | ⏭️ |

---

## Critical Business Rules

### 1. No False Positives (MANDATORY) ✅
**Definition:** A match is only valid if Ollama explicitly approves it after reading both contents.

**Implementation:**
- 3-stage filtering: Vector Search → Re-Ranker → LLM Validation
- Re-Ranker threshold: score >= 0.75
- Ollama must respond with JSON: `{"approved": boolean, "confidence": 0-100, "reason": "string"}`
- Log all rejected matches for audit

**Validation:**
```python
# All matches in output must have approved == true
assert all(match['approved'] for match in output_matches)
```

### 2. Embedding Consistency ✅
**Definition:** All embeddings (vault notes + book chunks) must use the SAME model.

**Implementation:**
- Vault notes: `bge-m3` via Ollama
- Book chunks: `bge-m3` via Ollama
- Model cannot change between indexing and retrieval

### 3. Language Handling ✅
**Definition:** Book content must match vault language for accurate embedding.

**Implementation:**
- Detect chunk language
- If different from vault (e.g., English book, Portuguese vault), translate with Gemini 1.5 Flash BEFORE embedding
- Store original + translated text in metadata

### 4. Chunk Density ✅
**Definition:** Chunks must be semantically dense for accurate retrieval.

**Implementation:**
- Vault notes: Full note if < 1000 tokens, else chunk at 800 tokens
- Book chunks: 512 tokens with 50 token overlap
- Remove markdown syntax, keep semantic content

---

## Project Phases

| Phase | Sprint | Status | Description |
|-------|--------|--------|-------------|
| Phase 0 | Sprint 00 | ✅ COMPLETE | Documentation & Context Setup |
| Phase 1 | Sprint 01 | ✅ COMPLETE | Vault Re-Indexing (10144 chunks, 3570 notes) |
| Phase 2 | Sprint 02 | ✅ COMPLETE | PDF Ingestion & Translation |
| Phase 3 | Sprint 03 | ✅ COMPLETE | Retrieval & Re-Ranking (2-stage pipeline) |
| Phase 4 | Sprint 04 | ✅ COMPLETE | Ollama Validation Pipeline |
| Phase 5 | Sprint 05 | ✅ COMPLETE | Output Generation (Markdown) |
| Phase 6 | Sprint 06 | ✅ COMPLETE | Chapter-Based Processing + Vault Integration |

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

### Current Strategy: Sprint 02 Starts While Sprint 01 Completes

**Rationale:**
- Sprint 01 is hardware-bound (Ollama embeddings on CPU)
- Sprint 02 processes PDFs and doesn't need ChromaDB to be populated
- This saves ~4-6 hours of idle time

**Risk Mitigation:**
- Sprint 03 will wait for BOTH Sprint 01 and 02 to complete
- If Sprint 01 fails, we can re-index without losing Sprint 02 work
- Modules are independent (no shared state until Sprint 03)

**Expected Timeline:**
- Sprint 01: Complete in background (~6-10 hours total)
- Sprint 02: Develop now (~2-3 hours)
- Sprint 03: Start after both complete

See `docs/08_SPRINT_DEPENDENCIES.md` for complete dependency graph.

---

## Completed Work Log

### Phase 0: Documentation (COMPLETED 2026-02-28)
- ✅ `00_PROJECT_BRIEF.md` - Project overview and rules
- ✅ `01_ARCHITECTURE.md` - System architecture and flow
- ✅ `02_CURRENT_STATUS.md` - Current implementation status
- ✅ `03_CODING_STANDARDS.md` - Code standards and conventions
- ✅ `04_DATA_DICTIONARY.md` - Data schemas and structures

---

## Next: Phase 1 - Vault Re-Indexing

**Tasks:**
- Create `vault_indexer.py` script
- Configure ChromaDB persistent storage
- Implement Ollama embedding integration (`bge-m3`)
- Add progress tracking and error logging
- Create cleanup option (`--clean` flag)

**Deliverables:**
- `src/indexing/vault_indexer.py`
- `tests/unit/test_indexing.py`
- `data/vectors/chroma_db/` (persistent storage)

---

## Context for Future Agents

- Vault has 3000+ notes in Portuguese
- All notes need re-indexing with `bge-m3`
- ChromaDB is the vector store (persistent on disk)
- Ollama must be running locally with required models
- Translation uses Gemini 1.5 Flash (API key required)
- Output format: Obsidian Markdown with frontmatter

---

## Key Files (To Be Created)

```
src/
├── indexing/
│   ├── vault_indexer.py      # Sprint 01
│   └── __init__.py
├── ingestion/
│   ├── pdf_processor.py      # Sprint 02
│   ├── translator.py         # Sprint 02
│   └── __init__.py
├── retrieval/
│   ├── vector_search.py      # Sprint 03
│   ├── reranker.py           # Sprint 03
│   └── __init__.py
├── validation/
│   ├── gemini_validator.py   # Sprint 04
│   └── __init__.py
├── output/
│   ├── markdown_generator.py # Sprint 05
│   └── __init__.py
└── utils/
    ├── config.py
    ├── database.py
    └── logging.py

tests/
├── unit/
│   ├── test_indexing.py
│   ├── test_ingestion.py
│   └── test_validation.py
└── integration/
    └── test_pipeline.py

data/
├── vectors/                  # ChromaDB storage
├── processed/                # Output markdown files
└── logs/                     # Execution logs

docs/
├── 00_PROJECT_BRIEF.md
├── 01_ARCHITECTURE.md
├── 02_CURRENT_STATUS.md
├── 03_CODING_STANDARDS.md
└── 04_DATA_DICTIONARY.md
```

---

## Quick Reference

### Check Ollama Models (for embeddings)
```bash
ollama list
# Should show: bge-m3
```

### Check Gemini API
```bash
echo $GEMINI_API_KEY  # Should not be empty
```

### Check ChromaDB Status
```bash
ls -la data/vectors/
```

### Run Tests
```bash
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v
```

### View Logs
```bash
tail -f data/logs/indexing.log
```
```

---