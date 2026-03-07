## 📄 `docs/01_ARCHITECTURE.md`

```markdown
# 01 ARCHITECTURE - Obsidian Topic-Based Classification System v2.1

**Status:** Architecture v2.1 Production Ready  
**Last Updated:** 2026-03-07  
**Architecture:** Topic-Based (NO EMBEDDINGS)

---

## 1. High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  Obsidian   │  │   PDF Books │  │   Gemini    │                      │
│  │   Vault     │  │   Library   │  │   API       │                      │
│  │  (3,600+    │  │             │  │ (Topic      │                      │
│  │   notes)    │  │             │  │  Extract)   │                      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                      │
└─────────┼────────────────┼────────────────┼─────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        TOPIC LAYER (v2.0+)                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Topic Extractor (Gemini API)                    │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Read Note │→ │  Extract   │→ │  CDU       │                 │   │
│  │   │  Content   │  │  Topics    │  │  Classify  │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DAILY SYNC LAYER (v2.1)                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     DailySync Orchestrator                        │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Scan      │→ │  Filter    │→ │  Process   │                 │   │
│  │   │  Vault     │  │  New/Mod   │  │  Notes     │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FAILURE TRACKING (v2.1)                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     FailureTracker Class                          │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Track     │  │  Skip      │  │  Reset     │                 │   │
│  │   │  Failures  │  │  >3 errors │  │  on Success│                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    VAULT WRITER (v2.0+)                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Obsidian Frontmatter Writer                      │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  Build     │→ │  Update    │→ │  Save      │                 │   │
│  │   │  Topics    │  │  Frontmatter│  │  Note      │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └──────────────────────────────────────────┼───────────────────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GIT INTEGRATION (v2.1)                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Automatic Version Control                        │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐                 │   │
│  │   │  git add   │→ │  git       │→ │  git       │                 │   │
│  │   │            │  │  commit    │  │  push      │                 │   │
│  │   └────────────┘  └────────────┘  └─────┬──────┘                 │   │
│  └─────────────────────────────────────────┼────────────────────────┘   │
└────────────────────────────────────────────┼────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OUTPUT - Obsidian Vault                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  Markdown with Topics + CDU                     │   │
│  │   - Frontmatter: topic_classification                            │   │
│  │   - Topics: [{"name": "topic", "weight": 8}]                     │   │
│  │   - CDU: Primary + Secondary classifications                     │   │
│  │   - thematic_connections (for chapters)                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Architecture

### 2.1 Daily Sync Flow (v2.1)

```
[Daily Sync Trigger]
       │
       ▼
┌─────────────────────┐
│  1. Git Operations  │
│  - git add .       │
│  - git commit      │
│  - git push        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  2. Scan Vault      │
│  - Find new notes   │
│  - Find modified    │
│  - Check timestamps │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  3. Filter Notes    │
│  - Skip if in       │
│    failure tracker  │
│  - Skip if already  │
│    classified today │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  4. Extract Topics  │
│  - Call Gemini API  │
│  - 8s delay between │
│  - Rate limiting    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  5. Validate CDU    │
│  - Check format     │
│  - Transliterate    │
│  - Fallback logic   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  6. Write to Vault  │
│  - Update frontmatter│
│  - Preserve content │
│  - YAML formatting  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  7. Track Stats     │
│  - Save statistics  │
│  - Update failure   │
│    tracker          │
└─────────────────────┘
```

### 2.2 Topic Extraction Flow

```
[Note Content]
       │
       ▼
┌─────────────────────────┐
│  Clean Content          │
│  - Remove frontmatter   │
│  - Strip URLs           │
│  - Clean Unicode        │
│  - Remove code blocks   │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Build Prompt           │
│  - System instruction   │
│  - Content preview      │
│  - Output format spec   │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Gemini API Call        │
│  - Model: flash-lite    │
│  - Timeout: 90s         │
│  - Temperature: 0.3     │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Parse Response         │
│  - JSON validation      │
│  - Topic extraction     │
│  - CDU classification   │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│  Validate Results       │
│  - Check topic names    │
│  - Validate CDU format  │
│  - Transliterate chars  │
└─────────┬───────────────┘
          │
          ▼
