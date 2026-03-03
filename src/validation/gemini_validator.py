"""Gemini Validator - Validate semantic matches using Gemini API."""

import json
import re
from typing import Any, Dict, List, Optional

from google import genai
from pydantic import BaseModel, Field

from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationResponse(BaseModel):
    """Structured validation response from Gemini."""

    approved: bool = Field(..., description="Whether match is semantically valid")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    reason: str = Field(..., min_length=10, description="Human-readable explanation")


class GeminiValidator:
    """Validate semantic matches using Gemini API.

    Replaces OllamaValidator for faster, more reliable validation.
    """

    def __init__(
        self, config: Optional[Settings] = None, model: str = "gemini-2.0-flash"
    ):
        """Initialize Gemini validator.

        Args:
            config: Application settings.
            model: Gemini model to use (default: gemini-2.0-flash).
        """
        self.config = config or Settings()
        self.model = model

        if not self.config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        self.client = genai.Client(api_key=self.config.gemini_api_key)
        logger.info(f"Initialized GeminiValidator with model: {self.model}")

    def validate_match(
        self,
        book_chunk: str,
        note_content: str,
        note_title: str,
        rerank_score: float,
    ) -> ValidationResponse:
        """Validate a single match between book chunk and vault note."""
        prompt = self._build_prompt(book_chunk, note_content, note_title, rerank_score)

        logger.info(f"🔮 Calling Gemini for validation: {note_title}")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",
                },
            )

            json_str = self._extract_json(response.text)
            result = ValidationResponse(**json.loads(json_str))

            if result.approved:
                logger.info(
                    f"✅ VALIDATED: {note_title} (confidence: {result.confidence}%)"
                )
            else:
                logger.info(
                    f"❌ REJECTED: {note_title} (confidence: {result.confidence}%)"
                )

            return result

        except Exception as e:
            logger.error(f"Gemini validation failed: {e}")
            return ValidationResponse(
                approved=False, confidence=0, reason=f"Validation error: {str(e)}"
            )

    def _build_prompt(
        self, book_chunk: str, note_content: str, note_title: str, rerank_score: float
    ) -> str:
        """Build validation prompt for Gemini."""
        book_text = book_chunk[:3000]
        note_text = note_content[:4000]

        return f"""Você é um curador cético de conhecimento pessoal.
Sua tarefa é validar conexões semânticas entre trechos de livros e notas do Obsidian.

REGRAS CRÍTICAS:
1. Seja EXIGENTE - rejeite matches fracos ou superficiais
2. Só aprove se houver relação semântica CLARA e DIRETA
3. Considere o contexto completo da nota, não apenas palavras-chave
4. Similaridade temática não é suficiente - precisa haver conexão conceitual

CONTEXTO DA VALIDAÇÃO:

📖 TRECHO DO LIVRO:
{book_text}

📝 NOTA DO OBSIDIAN:
Título: {note_title}
Conteúdo:
{note_text}

📊 SCORE DO RE-RANKER: {rerank_score:.3f}

PERGUNTA:
Existe uma relação semântica RELEVANTE e DIRETA entre o trecho do livro e a nota?

Responda APENAS em JSON válido com esta estrutura:
{{"approved": boolean, "confidence": integer, "reason": "string"}}

NÃO inclua texto fora do JSON."""

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response."""
        match = re.search(r'\{[^{}]*"approved"[^{}]*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text.strip()

    def validate_batch(
        self, book_chunk: str, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate multiple candidates for a single chapter."""
        validated = []

        for candidate in candidates:
            result = self.validate_match(
                book_chunk=book_chunk,
                note_content=candidate.get("document", ""),
                note_title=candidate.get("metadata", {}).get("note_title", "Unknown"),
                rerank_score=candidate.get("rerank_score", 0.0),
            )

            if result.approved:
                validated.append(
                    {
                        **candidate,
                        "validation": {
                            "approved": result.approved,
                            "confidence": result.confidence,
                            "reason": result.reason,
                            "model": self.model,
                        },
                    }
                )

        logger.info(
            f"✅ Validation complete: {len(validated)}/{len(candidates)} matches approved"
        )
        return validated
