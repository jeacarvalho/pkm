## 📄 `docs/03_CODING_STANDARDS.md`

```markdown
# Coding Standards - Obsidian RAG Connector

**Language:** Python 3.10+  
**Last Updated:** 2026-03-02

---

## ⚠️ IMPORTANT: Python Environment

**CRITICAL:** Due to ChromaDB version incompatibility (Poetry has 0.4.24, System Python has 1.5.1),
**ALWAYS use system Python with PYTHONPATH** instead of Poetry:

```bash
# ✅ CORRECT (use system Python)
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.indexing.vault_indexer --stats

# ❌ WRONG (Poetry has incompatible ChromaDB version)
poetry run python src/indexing/vault_indexer.py --stats
```

---

## 1. Language & Style

### Python Version

| Requirement | Value |
|-------------|-------|
| Minimum | Python 3.10 |
| Recommended | Python 3.11+ |
| Version Pinning | `python = "^3.10"` in `pyproject.toml` |

### PEP 8 Compliance

| Rule | Value |
|------|-------|
| Line Length | 88 characters (Black default) |
| Formatter | Black (`poetry run black .`) |
| Import Sorter | isort (`poetry run isort .`) |
| Linter | ruff or flake8 |

### Type Hints (MANDATORY)

All Python files MUST include type hints for:
- Function parameters
- Function return values
- Class attributes
- Variable annotations where beneficial

```python
# ✅ GOOD
def calculate_similarity(query: str, document: str) -> float:
    """Calculate semantic similarity between query and document."""
    ...

def get_chunks(text: str, max_tokens: int = 512) -> List[str]:
    """Split text into chunks of max_tokens."""
    ...

# ❌ BAD
def calculate_similarity(query, document):
    ...

def get_chunks(text, max_tokens=512):
    ...
```

### Docstrings (Google Style)

All public functions and classes MUST have docstrings:

```python
def embed_text(text: str, model: str = "bge-m3") -> List[float]:
    """Generate embedding for text using Ollama.

    Args:
        text: The text to embed (cleaned, no markdown).
        model: Ollama model name (default: bge-m3).

    Returns:
        List of floats representing the embedding vector.

    Raises:
        OllamaConnectionError: If Ollama API is unavailable.
        ValueError: If text is empty or exceeds model context.

    Example:
        >>> embedding = embed_text("Hello world")
        >>> len(embedding)
        1024
    """
```

---

## 2. Functional Programming Principles

| Principle | Implementation |
|-----------|----------------|
| Pure Functions | Prefer pure functions over classes where possible |
| Immutability | Use frozen dataclasses for configuration |
| Side Effects | Avoid in core business logic (logging/IO at boundaries) |
| Comprehensions | Use list/dict comprehensions for transformations |

```python
# ✅ GOOD: Pure function
def clean_text(content: str) -> str:
    """Remove frontmatter and markdown syntax."""
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    content = re.sub(r'\[\[(.*?)\]\]', r'\1', content)
    return content.strip()

# ❌ BAD: Function with side effects
def clean_text(content):
    global log_file
    log_file.write("Cleaning text...")  # Side effect
    return content.replace('[[', '')
```

---

## 3. Error Handling

### Custom Exceptions

```python
# src/utils/exceptions.py
class ObsidianRAGError(Exception):
    """Base exception for Obsidian RAG project."""
    pass

class OllamaConnectionError(ObsidianRAGError):
    """Raised when Ollama API is unavailable."""
    pass

class EmbeddingError(ObsidianRAGError):
    """Raised when embedding generation fails."""
    pass

class ValidationError(ObsidianRAGError):
    """Raised when LLM validation fails."""
    pass
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=30)
)
def call_ollama_api(prompt: str) -> str:
    """Call Ollama API with retry logic."""
    ...
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_note(file_path: str) -> Optional[Chunk]:
    try:
        content = read_file(file_path)
        chunks = chunk_text(content)
        return chunks
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {str(e)}")
        return None  # Don't crash, skip and continue
```

---

## 4. Testing Standards

| Requirement | Value |
|-------------|-------|
| Coverage | Minimum 80% for core modules |
| Framework | pytest |
| Naming | `test_<module>_<function>_<scenario>` |
| Fixtures | Use pytest fixtures for reusable test data |
| Mocking | Mock external APIs (Ollama, Gemini) |

### Test Structure

```python
# tests/unit/test_indexing.py
import pytest
from src.indexing.vault_indexer import VaultIndexer

class TestVaultIndexer:
    """Tests for VaultIndexer class."""

    @pytest.fixture
    def indexer(self):
        """Create indexer instance for tests."""
        return VaultIndexer(vault_path="/tmp/test_vault")

    def test_clean_text_removes_frontmatter(self, indexer):
        """Test that frontmatter is removed from notes."""
        content = "---\ntags: [test]\n---\nHello world"
        cleaned = indexer.clean_text(content)
        assert "---" not in cleaned
        assert "Hello world" in cleaned

    def test_chunk_text_respects_token_limit(self, indexer):
        """Test that chunks don't exceed max tokens."""
        text = "word " * 1000
        chunks = indexer.chunk_text(text, max_tokens=512)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 600 for c in chunks)  # Buffer for safety
