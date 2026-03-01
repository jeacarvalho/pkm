## 📄 `docs/04_DATA_DICTIONARY.md`

```markdown
# Data Dictionary - Obsidian RAG Connector

**Last Updated:** 2026-02-28  
**Vector Store:** ChromaDB (Persistent)  
**Schema Version:** 001

---

## 1. Core Data Structures

### 1.1 ChromaDB Collection: `obsidian_notes`

Stores embedded chunks from Obsidian vault notes.

| Field | Type | Nullable | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | String | NOT NULL | Primary key (hash of file_path + chunk_id) | `a1b2c3d4e5f6_chunk_0` |
| `document` | String | NOT NULL | Cleaned text content (no frontmatter) | "Antifragilidade é um conceito..." |
| `embedding` | Vector | NOT NULL | bge-m3 embedding (1024 dimensions) | `[0.123, -0.456, ...]` |
| `metadata.file_path` | String | NOT NULL | Absolute path to .md file | `/vault/Notes/Antifragil.md` |
| `metadata.note_title` | String | NOT NULL | Extracted title from file or frontmatter | `Antifragilidade` |
| `metadata.tags` | List[String] | YES | Obsidian tags from content | `["#risco", "# Nassim"]` |
| `metadata.chunk_id` | Integer | NOT NULL | Chunk sequence number | `0`, `1`, `2` |
| `metadata.token_count` | Integer | NOT NULL | Number of tokens in chunk | `512` |
| `metadata.created_at` | Timestamp | NOT NULL | Indexing timestamp | `2026-02-28T10:00:00Z` |

**Indexes:**
- PRIMARY KEY: `id`
- METADATA FILTER: `file_path`, `note_title`, `tags`

**Foreign Keys:** None (document store)

---

### 1.2 ChromaDB Collection: `processed_books`

Stores embedded chunks from processed PDF books.

| Field | Type | Nullable | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | String | NOT NULL | Primary key (hash of book_path + chunk_id) | `book123_chunk_0` |
| `document` | String | NOT NULL | Translated chunk text | "Antifragility is a concept..." |
| `embedding` | Vector | NOT NULL | bge-m3 embedding (1024 dimensions) | `[0.123, -0.456, ...]` |
| `metadata.book_path` | String | NOT NULL | Absolute path to PDF file | `/books/Antifragile.pdf` |
| `metadata.book_title` | String | NOT NULL | Extracted from PDF metadata | `Antifragile` |
| `metadata.chunk_id` | Integer | NOT NULL | Chunk sequence number | `0`, `1`, `2` |
| `metadata.original_language` | String | YES | Detected language before translation | `en`, `pt`, `es` |
| `metadata.translated` | Boolean | NOT NULL | Whether translation was applied | `true`, `false` |
| `metadata.validation_status` | String | NOT NULL | Validation state | `pending`, `approved`, `rejected` |
| `metadata.created_at` | Timestamp | NOT NULL | Processing timestamp | `2026-02-28T10:00:00Z` |

---

### 1.3 Output: Obsidian Markdown Files

Generated markdown files with validated matches.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `frontmatter.validation_engine` | String | Validation system used | `ollama` |
| `frontmatter.validation_status` | String | Overall status | `approved` |
| `frontmatter.book_title` | String | Source book title | `Antifragile` |
| `frontmatter.processed_date` | Date | Processing date | `2026-02-28` |
| `frontmatter.ollama_model` | String | Model used for validation | `llama3.1` |
| `content.sections[].book_chunk` | String | Excerpt from book | "Chapter 1: ..." |
| `content.sections[].matched_notes` | List | Validated note links | `[[Antifragilidade]]` |
| `content.sections[].validation_reason` | String | Why match was approved | "Both discuss risk concepts" |
| `content.sections[].rerank_score` | Float | Re-ranker similarity score | `0.85` |

**Example Output:**

```markdown
---
validation_engine: ollama
validation_status: approved
book_title: Antifragile
processed_date: 2026-02-28
ollama_model: llama3.1
rerank_threshold: 0.75
---

# Conexões Validadas: Antifragile

## Capítulo 1 - Introdução

### Trecho do Livro
> "Antifragility is beyond resilience or robustness..."

### Notas Relacionadas (Validadas)

#### [[Antifragilidade]]
- **Re-Rank Score:** 0.85
- **Confiança Ollama:** 95
- **Motivo:** Ambos discutem o conceito de antifragilidade e resposta ao estresse

#### [[Gestão de Risco]]
- **Re-Rank Score:** 0.78
- **Confiança Ollama:** 88
- **Motivo:** Conceitos de risco e exposição a volatilidade