[Validated Topics + CDU]
```

---

## 3. Component Architecture

### 3.1 Core Classes (v2.1)

```
┌─────────────────────────────────────────────────────────────┐
│                    Core Module: topics/                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ DailySync                                            │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - scan_vault()           → Find notes to process   │   │
│  │ - process_notes()        → Main orchestrator        │   │
│  │ - extract_topics_for_notes() → Batch extraction     │   │
│  │ - _write_topics_directly() → Save to vault          │   │
│  │ - _save_stats()          → Persist statistics       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ FailureTracker                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - should_skip()          → Check if skip note       │   │
│  │ - record_failure()       → Increment fail count     │   │
│  │ - record_success()       → Clear fail history       │   │
│  │ - reset()                → Reset tracking         │   │
│  │ - get_stats()            → Failure statistics       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ TopicExtractor                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - extract_topics()       → Gemini API call          │   │
│  │ - process_note()         → Full note processing    │   │
│  │ - _clean_obsidian_syntax() → Clean markdown       │   │
│  │ - _build_prompt()        → Construct prompt       │   │
│  │ - process_directory()    → Batch processing       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ TopicMatcher                                         │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - match_chapter_to_vault() → Find connections      │   │
│  │ - _calculate_match_score() → Fuzzy matching        │   │
│  │ - _fuzzy_match()         → Compare topics          │   │
│  │ - _match_topics()        → Batch matching          │   │
│  │ - _calculate_cdu_bonus() → CDU scoring            │   │
│  │ - run()                  → Main matcher            │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ VaultWriter                                          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - write_properties()     → Write to single note     │   │
│  │ - _read_note()           → Read frontmatter         │   │
│  │ - _write_note()        → Save with frontmatter    │   │
│  │ - _build_topic_classification() → Build structure   │   │
│  │ - write_all_chapters()   → Batch chapter write     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ TaxonomyManager                                      │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - validate_cdu()         → Check CDU format        │   │
│  │ - get_cdu_description()  → Lookup description      │   │
│  │ - infer_cdu_fallback()   → Fallback logic          │   │
│  │ - get_taxonomy_stats()   → Statistics              │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ TopicValidator                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ - validate_topic_name()  → Check name format       │   │
│  │ - validate_cdu_format()  → Check CDU format        │   │
│  │ - remove_accents()       → Transliterate           │   │
│  │ - to_snake_case()        → Normalize names         │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Supporting Classes

```
┌─────────────────────────────────────────────────────────────┐
│              Supporting Modules                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ChapterTextExtractor (ingestion/pdf_processor.py)         │
│  ├─ extract_chapter_text()   → From PDF pages              │
│  ├─ extract_chapter_title()  → From first page             │
│  └─ get_total_pages()        → PDF metadata                │
│                                                             │
│  ChapterCacheManager (ingestion/pdf_processor.py)          │
│  ├─ get_cached_content()     → Check cache                 │
│  ├─ save_translation()       → Cache results                │
│  └─ Uses: TranslationCache                                 │
│                                                             │
│  ChapterTopicExtractor (ingestion/pdf_processor.py)          │
│  ├─ extract_topics_and_connections() → Topics + matching   │
│  ├─ _find_thematic_connections() → Vault matching            │
│  ├─ _filter_self_references() → Remove book matches         │
│  └─ Uses: TopicExtractor + TopicMatcher                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Data Structures

### 4.1 Topic Classification (Frontmatter)

```yaml
---
topic_classification:
  version: "2.0"
  classified_at: "2026-03-07T10:30:00+00:00"
  model: "gemini-2.5-flash-lite"
  topics:
    - name: "inteligencia_artificial"
      weight: 10
    - name: "machine_learning"
      weight: 8
  cdu_primary: "004.8"
  cdu_secondary: ["004.9", "006.3"]
  cdu_description: "Inteligência Artificial e Machine Learning"