```

---

## 5. Project Structure

```
obsidian-rag/
├── pyproject.toml          # Poetry configuration
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── README.md               # Project documentation
│
├── docs/                   # Agent context files
│   ├── 00_PROJECT_BRIEF.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_CURRENT_STATUS.md
│   ├── 03_CODING_STANDARDS.md
│   └── 04_DATA_DICTIONARY.md
│
├── src/
│   ├── indexing/           # Sprint 01
│   │   ├── __init__.py
│   │   ├── vault_indexer.py
│   │   └── ...
│   ├── ingestion/          # Sprint 02
│   ├── retrieval/          # Sprint 03
│   ├── validation/         # Sprint 04
│   ├── output/             # Sprint 05
│   └── utils/              # Shared utilities
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── data/
│   ├── vectors/            # ChromaDB storage
│   ├── processed/          # Output files
│   └── logs/               # Execution logs
│
└── examples/
    └── indexing_example.py # Usage examples
```

---

## 6. Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | lowercase, snake_case | `vault_indexer.py` |
| Classes | PascalCase | `VaultIndexer` |
| Functions | snake_case | `clean_text()` |
| Variables | snake_case | `file_path` |
| Constants | UPPER_SNAKE_CASE | `MAX_TOKENS` |
| Private Methods | prefix `_` | `_internal_method()` |
| Test Files | `test_*.py` | `test_indexing.py` |

---

## 7. Configuration Management

### Environment Variables (.env)

```bash
# .env.example
VAULT_PATH=/path/to/obsidian/vault
CHROMA_PERSIST_DIR=./data/vectors
OLLAMA_HOST=http://localhost:11434
GEMINI_API_KEY=your_api_key_here
EMBEDDING_MODEL=bge-m3
VALIDATION_MODEL=llama3.1
RERANK_THRESHOLD=0.75
```

### Pydantic Config Class

```python
# src/utils/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    vault_path: str
    chroma_persist_dir: str = "./data/vectors"
    ollama_host: str = "http://localhost:11434"
    gemini_api_key: str
    embedding_model: str = "bge-m3"
    validation_model: str = "llama3.1"
    rerank_threshold: float = 0.75

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 8. Dependencies

### Pin Versions in pyproject.toml

```toml
[tool.poetry.dependencies]
python = "^3.10"
chromadb = "^0.4.22"
ollama = "^0.1.7"
google-generativeai = "^0.3.2"
pymupdf = "^1.23.8"
sentence-transformers = "^2.3.1"
pydantic = "^2.5.3"
python-dotenv = "^1.0.0"
tqdm = "^4.66.1"
tenacity = "^8.2.3"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
black = "^23.12.1"
isort = "^5.13.2"
ruff = "^0.1.9"
```

### Install Command

```bash
poetry install
poetry add google-generativeai pymupdf chromadb ollama
```

---

## 9. Git & Version Control

| Rule | Implementation |
|------|----------------|
| Commit Messages | Conventional Commits (`feat:`, `fix:`, `docs:`) |
| Branch Naming | `sprint-01-indexing`, `feature/re-ranker` |
| .gitignore | Never commit `.env`, `data/`, `__pycache__/` |
| Tags | `v0.1.0-sprint01`, `v0.2.0-sprint02` |

---

## 10. Security Best Practices

| Practice | Implementation |
|----------|----------------|
| Secrets | Never commit `.env` files |
| API Keys | Use environment variables only |
| Logging | Mask sensitive data in logs |
| File Paths | Validate paths to prevent directory traversal |
| Rate Limiting | Respect API limits (Gemini: 15 RPM) |

---

## 11. Data Protection Standards (CRITICAL - ADDED 2026-03-02)

### Rule 1: Never Use `rm -rf` on Data Directories

```bash
# ❌ NEVER DO THIS
rm -rf data/vectors/
rm -rf data/processed/

# ✅ SAFE ALTERNATIVE (use system Python, not Poetry)
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.indexing.vault_indexer --clean
# (Requires confirmation + creates automatic backup)
```

### Rule 2: Backup Before Destructive Operations

- All `--clean` operations MUST create timestamped backup first
- Backup location: `data/backups/vectors_YYYYMMDD_HHMMSS/`
- Keep last 3 backups automatically
- Restore script: `scripts/restore_vectors.sh <backup_path>`

### Rule 3: Confirmation for Data Loss

- Any operation that deletes embeddings requires explicit confirmation
- User must type `YES_DELETE` to proceed
- Display estimated re-index time in warning
- Exception: `--no-confirm` flag for automated scripts

### Rule 4: Partial Indexing for Development

| Use Case | Command | Time |
|----------|---------|------|
| Full re-index | `--clean` | 10+ hours |
| Folder test | `--folder "Notes/Projetos"` | 1-2 hours |
| Quick test | `--limit 100` | 5-10 minutes |

### Rule 5: Recovery Procedures

Always maintain `docs/RECOVERY.md` with:
- Steps to rebuild from scratch
- Estimated time for each sprint
- Backup restore procedures
- Contact for emergencies

### Rule 6: Git Strategy for Data

| Directory | Git Status | Rationale |
|-----------|------------|-----------|
| `data/vectors/chroma_db/` | Ignored | Large, regenerable |
| `data/backups/` | Tracked (.gitkeep) | Recovery option |
| `scripts/backup*.sh` | Tracked | Critical for recovery |
| `data/logs/` | Ignored | Sensitive paths |
| `data/processed/` | Ignored | User content |
```

---