---
```

---

## 2. Data Types & Precision

### Embeddings

| Property | Value |
|----------|-------|
| Model | `bge-m3` via Ollama |
| Dimensions | 1024 |
| Data Type | Float32 |
| Normalization | L2 normalized |

### Text Content

| Property | Value |
|----------|-------|
| Encoding | UTF-8 |
| Max Chunk Size | 800 tokens (vault), 512 tokens (books) |
| Overlap | 100 tokens (vault), 50 tokens (books) |
| Tokenizer | tiktoken (cl100k_base) |

### Timestamps

| Property | Value |
|----------|-------|
| Format | ISO 8601 |
| Timezone | UTC |
| Example | `2026-02-28T10:00:00Z` |

### Scores & Metrics

| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `rerank_score` | Float | 0.0 - 1.0 | Cross-encoder similarity |
| `ollama_confidence` | Integer | 0 - 100 | LLM confidence percentage |
| `vector_similarity` | Float | 0.0 - 1.0 | Cosine similarity from ChromaDB |

---

## 3. Validation Schema (Ollama Output)

### JSON Response Format

```json
{
  "approved": true,
  "confidence": 95,
  "reason": "Ambos discutem o conceito de antifragilidade e resposta ao estresse"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approved` | Boolean | YES | Whether match is semantically valid |
| `confidence` | Integer | YES | Confidence score 0-100 |
| `reason` | String | YES | Human-readable explanation |

### Validation Rules

```python
from pydantic import BaseModel, Field

class ValidationResponse(BaseModel):
    approved: bool = Field(..., description="Whether match is approved")
    confidence: int = Field(..., ge=0, le=100, description="Confidence 0-100")
    reason: str = Field(..., min_length=10, description="Explanation")

    class Config:
        schema_extra = {
            "example": {
                "approved": True,
                "confidence": 95,
                "reason": "Both discuss risk management concepts"
            }
        }
```

---

## 4. Common Queries (ChromaDB)

### Get Similar Notes for a Chunk

```python
from chromadb import Collection

collection: Collection = chroma_client.get_collection("obsidian_notes")

results = collection.query(
    query_embeddings=[chunk_embedding],
    n_results=20,
    include=["documents", "metadatas", "distances"]
)
```

### Filter by Tags

```python
results = collection.query(
    query_embeddings=[chunk_embedding],
    n_results=20,
    where={
        "tags": {"$in": ["#risco", "#gestao"]}
    }
)
```

### Filter by File Path

```python
results = collection.query(
    query_embeddings=[chunk_embedding],
    n_results=20,
    where={
        "file_path": {"$contains": "/Notes/"}
    }
)
```

---

## 5. Data Flow Diagrams

### 5.1 Vault Indexing Flow

```
[Obsidian .md File]
        ↓
[Read Content]
        ↓
[Clean: Remove frontmatter, [[links]], code]
        ↓
[Chunk: 800 tokens, 100 overlap]
        ↓
[Embed: Ollama bge-m3]
        ↓
[ChromaDB Upsert: obsidian_notes collection]
        ↓
[Persistent Storage: data/vectors/chroma_db/]
```

### 5.2 Book Processing Flow

```
[PDF Book]
        ↓
[Extract Text: PyMuPDF]
        ↓
[Chunk: 512 tokens, 50 overlap]
        ↓
[Detect Language]
        ↓
[Translate if needed: Gemini 1.5 Flash]
        ↓
[Embed: Ollama bge-m3]
        ↓
[Vector Search: Top-20 from obsidian_notes]
        ↓
[Re-Rank: bge-reranker-v2-m3, threshold 0.75]
        ↓
[Validate: Ollama llama3.1]
        ↓
[Output: Markdown with approved matches]
```

---

## 6. Notes & Best Practices

### Embedding Consistency

| Rule | Implementation |
|------|----------------|
| Same model for all embeddings | Never mix `bge-m3` with other models |
| Same preprocessing | Clean text before embedding (no markdown) |
| Same tokenization | Use consistent tokenizer (tiktoken) |

### Chunking Best Practices

| Aspect | Recommendation |
|--------|----------------|
| Vault notes | 800 tokens if > 1000, else full note |
| Book chunks | Always 512 tokens |
| Overlap | 10-15% of chunk size |
| Boundaries | Prefer sentence boundaries over hard cuts |

### Metadata Standards

| Field | Format | Example |
|-------|--------|---------|
| `file_path` | Absolute path | `/Users/name/Vault/Notes/Test.md` |
| `tags` | List with # prefix | `["#risco", "#gestao"]` |
| `created_at` | ISO 8601 UTC | `2026-02-28T10:00:00Z` |

### Error Handling

| Error | Action |
|-------|--------|
| Failed to parse PDF | Log to `pdf_errors.log`, skip file |
| Ollama API timeout | Retry 3x, then skip chunk |
| Gemini rate limit | Exponential backoff (10s, 20s, 40s) |
| Invalid note content | Log to `skipped_notes.log`, continue |

---

## 7. Storage Locations

| Data Type | Path | Persistence |
|-----------|------|-------------|
| ChromaDB | `data/vectors/chroma_db/` | Persistent on disk |
| Output Markdown | `data/processed/` | Persistent (user vault) |
| Logs | `data/logs/` | Persistent (rotating) |
| Cache | `data/cache/` | Can be cleared |
| Environment | `.env` | Never commit to git |

---

## 8. Data Retention & Cleanup

| Operation | Command | Effect |
|-----------|---------|--------|
| Full Re-index | `python vault_indexer.py --clean` | Deletes ChromaDB, rebuilds |
| Clear Processed | `rm -rf data/processed/*` | Removes output files |
| Clear Logs | `rm -rf data/logs/*` | Removes log files |
| Clear Cache | `rm -rf data/cache/*` | Removes temporary files |

**Warning:** `--clean` flag will delete all embeddings. Use only when:
- Changing embedding model
- Recovering from corruption
- Full vault restructure
```

---