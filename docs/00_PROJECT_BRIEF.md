---

## 📄 `docs/00_PROJECT_BRIEF.md`

```markdown
# Project Brief: Obsidian Topic-Based Classification System v2.1

**Status:** v2.1 Production Ready ✅  
**Last Updated:** 2026-03-07  
**Architecture:** Topic-Based (NO EMBEDDINGS)  
**Agent Context:** OpenCode (kimi-k2.5)

---

## Quick Start for New Agents

```bash
# 1. Install dependencies (Poetry or pip)
pip install -r requirements.txt
# OR
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env with your VAULT_PATH and GEMINI_API_KEY

# 3. Run Daily Sync (process new/modified notes)
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.topics.daily_sync --vault-dir "/path/to/vault"

# 4. Run tests
python3 -m pytest tests/unit/ -v
```

---

## Objective

Build a **topic-based classification system** that automatically categorizes 3,600+ notes in an Obsidian vault. The system:

1. **Daily Sync** - Runs nightly to detect new/modified notes
2. **Topic Extraction** - Uses Gemini API to extract topics and CDU classifications
3. **Smart Filtering** - Skips notes that repeatedly fail (failure tracking)
4. **Git Integration** - Commits and pushes changes automatically
5. **Topic Matching** - Links book chapters to vault notes by topic overlap

**⚠️ IMPORTANT:** This is v2.1 (topic-based). The old v1.0 embedding system (ChromaDB/Ollama) has been completely removed.

---

## Tech Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Language | Python 3.10+ | ✅ |
| Package Manager | Poetry / pip | ✅ |
| Topic Extraction | Gemini 2.5 Flash Lite | ✅ |
| Classification | CDU (Universal Decimal Classification) | ✅ |
| Translation | Google Gemini 1.5 Flash | ✅ (for PDFs) |
| Testing | Pytest (144 tests) | ✅ |
| Version Control | Git (auto-commit) | ✅ |

---

## Critical Business Rules

### 1. Incremental Processing (MANDATORY) ✅
**Definition:** Only process notes that are NEW or MODIFIED today.

**Implementation:**
- `DailySync` class scans vault for timestamps
- New notes: created today without `topic_classification`
- Modified notes: changed today WITH `topic_classification` (reindex needed)
- Skips notes that already have classification and weren't modified

**Usage:**
```bash
# Daily sync (automatic)
./scripts/production_daily_sync.sh

# Force all unclassified notes
python3 -m src.topics.daily_sync --vault-dir "/path" --force-all
```

### 2. Failure Tracking & Skip Logic ✅
**Definition:** Skip notes that fail 3+ times within 7 days.

**Implementation:**
- `FailureTracker` class persists failures to `~/.pkm_failure_tracker.json`
- Max failures: 3 attempts
- Skip window: 7 days
- Automatically clears on success

**Configuration:**
```python
# src/topics/constants.py
MAX_FAILURE_COUNT = 3
SKIP_WINDOW_DAYS = 7
```

### 3. Git Integration ✅
**Definition:** All vault changes must be committed and pushed.

**Implementation:**
- `production_daily_sync.sh` runs git add/commit/push first
- Commits all vault changes before processing
- Prevents data loss and maintains version history

**Script Location:**
```bash
./scripts/production_daily_sync.sh  # Main production script
./scripts/cron_daily_sync_production.sh  # Cron wrapper
```

### 4. Rate Limiting ✅
**Definition:** Respect Gemini API rate limits with delays.

**Implementation:**
- Delay between API calls: 8 seconds (configurable)
- Timeout: 90 seconds per request
- Exponential backoff on errors
- 3 retries with increasing delays

**Configuration:**
```python
# src/topics/constants.py
API_RATE_LIMIT_DELAY = 8.0
API_TIMEOUT_SECONDS = 90.0
API_MAX_RETRIES = 3
```

---

## Project Phases

| Phase | Version | Status | Description |
|-------|---------|--------|-------------|
| Phase 0 | v0.x | ✅ COMPLETE | Manual CDU classification |
| Phase 1 | v1.0 | ✅ REMOVED | Embedding-based (ChromaDB/Ollama) - DEPRECATED |
| Phase 2 | v2.0 | ✅ COMPLETE | Topic-based classification (Gemini) |
| Phase 3 | v2.1 | ✅ PRODUCTION | Daily sync + failure tracking + git integration |

---

## Architecture Overview (v2.1)

### Active Modules

```
src/
├── topics/              # Main classification system
│   ├── daily_sync.py         # Daily sync orchestrator
│   ├── topic_extractor.py    # Gemini API topic extraction
│   ├── topic_matcher.py      # Fuzzy topic matching
│   ├── topic_validator.py    # CDU and topic validation
│   ├── taxonomy_manager.py   # CDU classification manager
│   ├── vault_writer.py       # Write to vault notes
│   ├── failure_tracker.py    # Track processing failures
│   ├── constants.py          # Centralized constants
│   └── config.py            # Configuration
├── ingestion/           # PDF processing (for books)
│   ├── pdf_processor.py       # PDF chapter processing
│   ├── chapter_parser.py     # Parse chapter ranges
│   ├── translator.py        # Translation service
│   └── translation_cache.py  # Cache translations
├── output/             # Markdown generation
│   ├── markdown_generator.py
│   ├── vault_writer.py
│   └── templates.py
└── utils/              # Utilities
    ├── config.py
    ├── logging.py
    └── exceptions.py

