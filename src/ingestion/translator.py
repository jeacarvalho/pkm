"""Translation utilities using Google Gemini API."""

import time
from typing import Optional, Tuple

import google.genai as genai
from google.api_core import exceptions as google_exceptions

from src.utils.config import settings
from src.utils.exceptions import TranslationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GeminiTranslator:
    """Translator using Google Gemini API.

    Uses the new google.genai package (not the deprecated google.generativeai).

    Attributes:
        api_key: Gemini API key.
        model: Gemini model name.
        rpm_limit: Requests per minute limit (default: 15 for free tier).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        rpm_limit: int = 15,
    ):
        """Initialize translator.

        Args:
            api_key: Gemini API key. If None, uses settings.gemini_api_key.
            model: Gemini model to use. If None, uses settings.gemini_model.
            rpm_limit: Rate limit in requests per minute.
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self.rpm_limit = rpm_limit
        self._last_request_time: Optional[float] = None

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            self.model = None
            logger.warning("No Gemini API key configured. Translation disabled.")

    def _rate_limit(self) -> None:
        """Apply rate limiting to respect RPM limits."""
        if self._last_request_time is not None:
            min_interval = 60.0 / self.rpm_limit
            elapsed = time.time() - self._last_request_time

            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        self._last_request_time = time.time()

    def translate(
        self,
        text: str,
        target_lang: str = "pt",
        source_lang: Optional[str] = None,
        retries: int = 3,
    ) -> Tuple[str, bool]:
        """Translate text using Gemini API.

        Args:
            text: Text to translate.
            target_lang: Target language code.
            source_lang: Source language code (auto-detected if None).
            retries: Number of retry attempts.

        Returns:
            Tuple of (translated_text, success).

        Raises:
            TranslationError: If all retries fail.
        """
        if not self.api_key or not self.client:
            logger.warning("Translation skipped: No API key configured")
            return (text, False)

        lang_name = {"pt": "Portuguese", "en": "English", "es": "Spanish"}.get(
            target_lang, target_lang
        )

        if source_lang:
            prompt = f"""Translate the following text from {source_lang} to {lang_name}.
            Preserve formatting and maintain academic/professional tone.
            Only return the translated text, no explanations.

            Text to translate:
            {text}
            """
        else:
            prompt = f"""Translate the following text to {lang_name}.
            Preserve formatting and maintain academic/professional tone.
            Only return the translated text, no explanations.

            Text to translate:
            {text}
            """

        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < retries:
            try:
                self._rate_limit()

                response = self.client.models.generate_content(
                    model=self.model_name, contents=[prompt]
                )

                if response and response.candidates:
                    translated = response.candidates[0].content.parts[0].text.strip()
                    logger.debug(
                        f"Translated {len(text)} chars -> {len(translated)} chars"
                    )
                    return (translated, True)
                else:
                    raise TranslationError("Empty response from Gemini API")

            except google_exceptions.ResourceExhausted as e:
                attempt += 1
                wait_time = 5 * (2**attempt)
                logger.warning(
                    f"Rate limit hit, waiting {wait_time}s before retry {attempt}"
                )
                time.sleep(wait_time)
                last_error = e

            except google_exceptions.InvalidArgument as e:
                raise TranslationError(f"Invalid API request: {e}") from e

            except Exception as e:
                attempt += 1
                if attempt < retries:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Translation attempt {attempt} failed: {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    last_error = e
                else:
                    break

        raise TranslationError(
            f"Failed to translate after {retries} attempts: {last_error}"
        ) from last_error

    def translate_chunk(
        self, text: str, target_lang: str = "pt", max_chars: int = 4000
    ) -> Tuple[str, bool]:
        """Translate a chunk of text, splitting if too large.

        Args:
            text: Text to translate.
            target_lang: Target language code.
            max_chars: Maximum characters per request.

        Returns:
            Tuple of (translated_text, success).
        """
        if len(text) <= max_chars:
            return self.translate(text, target_lang)

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                last_newline = text.rfind("\n", start, end)
                if last_newline > start:
                    end = last_newline

            chunk = text[start:end]
            translated, success = self.translate(chunk, target_lang)

            if not success:
                return ("", False)

            chunks.append(translated)
            start = end

        return ("\n".join(chunks), True)


def translate_if_needed(
    text: str,
    target_lang: str = "pt",
    api_key: Optional[str] = None,
    force: bool = False,
) -> Tuple[str, bool]:
    """Translate text only if needed.

    Args:
        text: Text to potentially translate.
        target_lang: Target language code.
        api_key: Gemini API key.
        force: If True, always translate regardless of detected language.

    Returns:
        Tuple of (text, was_translated).
    """
    from src.ingestion.language_detector import detect_language

    try:
        source_lang = detect_language(text[:1000])
    except Exception:
        source_lang = "en"

    if not force and source_lang == target_lang:
        logger.debug(f"Text already in {target_lang}, skipping translation")
        return (text, False)

    translator = GeminiTranslator(api_key=api_key)
    return translator.translate(text, target_lang, source_lang)
