"""Language detection for text content."""

from typing import Optional, Tuple

from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

from src.utils.exceptions import LanguageDetectionError

# Set seed for reproducible results
DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    """Detect the language of a text.

    Args:
        text: Text to analyze.

    Returns:
        ISO 639-1 language code (e.g., 'en', 'pt', 'es').

    Raises:
        LanguageDetectionError: If detection fails.

    Example:
        >>> detect_language("Hello world")
        'en'
        >>> detect_language("Olá mundo")
        'pt'
    """
    try:
        # Clean text for better detection
        cleaned = text.strip()
        if len(cleaned) < 10:
            # Text too short, assume English as default
            return "en"

        return detect(cleaned)
    except LangDetectException as e:
        raise LanguageDetectionError(f"Failed to detect language: {e}") from e
    except Exception as e:
        raise LanguageDetectionError(
            f"Unexpected error in language detection: {e}"
        ) from e


def detect_language_with_confidence(text: str) -> Tuple[str, float]:
    """Detect language with confidence score.

    Args:
        text: Text to analyze.

    Returns:
        Tuple of (language_code, confidence_score).
    """
    try:
        cleaned = text.strip()
        if len(cleaned) < 10:
            return ("en", 0.5)  # Default with low confidence

        from langdetect import detect_langs

        probs = detect_langs(cleaned)

        if probs:
            top = probs[0]
            return (top.lang, top.prob)
        else:
            return ("en", 0.5)

    except Exception as e:
        raise LanguageDetectionError(
            f"Failed to detect language with confidence: {e}"
        ) from e


def should_translate(text: str, target_lang: str = "pt") -> bool:
    """Determine if text should be translated.

    Args:
        text: Text to check.
        target_lang: Target language code.

    Returns:
        True if text is not in target language.
    """
    try:
        detected = detect_language(text)
        return detected != target_lang
    except LanguageDetectionError:
        # If detection fails, assume translation is needed
        return True


def get_language_name(lang_code: str) -> str:
    """Get full language name from ISO code.

    Args:
        lang_code: ISO 639-1 language code.

    Returns:
        Human-readable language name.
    """
    language_names = {
        "pt": "Portuguese",
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "nl": "Dutch",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
        "ar": "Arabic",
        "hi": "Hindi",
        "pl": "Polish",
        "tr": "Turkish",
        "sv": "Swedish",
        "da": "Danish",
        "no": "Norwegian",
        "fi": "Finnish",
        "cs": "Czech",
        "el": "Greek",
        "he": "Hebrew",
        "hu": "Hungarian",
        "ro": "Romanian",
        "sk": "Slovak",
        "th": "Thai",
        "uk": "Ukrainian",
        "vi": "Vietnamese",
    }

    return language_names.get(lang_code, f"Unknown ({lang_code})")


def detect_document_language(pages: list, sample_size: int = 5) -> str:
    """Detect primary language of a document from sample pages.

    Args:
        pages: List of page dictionaries with 'text' key.
        sample_size: Number of pages to sample for detection.

    Returns:
        Most common language code.
    """
    if not pages:
        return "en"

    # Sample pages from beginning, middle, and end
    total_pages = len(pages)
    indices = [
        0,  # First page
        total_pages // 4,  # 25%
        total_pages // 2,  # Middle
        3 * total_pages // 4,  # 75%
        total_pages - 1,  # Last page
    ]

    # Limit to sample_size unique indices
    indices = list(dict.fromkeys(i for i in indices if i < total_pages))[:sample_size]

    languages = []
    for idx in indices:
        text = pages[idx].get("text", "")
        if len(text.strip()) > 50:  # Need enough text
            try:
                lang = detect_language(text[:1000])  # Limit text length
                languages.append(lang)
            except LanguageDetectionError:
                continue

    if not languages:
        return "en"

    # Return most common language
    from collections import Counter

    most_common = Counter(languages).most_common(1)
    return most_common[0][0] if most_common else "en"