scripts/
├── production_daily_sync.sh      # Main production script
├── cron_daily_sync_production.sh # Cron job
├── test_production_dry_run.sh    # Test script
└── run_daily_sync.sh            # Manual execution
```

### DEPRECATED (v1.0 - REMOVED)

```
❌ src/indexing/       - ChromaDB-based indexing (REMOVED)
❌ src/retrieval/      - Vector search (REMOVED)
❌ src/validation/   - Ollama/Gemini validators (REMOVED)
```

---

## Key Classes (v2.1)

### DailySync
Main orchestrator for daily processing.
- Detects new/modified notes
- Manages failure tracking
- Writes topics to vault
- Saves statistics

### FailureTracker
Tracks note processing failures with skip logic.
```python
tracker = FailureTracker()
if tracker.should_skip(note_path):
    continue  # Skip problematic notes
tracker.record_failure(note_path)  # On error
tracker.record_success(note_path)  # On success
```

### TopicExtractor
Extracts topics using Gemini API.
```python
extractor = TopicExtractor(config)
topics = extractor.extract_topics(content, is_chapter=True)
```

### VaultWriter
Writes topic classifications to vault notes.
```python
writer = VaultWriter(config)
writer._write_topics_directly(note_path, topic_data)
```

---

## Configuration

### Environment Variables

```bash
# .env file
VAULT_PATH=/home/user/MEGAsync/Minhas_notas
GEMINI_API_KEY=your_api_key_here
```

### Constants

All magic numbers centralized in `src/topics/constants.py`:

```python
MAX_FAILURE_COUNT = 3          # Max failures before skip
SKIP_WINDOW_DAYS = 7           # Days to skip after max failures
API_RATE_LIMIT_DELAY = 8.0     # Seconds between API calls
API_TIMEOUT_SECONDS = 90.0      # API timeout
MIN_NOTE_LENGTH = 50          # Min chars to process
MAX_TOPICS_PER_NOTE = 10       # Max topics to extract
FUZZY_MATCH_THRESHOLD = 40     # Fuzzy matching threshold
```

---

## Usage Examples

### 1. Daily Sync (Production)

```bash
# Run via cron at 2:00 AM daily
0 2 * * * /home/user/pkm/scripts/cron_daily_sync_production.sh

# Or run manually
./scripts/production_daily_sync.sh
```

### 2. Process Specific Notes

```python
from src.topics.daily_sync import DailySync
from src.topics.config import TopicConfig

config = TopicConfig()
daily_sync = DailySync(config)

# Process all notes without topic_classification
modified = daily_sync.process_notes(vault_path, force_all=True)
```

### 3. Check Failure Tracker

```bash
# View failure tracker
cat ~/.pkm_failure_tracker.json

