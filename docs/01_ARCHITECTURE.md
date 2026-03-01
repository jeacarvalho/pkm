## 📄 `docs/01_ARCHITECTURE.md`

```markdown
# 01 ARCHITECTURE - Obsidian RAG Connector

**Status:** Architecture Defined (v1.0)  
**Last Updated:** 2026-02-28

---

## 1. High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  Obsidian   │  │   PDF Books │  │   Gemini    │                      │
│  │   Vault     │  │   Library   │  │   API       │                      │
│  │  (3000+     │  │             │  │ (Translate) │                      │
│  │   notes)    │  │             │  │             │                      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                      │
└─────────┼────────────────┼────────────────┼─────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        INDEXING LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Vault Indexer (Sprint 01)                     │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Read .md  │→ │  Clean     │→ │  Embed     │                 │   │
│  │   │            │  │  Text      │  │  (bge-m3)  │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       VECTOR STORE                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      ChromaDB (Persistent)                        │   │
│  │   Collection: obsidian_notes                                      │   │
│  │   Metadata: file_path, note_title, tags, chunk_id                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       INGESTION LAYER (Sprint 02)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │  Read PDF  │→ │  Chunk     │→ │  Translate │→ │  Embed     │       │
│  │  (PyMuPDF) │  │  (512 tok) │  │  (Gemini)  │  │  (bge-m3)  │       │
│  └────────────┘  └────────────┘  └────────────┘  └─────┬──────┘       │
└────────────────────────────────────────────────────────┼────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      RETRIEVAL LAYER (Sprint 03)                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    3-Stage Filtering Pipeline                     │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Vector    │→ │  Re-Rank   │→ │  Filter    │                 │   │
│  │   │  Search    │  │  (Cross)   │  │  (>=0.75)  │                 │   │
│  │   │  (Top-20)  │  │  (Top-5)   │  │            │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     VALIDATION LAYER (Sprint 04)                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Ollama Local LLM Validation                    │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Read      │→ │  Evaluate  │→ │  Approve/  │                 │   │
│  │   │  Both      │  │  Semantics │  │  Reject    │                 │   │
│  │   │  Contents  │  │            │  │            │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER (Sprint 05)                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Obsidian Markdown Generation                     │   │
│  │   - Frontmatter with validation metadata                          │   │
│  │   - Links to validated notes [[Note Title]]                       │   │
│  │   - Book chunk excerpts with context                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Architecture

### 2.1 Vault Indexing Flow (Sprint 01)

```
[Obsidian .md files] 
       ↓
[Text Cleaning: Remove frontmatter, [[links]], code blocks]
       ↓
[Chunking: <1000 tokens = full note, >1000 = 800 token chunks]
       ↓
[Embedding: Ollama bge-m3 via /api/embeddings]
       ↓
[ChromaDB Upsert: ID = hash(file_path + chunk_id)]
       ↓
[Persistent Storage: data/vectors/chroma_db/]
```

### 2.2 Book Processing Flow (Sprint 02-05)

```
[PDF Book] 
       ↓
[PyMuPDF: Extract text by chapter/page]
       ↓
[Chunking: 512 tokens, 50 token overlap]
       ↓
[Language Detection + Translation (Gemini 1.5 Flash if needed)]
       ↓
[Embedding: Ollama bge-m3]
       ↓
[Vector Search: Top-20 similar notes from ChromaDB]
       ↓
[Re-Ranking: bge-reranker-v2-m3, keep score >= 0.75]
       ↓
[Ollama Validation: llama3.1 reads chunk + note content]
       ↓
[Output: Markdown with approved matches only]
```

---

## 3. Component Specifications

### 3.1 Embedding Model: `bge-m3`

| Property | Value |
|----------|-------|
| Provider | Ollama Local |
| Language | Multilingual (PT-BR optimized) |
| Context Window | 8192 tokens |
| Dimension | 1024 |
| API Endpoint | `http://localhost:11434/api/embeddings` |

**Why bge-m3:**
- Superior Portuguese performance vs. nomic-embed-text
- Compatible with Ollama local deployment
- Supports long context for dense notes

### 3.2 Re-Ranker: `bge-reranker-v2-m3`