---
```

### 4.2 Failure Tracker JSON

```json
{
  "/path/to/note1.md": {
    "count": 2,
    "last_failure": "2026-03-06T15:30:00+00:00"
  },
  "/path/to/note2.md": {
    "count": 3,
    "last_failure": "2026-03-05T10:00:00+00:00"
  }
}
```

### 4.3 Daily Sync Statistics

```json
{
  "date": "2026-03-07T02:00:00+00:00",
  "total_notes_scanned": 3635,
  "new_notes_found": 5,
  "modified_notes_found": 12,
  "notes_processed": 17,
  "notes_skipped": 0,
  "notes_failed": 1,
  "notes_skipped_due_to_failures": 2,
  "new_notes_processed": [
    "/path/to/new_note1.md"
  ],
  "modified_notes_reindexed": [
    "/path/to/modified_note1.md"
  ],
  "notes_failed_list": [
    "/path/to/failed_note.md"
  ]
}
```

---

## 5. Configuration Architecture

### 5.1 Constants (src/topics/constants.py)

```python
# Failure Tracking
MAX_FAILURE_COUNT = 3
SKIP_WINDOW_DAYS = 7

# Content Processing
MIN_NOTE_LENGTH = 50
MAX_NOTE_LENGTH = 5000

# API Configuration
API_RATE_LIMIT_DELAY = 8.0        # seconds
API_TIMEOUT_SECONDS = 90.0        # seconds
API_MAX_RETRIES = 3

# Topic Extraction
MAX_TOPICS_PER_NOTE = 10
MIN_TOPIC_WEIGHT = 5
MAX_TOPIC_WEIGHT = 10

# Fuzzy Matching
FUZZY_MATCH_THRESHOLD = 40

# CDU Classification
CDU_EXACT_MATCH_BONUS = 20
CDU_CATEGORY_MATCH_BONUS = 10
CDU_SECONDARY_MATCH_BONUS = 5
```

### 5.2 Environment Variables (.env)

```bash
VAULT_PATH=/home/user/MEGAsync/Minhas_notas
GEMINI_API_KEY=your_api_key_here
```

---

## 6. Execution Flows

### 6.1 Production Daily Sync

```bash
./scripts/production_daily_sync.sh

Flow:
1. git add → git commit → git push (vault changes)
2. Run DailySync with dry_run=False
3. Process new notes (no topic_classification)
4. Process modified notes (with classification, need reindex)
5. Skip notes in failure tracker (>=3 fails, <7 days)
6. Save statistics to JSON
7. Exit with code 0 (success) or 1 (if failures > 0)
```

### 6.2 Manual Force Processing

```bash
python3 -m src.topics.daily_sync --vault-dir "/path" --force-all

