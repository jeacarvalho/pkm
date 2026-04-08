# Daily Sync System v2.1

## Overview

The Daily Sync System is an incremental topic classification system that runs once per day to process new and modified notes in the Obsidian vault. It uses the Gemini API to extract topics from note content and stores them in the note's frontmatter.

## Key Features

- **Incremental Processing**: Only processes notes that need classification
- **Efficient Scanning**: Scans 3600+ notes in ~10 seconds
- **Failure Recovery**: Tracks failed notes and skips them after 3 failures for 7 days
- **Comprehensive Cleaning**: Cleans Unicode, frontmatter, Obsidian syntax, URLs, and code blocks
- **Robust Error Handling**: Graceful handling of API timeouts and parsing errors
- **Detailed Logging**: Complete statistics and failure tracking

## Architecture

### Components

1. **`daily_sync.py`** - Main orchestrator
   - Scans vault for new/modified notes
   - Manages failure tracking
   - Coordinates topic extraction and note updates

2. **`topic_extractor.py`** - Gemini API integration
   - Enhanced cleaning pipeline (Unicode, frontmatter, Obsidian syntax, URLs, code blocks)
   - API timeout handling (30 seconds)
   - Batch processing support

3. **`topic_validator.py`** - Topic validation
   - Validates topic names (snake_case with hyphens allowed)
   - Handles Portuguese accents
   - Ensures topic uniqueness

4. **`config.py`** - Configuration
   - API settings and timeouts
   - Model configuration (gemini-2.5-flash-lite)

### Cleaning Pipeline

The system applies multiple cleaning steps before sending content to Gemini:

1. **Unicode Cleaning** - Removes unusual Unicode characters (U+2000 to U+2FFF)
2. **Frontmatter Stripping** - Removes YAML frontmatter
3. **Obsidian Syntax Cleaning** - Removes embedded images, wikilinks, and code blocks
4. **URL Cleaning** - Removes URLs with various prefixes/suffixes
5. **Code Block Removal** - Removes dataview and tasks queries that cause API timeouts

## Usage

### Manual Execution

```bash
# Dry run (see what would be processed)
python3 src/topics/daily_sync.py --vault-dir /path/to/vault --dry-run

# Process notes (with limit for testing)
python3 src/topics/daily_sync.py --vault-dir /path/to/vault --limit 10

# Force process all notes without topic_classification
python3 src/topics/daily_sync.py --vault-dir /path/to/vault --force-all
```

### Cron Job

The system includes a cron job script that runs at 2:00 AM daily:

```bash
# Test the cron job script
bash scripts/cron_daily_sync.sh

# Add to crontab (run at 2:00 AM daily)
0 2 * * * /home/s015533607/Documentos/desenv/pkm/scripts/cron_daily_sync.sh
```

### Error Recovery

```bash
# List notes with 3+ failures
python3 scripts/recover_failed_notes.py --list

# Interactive recovery mode
python3 scripts/recover_failed_notes.py

# Retry specific note
python3 scripts/recover_failed_notes.py --retry "path/to/note.md"

# Retry all failed notes
python3 scripts/recover_failed_notes.py --retry-all
```

## Statistics

### Current Coverage (as of 2026-03-06)
- **Total Notes**: 3630
- **Notes with topic_classification**: 3464 (95.4%)
- **Notes without topic_classification**: 166 (4.6%)
- **Modified notes needing reindexing**: 24 (daily average)

### Performance
- **Scan Time**: ~10 seconds for 3600+ notes
- **Processing Time**: ~2-3 seconds per note
- **Daily Processing**: ~1 minute for 24 notes
- **Success Rate**: 100% after cleaning improvements

## Failure Handling

### Skip Logic
Notes that fail 3 times are skipped for 7 days to prevent wasting API calls. The system tracks:
- Failure count
- Last failure timestamp
- Skip expiration date

### Common Failure Causes
1. **API Timeouts**: Notes with dataview/tasks queries in code blocks
2. **Unicode Issues**: Notes with unusual Unicode characters
3. **Content Length**: Very long notes (>10KB)
4. **Frontmatter Complexity**: Notes with hundreds of CDU codes

### Solutions Implemented
1. **Code Block Removal**: Fixed "20231220.md" timeout (456-line frontmatter with dataview queries)
2. **Unicode Cleaning**: Fixed JSON parsing errors
3. **Frontmatter Stripping**: Reduced content sent to API
4. **URL Cleaning**: Prevented URL-related parsing issues

## Monitoring

### Log Files
- `data/logs/topics/daily_sync/daily_sync_stats_YYYY-MM-DD.json` - Daily statistics
- `data/logs/topics/daily_sync/failure_tracker.json` - Failure tracking
- `data/logs/topics/daily_sync/cron_daily_sync_*.log` - Cron job logs

### Statistics Format
```json
{
  "date": "2026-03-06",
  "total_notes_scanned": 3630,
  "new_notes_found": 0,
  "modified_notes_needing_reindexing": 24,
  "notes_processed": 24,
  "notes_failed": 0,
  "notes_skipped": 0,
  "processing_time_seconds": 59.2
}
```

## Troubleshooting

### Common Issues

1. **API Timeout Warnings**
   - Solution: The system already handles this with skip logic
   - Check: `failure_tracker.json` for problematic notes

2. **Missing `classified_at` Timestamp**
   - Status: All notes have this timestamp (0 missing)
   - If found: Run with `--force-all` to add missing timestamps

3. **Python Package**
   - Status: ✅ Migrated to `google.genai` (new official package)
   - Previous: `google.generativeai` (deprecated)
   - Impact: Uses latest stable API

### Debugging

```bash
# Test specific note
python3 test_problematic_note.py

# Test cleaning pipeline
python3 test_frontmatter_stripping.py

# Test extraction
python3 test_simple_extraction.py
```

## Future Improvements

1. **✅ Migrate to `google.genai`** - Completed
2. **Content Chunking** - Handle extremely long notes (>20KB)
3. **Topic Deduplication** - Merge similar topics across notes
4. **Quality Metrics** - Track topic relevance and consistency
5. **Batch API Calls** - Process multiple notes in single API call
6. **Fallback Models** - Use alternative models when Gemini fails

## Dependencies

- `google-genai` (official Google GenAI SDK)
- `python-frontmatter`
- `python-dotenv`

## Environment Variables

```bash
GEMINI_API_KEY=your_api_key_here
API_TIMEOUT=30
MODEL_NAME=gemini-2.5-flash-lite
MAX_TOPICS=10
```

## Credits

System developed to solve Gemini API timeout issues with complex Obsidian notes. Successfully processes 3600+ Portuguese notes with 95.4% coverage and 100% success rate after cleaning improvements.