# Reset specific note
python3 -c "
from src.topics.failure_tracker import FailureTracker
tracker = FailureTracker()
tracker.reset(Path('/path/to/note.md'))
"
```

### 4. Dry Run Testing

```bash
# Test without making changes
./scripts/test_production_dry_run.sh
```

---

## Testing

### Run All Tests

```bash
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m pytest tests/unit/ -v
```

### Current Test Coverage

- **Total Tests:** 144 passing
- **Coverage:** 30.25%
- **Key Test Files:**
  - `test_failure_tracker.py` - 16 tests (96% coverage)
  - `test_constants.py` - 17 tests (100% coverage)
  - `test_topics_vault_writer.py` - 13 tests
  - `test_topic_matcher.py` - 15 tests
  - `test_ingestion.py` - 19 tests

### Test Categories

```bash
# Run specific test files
pytest tests/unit/test_failure_tracker.py -v
pytest tests/unit/test_constants.py -v
pytest tests/unit/test_topics_vault_writer.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html
```

---

## Logs and Monitoring

### Log Locations

```
data/logs/
├── daily_sync/          # Daily sync logs
│   └── daily_sync_YYYY-MM-DD.log
├── topics/             # Topic extraction logs
│   └── topic_extraction_*.json
├── writer.log          # Vault writer logs
└── matcher.log         # Topic matcher logs
```

### View Logs

```bash
# Real-time log monitoring
tail -f data/logs/daily_sync/*.log

# Check specific date
cat data/logs/daily_sync/daily_sync_2026-03-07.log
```

---

## Migration Notes (v1.0 → v2.1)

### What Changed

1. **Removed:** ChromaDB, Ollama embeddings, vector search
2. **Added:** Gemini API topic extraction, CDU classification
3. **New:** Daily sync system with incremental processing
4. **New:** Failure tracking and skip logic
5. **New:** Automatic git integration

### Data Compatibility

- **Vault notes:** 100% compatible (same frontmatter format)
- **Old embeddings:** Can be safely deleted
- **ChromaDB:** Can be uninstalled

### Migration Steps

```bash
# 1. Stop old services
# (No Ollama/ChromaDB needed anymore)

# 2. Install new dependencies
pip install google-genai pyyaml thefuzz

# 3. Configure Gemini API key
export GEMINI_API_KEY=your_key

# 4. Run daily sync
./scripts/production_daily_sync.sh
```

---

## Quick Reference

### Check System Status

```bash
# Check vault stats
ls -la /path/to/vault/*.md | wc -l

# Check failure tracker
cat ~/.pkm_failure_tracker.json | jq '. | length'

# Check recent logs
ls -lt data/logs/daily_sync/ | head -5
```

### Common Commands

```bash
# Run daily sync
python3 -m src.topics.daily_sync --vault-dir "/path"

# Force all unclassified
python3 -m src.topics.daily_sync --vault-dir "/path" --force-all

# Test dry run
./scripts/test_production_dry_run.sh

# Check git status in vault
cd /path/to/vault && git status
```

### Troubleshooting

**Problem:** Notes timing out during processing  
**Solution:** Check `src/topics/constants.py` - increase `API_TIMEOUT_SECONDS`

**Problem:** Too many API rate limit errors  
**Solution:** Increase `API_RATE_LIMIT_DELAY` (default: 8.0 seconds)

**Problem:** Notes failing repeatedly  
**Solution:** Check failure tracker: `cat ~/.pkm_failure_tracker.json`

---

## Next Steps

1. **Monitor:** Check daily sync logs for errors
2. **Optimize:** Adjust rate limits if needed
3. **Extend:** Add more CDU categories to taxonomy
4. **Improve:** Increase test coverage to 80%+

---

## Key Files (v2.1)

```
src/
├── topics/
│   ├── daily_sync.py          ⭐ Main orchestrator
│   ├── topic_extractor.py     ⭐ Gemini API integration
│   ├── vault_writer.py        ⭐ Write to vault
│   ├── failure_tracker.py     ⭐ Skip logic
│   ├── constants.py           ⭐ Configuration
│   └── config.py              ⭐ Settings
├── ingestion/
│   └── pdf_processor.py       # PDF book processing
└── utils/
    ├── config.py
    └── logging.py

tests/
├── unit/
│   ├── test_failure_tracker.py    ⭐ 96% coverage
│   ├── test_constants.py          ⭐ 100% coverage
│   ├── test_topics_vault_writer.py
│   └── test_topic_matcher.py

docs/
├── 00_PROJECT_BRIEF.md       ⭐ This file
├── 01_ARCHITECTURE.md        ⭐ System architecture
├── 02_CURRENT_STATUS.md      ⭐ Current state
├── 10_ROADMAP_v2.md         ⭐ Future plans
└── daily_sync_system.md      ⭐ Daily sync docs

scripts/
├── production_daily_sync.sh      ⭐ Production script
├── cron_daily_sync_production.sh ⭐ Cron job
└── test_production_dry_run.sh    ⭐ Testing
```

---

## Support

**For issues or questions:**
1. Check logs in `data/logs/`
2. Review test output: `pytest tests/unit/ -v`
3. Check failure tracker: `~/.pkm_failure_tracker.json`

**Version:** v2.1.0  
**Last Updated:** 2026-03-07  
**Status:** Production Ready ✅
```

---