Flow:
1. Find ALL notes without topic_classification (not just today's)
2. Process each with 8s delay
3. Apply failure tracking
4. Write topics to vault
5. Save statistics
```

### 6.3 PDF Book Processing

```bash
python3 -m src.ingestion.pdf_processor --pdf "/path/to/book.pdf" --chapters "/path/caps.txt"

Flow:
1. Parse chapter ranges from capitulos.txt
2. Extract text for each chapter
3. Detect language
4. Translate if needed (Gemini)
5. Cache translations
6. Extract topics (TopicExtractor)
7. Find thematic connections (TopicMatcher)
8. Write chapters to vault (VaultWriter)
```

---

## 7. Error Handling

### 7.1 Retry Strategy

```python
# Exponential backoff for API calls
for attempt in range(API_MAX_RETRIES):
    try:
        result = api_call()
        break
    except Exception as e:
        delay = API_RETRY_DELAY_BASE * (2 ** attempt)
        time.sleep(delay)
        if attempt == API_MAX_RETRIES - 1:
            raise
```

### 7.2 Failure Tracking

```python
# Skip logic
if failure_tracker.should_skip(note_path):
    logger.info(f"Skipping {note_path.name} - too many failures")
    continue

try:
    result = process_note(note_path)
    failure_tracker.record_success(note_path)
except Exception as e:
    failure_tracker.record_failure(note_path)
    logger.error(f"Failed to process {note_path.name}: {e}")
```

---

## 8. Git Integration

### 8.1 Production Script Workflow

```bash
#!/bin/bash
# production_daily_sync.sh

# Step 1: Git operations (FIRST!)
cd "$VAULT_PATH"
git add .
git commit -m "Auto: Pre-sync checkpoint $(date)" || true
git push origin master || true

# Step 2: Run daily sync
python3 -m src.topics.daily_sync --vault-dir "$VAULT_PATH"

# Step 3: Git operations (if changes)
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "Auto: Daily sync updates $(date)"
    git push origin master
fi
```

### 8.2 Cron Job Setup

```bash
# cron_daily_sync_production.sh - Wrapper for cron
0 2 * * * /home/user/pkm/scripts/cron_daily_sync_production.sh
```

---

## 9. Migration from v1.0 to v2.1

### 9.1 What Changed

| Component | v1.0 (OLD) | v2.1 (NEW) |
|-----------|------------|------------|
| **Core Tech** | ChromaDB + Ollama | Gemini API |
| **Embeddings** | bge-m3 vectors | ❌ REMOVED |
| **Retrieval** | Vector search | ❌ REMOVED |
| **Re-Ranking** | Cross-encoder | ❌ REMOVED |
| **Classification** | None | Topics + CDU |
| **Processing** | Manual/Batch | Daily Sync |
| **Failure Handling** | None | FailureTracker |
| **Version Control** | Manual | Automatic Git |

### 9.2 Deleted Modules

```
❌ src/indexing/       - ChromaDB-based indexing
❌ src/retrieval/      - Vector search, reranker
❌ src/validation/   - Ollama/Gemini validators
```

### 9.3 New Modules

```
✅ src/topics/daily_sync.py       - Daily sync system
✅ src/topics/failure_tracker.py - Failure tracking
✅ src/topics/constants.py       - Centralized config
```

---

## 10. Performance Considerations

### 10.1 API Rate Limiting

- **Delay between calls:** 8 seconds (configurable)
- **Max concurrent:** 1 (sequential processing)
- **Timeout:** 90 seconds per request
- **Retries:** 3 with exponential backoff

### 10.2 Batch Processing

- **Daily sync:** Process only new/modified notes
- **Force all:** Process all unclassified notes (slower)
- **Chapter processing:** Batch chapters with caching

### 10.3 Memory Usage

- **Streaming:** Read notes in chunks
- **Caching:** Persist translations to disk
- **Cleanup:** Remove old log files periodically

---

## 11. Security

### 11.1 API Keys

- **Storage:** Environment variables only
- **Rotation:** Manual (update .env file)
- **Logging:** Never log API keys

### 11.2 Vault Data

- **Git:** All changes committed and pushed
- **Backup:** Git history provides rollback
- **Permissions:** Normal user permissions

---

## 12. Monitoring & Observability

### 12.1 Logs

```
data/logs/
├── daily_sync/
│   └── daily_sync_YYYY-MM-DD.log
├── writer.log
└── matcher.log
```

### 12.2 Metrics

- **Notes processed per day**
- **API calls per day**
- **Failure rate**
- **Average processing time**

### 12.3 Alerts

- **Failures > threshold:** Check failure tracker
- **API errors:** Check rate limiting
- **Git push failures:** Check network

---

**Version:** v2.1.0  
**Last Updated:** 2026-03-07  
**Architecture:** Topic-Based Classification  
**Status:** Production Ready ✅
```

---