| Property | Value |
|----------|-------|
| Provider | HuggingFace (local via sentence-transformers) |
| Type | Cross-Encoder |
| Input | (Query, Document) pair |
| Output | Similarity score 0-1 |
| Threshold | >= 0.75 for retention |

**Why Re-Ranking:**
- Bi-encoder (embedding) = fast but imprecise
- Cross-encoder (re-ranker) = slow but precise
- Eliminates false positives before LLM validation

### 3.3 Validation LLM: `llama3.1` or `mistral`

| Property | Value |
|----------|-------|
| Provider | Ollama Local |
| Model | llama3.1 (8B) or mistral (7B) |
| Input | Book chunk + Note content |
| Output | JSON: `{approved, confidence, reason}` |
| Temperature | 0.0 (deterministic) |

**Validation Prompt Structure:**
```
System: You are a skeptical knowledge curator. Reject weak matches.
User: Book: [chunk]. Note: [content]. Re-Rank Score: [score].
      Is there clear semantic relationship? Respond JSON only.
```

### 3.4 Translation: `gemini-1.5-flash`

| Property | Value |
|----------|-------|
| Provider | Google AI Studio API |
| Model | gemini-1.5-flash |
| Use Case | Translate non-Portuguese chunks |
| Rate Limit | 15 RPM (free tier) |
| Retry Logic | Exponential backoff (3 attempts) |

---

## 4. Database Schema (ChromaDB)

### Collection: `obsidian_notes`

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique: hash(file_path + chunk_id) |
| `document` | String | Cleaned text content |
| `embedding` | Vector | bge-m3 embedding (1024 dim) |
| `metadata.file_path` | String | Absolute path to .md file |
| `metadata.note_title` | String | Extracted from filename or frontmatter |
| `metadata.tags` | List[String] | Obsidian tags from content |
| `metadata.chunk_id` | Integer | Chunk sequence number (0, 1, 2...) |
| `metadata.token_count` | Integer | Number of tokens in chunk |
| `metadata.created_at` | Timestamp | Indexing timestamp |

### Collection: `processed_books`

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique: hash(book_path + chunk_id) |
| `document` | String | Translated chunk text |
| `embedding` | Vector | bge-m3 embedding (1024 dim) |
| `metadata.book_path` | String | Absolute path to PDF |
| `metadata.book_title` | String | Extracted from PDF metadata |
| `metadata.chunk_id` | Integer | Chunk sequence number |
| `metadata.original_language` | String | Detected language before translation |
| `metadata.translated` | Boolean | Whether translation was applied |
| `metadata.validation_status` | String | 'pending', 'approved', 'rejected' |

---

## 5. Module Responsibilities

| Module | Path | Responsibility |
|--------|------|----------------|
| `indexing` | `src/indexing/` | Vault note embedding and ChromaDB storage |
| `ingestion` | `src/ingestion/` | PDF parsing, chunking, translation |
| `retrieval` | `src/retrieval/` | Vector search, re-ranking, filtering |
| `validation` | `src/validation/` | Ollama LLM validation and approval |
| `output` | `src/output/` | Markdown generation for Obsidian |
| `utils` | `src/utils/` | Config, logging, database helpers |

---

## 6. Security & Compliance

| Aspect | Implementation |
|--------|----------------|
| API Keys | `.env` file (never commit) |
| Rate Limiting | Gemini: 15 RPM, Ollama: local (no limit) |
| Data Privacy | All processing local except translation |
| Logging | Sensitive data masked in logs |
| Error Handling | Retry logic with exponential backoff |

---

## 7. Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| Ollama API Unavailable | Retry 3x with 5s backoff, then log and skip |
| Gemini Rate Limit | Exponential backoff (10s, 20s, 40s) |
| PDF Parse Failure | Log error, continue with next book |
| ChromaDB Corruption | `--clean` flag to rebuild |
| Invalid Note Content | Skip note, log to `skipped_notes.log` |

---

## 8. Performance Targets

| Operation | Target |
|-----------|--------|
| Vault Indexing (3000 notes) | < 30 minutes |
| Book Chunk Embedding | < 1 second per chunk |
| Vector Search (Top-20) | < 100ms |
| Re-Ranking (20 candidates) | < 500ms |
| Ollama Validation | < 5 seconds per pair |
| End-to-End (100-page book) | < 60 minutes |
```

---