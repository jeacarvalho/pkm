"""Unit tests for constants module.

Tests that all constants are properly defined and have expected values.
"""

import pytest

from src.topics import constants


class TestConstantsValues:
    """Test that constants have expected values."""

    def test_failure_tracking_constants(self):
        """Test failure tracking related constants."""
        assert constants.MAX_FAILURE_COUNT == 3
        assert constants.SKIP_WINDOW_DAYS == 7
        assert constants.FAILURE_TRACKER_FILE == ".pkm_failure_tracker.json"

    def test_content_processing_constants(self):
        """Test content processing related constants."""
        assert constants.MIN_NOTE_LENGTH == 50
        assert constants.MAX_NOTE_LENGTH == 5000
        assert constants.FRONTMATTER_DELIMITER == "---"

    def test_api_constants(self):
        """Test API related constants."""
        assert constants.API_RATE_LIMIT_DELAY == 8.0
        assert constants.API_TIMEOUT_SECONDS == 90.0
        assert constants.API_MAX_RETRIES == 3
        assert constants.API_RETRY_DELAY_BASE == 2.0

    def test_topic_extraction_constants(self):
        """Test topic extraction related constants."""
        assert constants.MAX_TOPICS_PER_NOTE == 10
        assert constants.MIN_TOPIC_WEIGHT == 5
        assert constants.MAX_TOPIC_WEIGHT == 10
        assert constants.DEFAULT_GEMINI_MODEL == "gemini-2.5-flash-lite"

    def test_fuzzy_matching_constants(self):
        """Test fuzzy matching related constants."""
        assert constants.FUZZY_MATCH_THRESHOLD == 40
        assert constants.FUZZY_MATCH_ALGORITHM == "token_sort_ratio"

    def test_cdu_constants(self):
        """Test CDU (Classification) related constants."""
        assert constants.CDU_EXACT_MATCH_BONUS == 20
        assert constants.CDU_CATEGORY_MATCH_BONUS == 10
        assert constants.CDU_SECONDARY_MATCH_BONUS == 5
        assert constants.MIN_CDU_FREQUENCY == 2

    def test_topic_matching_constants(self):
        """Test topic matching related constants."""
        assert constants.DEFAULT_TOP_K_MATCHES == 20
        assert constants.DEFAULT_MATCH_THRESHOLD == 0.0

    def test_pdf_processing_constants(self):
        """Test PDF processing related constants."""
        assert constants.PDF_CHUNK_SIZE_TOKENS == 512
        assert constants.PDF_CHUNK_OVERLAP_TOKENS == 50
        assert constants.PDF_RATE_LIMIT_RPM == 15
        assert constants.LANGUAGE_DETECTION_SAMPLE_SIZE == 5

    def test_logging_constants(self):
        """Test logging related constants."""
        assert constants.DEFAULT_LOG_LEVEL == "INFO"
        assert constants.LOG_DATE_FORMAT == "%Y-%m-%d %H:%M:%S"

    def test_version_constants(self):
        """Test version related constants."""
        assert constants.TOPIC_CLASSIFICATION_VERSION == "2.0"
        assert constants.YAML_DUMP_WIDTH == 1000
        assert constants.YAML_DUMP_INDENT == 2


class TestConstantsImmutability:
    """Test that constants are immutable (Final type hint)."""

    def test_constants_are_defined(self):
        """Test that all expected constants are defined."""
        expected_constants = [
            "MAX_FAILURE_COUNT",
            "SKIP_WINDOW_DAYS",
            "FAILURE_TRACKER_FILE",
            "MIN_NOTE_LENGTH",
            "MAX_NOTE_LENGTH",
            "FRONTMATTER_DELIMITER",
            "API_RATE_LIMIT_DELAY",
            "API_TIMEOUT_SECONDS",
            "API_MAX_RETRIES",
            "API_RETRY_DELAY_BASE",
            "MAX_TOPICS_PER_NOTE",
            "MIN_TOPIC_WEIGHT",
            "MAX_TOPIC_WEIGHT",
            "DEFAULT_GEMINI_MODEL",
            "FUZZY_MATCH_THRESHOLD",
            "FUZZY_MATCH_ALGORITHM",
            "CDU_EXACT_MATCH_BONUS",
            "CDU_CATEGORY_MATCH_BONUS",
            "CDU_SECONDARY_MATCH_BONUS",
            "MIN_CDU_FREQUENCY",
            "DEFAULT_TOP_K_MATCHES",
            "DEFAULT_MATCH_THRESHOLD",
            "PDF_CHUNK_SIZE_TOKENS",
            "PDF_CHUNK_OVERLAP_TOKENS",
            "PDF_RATE_LIMIT_RPM",
            "LANGUAGE_DETECTION_SAMPLE_SIZE",
            "DEFAULT_LOG_LEVEL",
            "LOG_DATE_FORMAT",
            "TOPIC_CLASSIFICATION_VERSION",
            "YAML_DUMP_WIDTH",
            "YAML_DUMP_INDENT",
        ]

        for const_name in expected_constants:
            assert hasattr(constants, const_name), f"Missing constant: {const_name}"

    def test_constant_types(self):
        """Test that constants have correct types."""
        assert isinstance(constants.MAX_FAILURE_COUNT, int)
        assert isinstance(constants.SKIP_WINDOW_DAYS, int)
        assert isinstance(constants.FAILURE_TRACKER_FILE, str)
        assert isinstance(constants.API_RATE_LIMIT_DELAY, float)
        assert isinstance(constants.MAX_TOPICS_PER_NOTE, int)
        assert isinstance(constants.FUZZY_MATCH_THRESHOLD, int)


class TestConstantsRelationships:
    """Test logical relationships between constants."""

    def test_weight_range_valid(self):
        """Test that min weight is less than max weight."""
        assert constants.MIN_TOPIC_WEIGHT < constants.MAX_TOPIC_WEIGHT

    def test_retry_delay_positive(self):
        """Test that retry delay is positive."""
        assert constants.API_RETRY_DELAY_BASE > 0

    def test_timeout_reasonable(self):
        """Test that timeout is reasonable (not too short, not too long)."""
        assert 30 <= constants.API_TIMEOUT_SECONDS <= 300

    def test_chunk_overlap_less_than_size(self):
        """Test that chunk overlap is less than chunk size."""
        assert constants.PDF_CHUNK_OVERLAP_TOKENS < constants.PDF_CHUNK_SIZE_TOKENS

    def test_cdu_bonuses_descending(self):
        """Test that CDU bonuses are in descending order of specificity."""
        assert constants.CDU_EXACT_MATCH_BONUS > constants.CDU_CATEGORY_MATCH_BONUS
        assert constants.CDU_CATEGORY_MATCH_BONUS > constants.CDU_SECONDARY_MATCH_BONUS
