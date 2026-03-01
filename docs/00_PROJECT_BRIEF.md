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
# 1. Pull required Ollama models
ollama pull bge-m3
ollama pull bge-reranker-v2-m3
ollama pull llama3.1

# 2. Install Python dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your VAULT_PATH and API keys

# 4. Run Sprint 01 (Vault Indexing)
poetry run python src/indexing/vault_indexer.py --clean

# 5. Run tests
poetry run pytest tests/ -v
```

---

## Objective

Build a Retrieval-Augmented Generation (RAG) pipeline that connects PDF books to an existing Obsidian vault (3000+ notes). The system must:

1. **Ingest** PDF books (chunking, translation if needed)
2. **Retrieve** semantically similar notes from the vault
3. **Re-Rank** candidates to eliminate false positives
4. **Validate** matches with Ollama (semantic curation)
5. **Output** validated connections as Obsidian Markdown

**Critical Rule:** No match is considered valid without explicit Ollama approval after reading both the book chunk and the note content.

---

## Tech Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Language | Python 3.10+ | ✅ |
| Package Manager | Poetry | ✅ |
| Embedding Model | Ollama `bge-m3` | ⏭️ |
| Re-Ranker | HuggingFace `bge-reranker-v2-m3` | ⏭️ |
| Vector Store | ChromaDB (Persistent) | ⏭️ |
| Translation | Google Gemini 1.5 Flash | ⏭️ |
| Validation LLM | Ollama `llama3.1` or `mistral` | ⏭️ |
| PDF Parsing | PyMuPDF (fitz) | ⏭️ |
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
| Phase 1 | Sprint 01 | ⏭️ NEXT | Vault Re-Indexing (Embeddings) |
| Phase 2 | Sprint 02 | ⏭️ FUTURE | PDF Ingestion & Translation |
| Phase 3 | Sprint 03 | ⏭️ FUTURE | Retrieval & Re-Ranking |
| Phase 4 | Sprint 04 | ⏭️ FUTURE | Ollama Validation Pipeline |
| Phase 5 | Sprint 05 | ⏭️ FUTURE | Output & Obsidian Integration |

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
│   ├── ollama_validator.py   # Sprint 04
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

### Check Ollama Models
```bash
ollama list
# Should show: bge-m3, bge-reranker-v2-m3, llama3.1
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