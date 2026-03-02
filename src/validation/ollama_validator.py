"""Ollama validator for semantic match validation."""

import json
import re
import time
from typing import Any, Dict, List, Optional

import ollama

from src.utils.config import Settings
from src.utils.logging import get_logger
from src.validation.prompt_templates import (
    SYSTEM_PROMPT,
    build_validation_prompt,
    FALLBACK_RESPONSE,
)

logger = get_logger(__name__)


class ValidationResponse:
    """Structured validation response from Ollama.

    Attributes:
        approved: Whether match is semantically valid.
        confidence: Confidence score 0-100.
        reason: Human-readable explanation.
    """

    def __init__(self, approved: bool, confidence: int, reason: str):
        self.approved = approved
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResponse":
        return cls(
            approved=bool(data.get("approved", False)),
            confidence=int(data.get("confidence", 0)),
            reason=str(data.get("reason", "")),
        )


class OllamaValidator:
    """Validate semantic matches between book chunks and vault notes.

    This class uses Ollama to validate whether retrieved matches from
    the re-ranker are actually semantically relevant. It acts as
    a second level of filtering (after cross-encoder re-ranking).

    The key principle is: "Be skeptical - reject weak matches".

    Attributes:
        config: Application settings.
        model: Ollama model to use for validation.
        temperature: Temperature for generation (0.0 for deterministic).
        timeout: Timeout for API calls in seconds.
        max_retries: Maximum retry attempts on failure.

    Example:
        >>> validator = OllamaValidator()
        >>> result = validator.validate_match(
        ...     book_chunk="Antifragility is beyond resilience...",
        ...     note_content="Antifragilidade é um conceito...",
        ...     note_title="Antifragilidade",
        ...     rerank_score=0.85,
        ... )
        >>> result.approved
        True
    """

    def __init__(
        self,
        config: Optional[Settings] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """Initialize Ollama validator.

        Args:
            config: Application settings. If None, uses default.
            model: Ollama model name. If None, uses config.
            temperature: Generation temperature (0.0 = deterministic).
            timeout: API call timeout in seconds.
            max_retries: Maximum retry attempts on failure.
        """
        self.config = config or Settings()
        self.model = model or self.config.validation_model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        logger.info(f"Initialized OllamaValidator with model: {self.model}")

    def validate_match(
        self,
        book_chunk: str,
        note_content: str,
        note_title: str,
        rerank_score: float,
    ) -> ValidationResponse:
        """Validate a single match between book chunk and note.

        Args:
            book_chunk: Text from the book chapter (translated if needed).
            note_content: Full content of the Obsidian note.
            note_title: Title of the note for context.
            rerank_score: Score from re-ranker (0.0-1.0).

        Returns:
            ValidationResponse with approved, confidence, and reason.

        Example:
            >>> validator = OllamaValidator()
            >>> result = validator.validate_match(
            ...     book_chunk="test chunk",
            ...     note_content="test note",
            ...     note_title="Test",
            ...     rerank_score=0.9,
            ... )
            >>> isinstance(result.approved, bool)
            True
        """
        prompt = build_validation_prompt(
            book_chunk=book_chunk,
            note_content=note_content,
            note_title=note_title,
            rerank_score=rerank_score,
        )

        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < self.max_retries:
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    options={"temperature": self.temperature},
                )

                # Extract and parse JSON response
                content = response["message"]["content"]
                json_str = self._extract_json(content)
                data = json.loads(json_str)

                result = ValidationResponse.from_dict(data)

                # Log decision
                status = "✅ APPROVED" if result.approved else "❌ REJECTED"
                logger.info(
                    f"Validation {status}: {note_title} "
                    f"(confidence: {result.confidence}%, "
                    f"rerank_score: {rerank_score:.3f})"
                )

                return result

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                last_error = e
                attempt += 1
                if attempt < self.max_retries:
                    time.sleep(1)

            except Exception as e:
                logger.warning(f"Ollama error (attempt {attempt + 1}): {e}")
                last_error = e
                attempt += 1
                if attempt < self.max_retries:
                    time.sleep(2**attempt)  # Exponential backoff

        # All retries failed - return fallback
        logger.error(f"All {self.max_retries} attempts failed for {note_title}")
        fallback = ValidationResponse(**FALLBACK_RESPONSE)
        fallback.reason = (
            f"Validation failed after {self.max_retries} attempts: {last_error}"
        )
        return fallback

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text (handles markdown code blocks).

        Args:
            text: Raw response text from Ollama.

        Returns:
            Extracted JSON string.

        Example:
            >>> validator = OllamaValidator()
            >>> text = '```json\\n{"approved": true}\\n```'
            >>> validator._extract_json(text)
            '{"approved": true}'
        """
        # Try to find JSON between ```json and ```
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Try to find JSON between ``` and ```
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Try to find JSON object directly (starts with {)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        # Return as-is if no code blocks found
        return text.strip()

    def validate_batch(
        self,
        book_chunk: str,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate multiple candidates for a single book chunk.

        Args:
            book_chunk: Text from the book.
            candidates: List of retrieved notes from Sprint 03.
                Each should have "document", "metadata", "rerank_score".

        Returns:
            List of validated matches (only approved ones).
            Each match includes validation metadata.

        Example:
            >>> validator = OllamaValidator()
            >>> candidates = [
            ...     {
            ...         "document": "note text",
            ...         "metadata": {"note_title": "Test"},
            ...         "rerank_score": 0.85,
            ...     }
            ... ]
            >>> results = validator.validate_batch("book chunk", candidates)
            >>> len(results) <= len(candidates)
            True
        """
        validated = []

        for candidate in candidates:
            result = self.validate_match(
                book_chunk=book_chunk,
                note_content=candidate.get("document", ""),
                note_title=candidate.get("metadata", {}).get("note_title", "Unknown"),
                rerank_score=candidate.get("rerank_score", 0.0),
            )

            if result.approved:
                # Add validation metadata to the candidate
                validated_candidate = {
                    **candidate,
                    "validation": result.to_dict(),
                    "validator_model": self.model,
                }
                validated.append(validated_candidate)

        logger.info(
            f"Validated {len(candidates)} candidates: "
            f"{len(validated)} approved, {len(candidates) - len(validated)} rejected"
        )

        return validated


class MockOllamaValidator(OllamaValidator):
    """Mock validator for testing without actual Ollama calls."""

    def __init__(self, approval_rate: float = 0.5, **kwargs):
        """Initialize mock validator.

        Args:
            approval_rate: Fraction of matches to approve (0.0-1.0).
            **kwargs: Passed to parent class.
        """
        super().__init__(**kwargs)
        self.approval_rate = approval_rate

    def validate_match(
        self,
        book_chunk: str,
        note_content: str,
        note_title: str,
        rerank_score: float,
    ) -> ValidationResponse:
        """Mock validation - returns deterministic results."""
        # Approve high scores, reject low scores
        approved = rerank_score > 0.80

        return ValidationResponse(
            approved=approved,
            confidence=int(rerank_score * 100),
            reason=f"Mock validation (score: {rerank_score:.3f})",
        )
