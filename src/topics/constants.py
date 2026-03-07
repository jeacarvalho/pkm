"""Application-wide constants for the PKM topic classification system.

This module contains all magic numbers, timeouts, thresholds, and string constants
to improve maintainability and make configuration changes easier.
"""

from typing import Final

# =============================================================================
# FAILURE TRACKING CONSTANTS
# =============================================================================

MAX_FAILURE_COUNT: Final[int] = 3
"""Maximum number of failures before a note is skipped."""

SKIP_WINDOW_DAYS: Final[int] = 7
"""Number of days to skip a note after it reaches MAX_FAILURE_COUNT."""

FAILURE_TRACKER_FILE: Final[str] = ".pkm_failure_tracker.json"
"""Default filename for failure tracking persistence."""

# =============================================================================
# CONTENT PROCESSING CONSTANTS
# =============================================================================

MIN_NOTE_LENGTH: Final[int] = 50
"""Minimum characters for a note to be processed (below this is treated as index note)."""

MAX_NOTE_LENGTH: Final[int] = 5000
"""Maximum characters to send to API (notes longer than this are truncated)."""

FRONTMATTER_DELIMITER: Final[str] = "---"
"""YAML frontmatter delimiter."""

# =============================================================================
# API CONSTANTS
# =============================================================================

API_RATE_LIMIT_DELAY: Final[float] = 8.0
"""Delay in seconds between API calls to avoid rate limiting."""

API_TIMEOUT_SECONDS: Final[float] = 90.0
"""Timeout for API calls in seconds."""

API_MAX_RETRIES: Final[int] = 3
"""Maximum number of retries for failed API calls."""

API_RETRY_DELAY_BASE: Final[float] = 2.0
"""Base delay for exponential backoff (multiplied by 2^attempt)."""

# =============================================================================
# TOPIC EXTRACTION CONSTANTS
# =============================================================================

MAX_TOPICS_PER_NOTE: Final[int] = 10
"""Maximum number of topics to extract per note."""

MIN_TOPIC_WEIGHT: Final[int] = 5
"""Minimum weight for a topic (importance scale 5-10)."""

MAX_TOPIC_WEIGHT: Final[int] = 10
"""Maximum weight for a topic (importance scale 5-10)."""

DEFAULT_GEMINI_MODEL: Final[str] = "gemini-2.5-flash-lite"
"""Default Gemini model for topic extraction."""

# =============================================================================
# FUZZY MATCHING CONSTANTS
# =============================================================================

FUZZY_MATCH_THRESHOLD: Final[int] = 40
"""Minimum fuzzy match score (0-100) to consider topics similar."""

FUZZY_MATCH_ALGORITHM: Final[str] = "token_sort_ratio"
"""Default fuzzy matching algorithm from thefuzz library."""

# =============================================================================
# CDU (CLASSIFICAÇÃO DECIMAL UNIVERSAL) CONSTANTS
# =============================================================================

CDU_EXACT_MATCH_BONUS: Final[int] = 20
"""Bonus score for exact CDU match."""

CDU_CATEGORY_MATCH_BONUS: Final[int] = 10
"""Bonus score when CDU categories match (first digits)."""

CDU_SECONDARY_MATCH_BONUS: Final[int] = 5
"""Bonus score for matching secondary CDU."""

MIN_CDU_FREQUENCY: Final[int] = 2
"""Minimum frequency for a CDU to be considered significant."""

# =============================================================================
# TOPIC MATCHING CONSTANTS
# =============================================================================

DEFAULT_TOP_K_MATCHES: Final[int] = 20
"""Default number of top matches to return."""

DEFAULT_MATCH_THRESHOLD: Final[float] = 0.0
"""Default minimum score threshold for matches."""

# =============================================================================
# PDF PROCESSING CONSTANTS
# =============================================================================

PDF_CHUNK_SIZE_TOKENS: Final[int] = 512
"""Default chunk size in tokens for PDF text."""

PDF_CHUNK_OVERLAP_TOKENS: Final[int] = 50
"""Overlap in tokens between consecutive chunks."""

PDF_RATE_LIMIT_RPM: Final[int] = 15
"""Rate limit in requests per minute for PDF translation."""

LANGUAGE_DETECTION_SAMPLE_SIZE: Final[int] = 5
"""Number of chapters to sample for language detection."""

# =============================================================================
# LOGGING CONSTANTS
# =============================================================================

DEFAULT_LOG_LEVEL: Final[str] = "INFO"
"""Default logging level."""

LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
"""Date format for log messages."""

# =============================================================================
# VERSION CONSTANTS
# =============================================================================

TOPIC_CLASSIFICATION_VERSION: Final[str] = "2.0"
"""Current version of topic classification schema."""

YAML_DUMP_WIDTH: Final[int] = 1000
"""Line width for YAML dumping."""

YAML_DUMP_INDENT: Final[int] = 2
"""Indentation spaces for YAML dumping."""
