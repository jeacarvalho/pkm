"""Topic extractor using Gemini API."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from tenacity import retry, stop_after_attempt, wait_exponential

from src.topics.config import TopicConfig
from src.topics.cdu_resolver import (
    infer_cdu_fallback,
    infer_cdu_from_keywords,
    get_cdu_description,
)
from src.topics.topic_validator import (
    TopicValidator,
    TopicValidationError,
    remove_accents,
)
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


TOPIC_EXTRACTION_PROMPT = """Você é um curador de conhecimento pessoal especializado em classificação bibliográfica CDU.
Extraia os 10 tópicos principais desta nota E sugira classificação CDU.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS JSON válido (sem markdown, sem texto extra)
2. Tópicos: name (str), weight (inteiro OBRIGATORIAMENTE entre 5 e 10), confidence (float 0.0-1.0)
3. Tópicos em português, snake_case, específicos (evite genéricos como "filosofia")
4. CDU: formato "XXX.X" (ex: "321.1", "305.8")
5. Se não houver CDU óbvio, use null para cdu_primary
6. Exatamente 10 tópicos, não mais, não menos
7. IMPORTANTE: weight deve ser 5, 6, 7, 8, 9 ou 10 (nunca abaixo de 5)

CONTEÚDO DA NOTA:
{note_content}

Responda em JSON estrito:
{{
  "topics": [
    {{"name": "exemplo_topico", "weight": 10, "confidence": 0.95}},
    ... (10 tópicos total)
  ],
  "cdu_primary": "321.1" | null,
  "cdu_secondary": ["305.8"] | [],
  "cdu_description": "Descrição da CDU" | null
}}"""

CHAPTER_TOPIC_EXTRACTION_PROMPT = """Você é um curador de conhecimento pessoal especializado em classificação bibliográfica CDU.
Extraia os 10 tópicos principais deste capítulo de livro E sugira classificação CDU.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS JSON válido (sem markdown, sem texto extra)
2. Tópicos: name (str), weight (inteiro OBRIGATORIAMENTE entre 5 e 10), confidence (float 0.0-1.0)
3. Tópicos em português, snake_case, GENÉRICOS (para facilitar conexões com outras notas)
4. CDU: formato "XXX.X" (ex: "321.1", "305.8")
5. Se não houver CDU óbvio, use null para cdu_primary
6. Exatamente 10 tópicos, não mais, não menos
7. IMPORTANTE: weight deve ser 5, 6, 7, 8, 9 ou 10 (nunca abaixo de 5)
8. PRIORIDADE: Gerar tópicos genéricos que facilitem conexões temáticas (ex: "lideranca", "historia", "estrategia", "comunicacao", "politica", "governanca")

CONTEÚDO DO CAPÍTULO:
{note_content}

Responda em JSON estrito:
{{
  "topics": [
    {{"name": "exemplo_topico", "weight": 10, "confidence": 0.95}},
    ... (10 tópicos total)
  ],
  "cdu_primary": "321.1" | null,
  "cdu_secondary": ["305.8"] | [],
  "cdu_description": "Descrição da CDU" | null
}}"""


class TopicExtractor:
    """Extract topics from Obsidian notes using Gemini."""

    def __init__(self, config: Optional[TopicConfig] = None):
        """Initialize topic extractor.

        Args:
            config: Topic extraction configuration
        """
        if config is None:
            self.config = TopicConfig()
        else:
            self.config = config
        self.validator = TopicValidator(self.config)

        # Get API key - try from config first, then from main settings
        self.gemini_api_key = getattr(
            self.config, "gemini_api_key", None
        ) or os.environ.get("GEMINI_API_KEY")

        if not self.gemini_api_key:
            # Fallback to main settings
            try:
                from src.utils.config import Settings

                settings = Settings()
                self.gemini_api_key = settings.gemini_api_key
            except Exception:
                pass

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(self.config.gemini_model)
        logger.info(
            f"Initialized TopicExtractor with model: {self.config.gemini_model}"
        )

    def _clean_unicode_chars(self, text: str) -> str:
        """Clean Unicode characters that can cause JSON parsing issues.

        Args:
            text: Input text

        Returns:
            Cleaned text with Unicode characters replaced
        """
        # Replace common Unicode characters with ASCII equivalents
        replacements = {
            "‘": "'",
            "’": "'",
            "“": '"',
            "”": '"',
            "—": "-",
            "–": "-",
            "…": "...",
            " ": " ",  # non-breaking space to regular space
        }

        cleaned = text
        for unicode_char, ascii_char in replacements.items():
            cleaned = cleaned.replace(unicode_char, ascii_char)

        # Also remove unusual Unicode characters (U+2000 to U+2FFF range)
        # These can cause issues with some APIs
        import re

        cleaned = re.sub(r"[\u2000-\u2FFF]", "", cleaned)

        return cleaned

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_topics(
        self, note_content: str, is_chapter: bool = False
    ) -> Dict[str, Any]:
        """Extract topics from note content.

        Args:
            note_content: Content of the note
            is_chapter: If True, use chapter-specific prompt for generic topics

        Returns:
            Dictionary with topics and CDU classification
        """
        # Clean Unicode characters that can cause JSON parsing issues
        cleaned_content = self._clean_unicode_chars(note_content)

        # Truncate if too long
        truncated = cleaned_content[: self.config.max_note_length]

        # Use different prompt for chapters vs. notes
        if is_chapter:
            prompt = CHAPTER_TOPIC_EXTRACTION_PROMPT.format(note_content=truncated)
        else:
            prompt = TOPIC_EXTRACTION_PROMPT.format(note_content=truncated)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
                request_options={"timeout": self.config.api_timeout},
            )

            # Parse JSON response
            response_text = response.text
            if response_text is None:
                raise ValueError("Empty response from Gemini API")
            result = json.loads(response_text)

            # Validate result
            self.validator.validate_full_result(result)

            return result

        except TopicValidationError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            # Check if it's a timeout error
            error_str = str(e).lower()
            if "timeout" in error_str or "504" in error_str or "deadline" in error_str:
                logger.warning(
                    f"⚠️ API timeout for note (content length: {len(truncated)} chars)"
                )
                # Log a sample of the content to debug
                if len(truncated) > 500:
                    logger.debug(f"Content sample (first 500 chars): {truncated[:500]}")
            # Check for rate limit errors
            elif "rate" in error_str or "quota" in error_str or "429" in error_str:
                logger.warning(f"⚠️ Rate limit detected: {error_str}")
                # Add extra delay before retry
                time.sleep(10)
            else:
                logger.error(f"Gemini API error: {e}")
            raise

    def _strip_frontmatter(self, content: str) -> str:
        """Strip YAML frontmatter from note content.

        Args:
            content: Full note content including frontmatter

        Returns:
            Content without frontmatter (body only)
        """
        content = content.strip()
        if content.startswith("---"):
            # Find the second "---"
            first_end = content.find("---", 3)  # Start searching after the first "---"
            if first_end != -1:
                # Return everything after the second "---"
                content = content[first_end + 3 :].strip()
        return content

    def _clean_obsidian_syntax(self, content: str) -> str:
        """Clean Obsidian-specific syntax from content.

        Removes embedded images (![[filename.png]]), wikilinks ([[link]]),
        and code blocks with dataview/tasks queries which can cause timeout issues.

        Args:
            content: Note content with Obsidian syntax

        Returns:
            Content cleaned of Obsidian syntax
        """
        import re

        # Remove embedded images: ![[filename.png]]
        content = re.sub(r"!\[\[[^\]]+\]\]", "", content)

        # Remove wikilinks: [[link]]
        content = re.sub(r"\[\[[^\]]+\]\]", "", content)

        # Remove code blocks (```code```) - especially dataview and tasks queries
        # This regex matches code blocks with any language specification
        content = re.sub(r"```[\w\s]*\n[\s\S]*?\n```", "", content)

        return content.strip()

    def _clean_urls(self, content: str) -> str:
        """Clean URLs from content to prevent API timeouts.

        Args:
            content: Note content with URLs

        Returns:
            Content with URLs replaced with placeholders
        """
        import re

        # More comprehensive URL pattern that catches URLs with various prefixes/suffixes
        # Handles URLs that might be preceded by •, -, *, etc. and followed by various characters
        url_pattern = r"\b(?:https?://|www\.)\S+[/\w.?=&%-]*"
        content = re.sub(url_pattern, "[URL]", content)

        # Also catch URLs without http:// prefix but with common patterns
        url_pattern2 = r"\b[\w.-]+\.(?:com|org|net|br|edu|gov)[/\w.?=&%-]*"
        content = re.sub(url_pattern2, "[URL]", content)

        return content.strip()

    def process_note(self, note_path: Path) -> Tuple[Optional[Dict], Optional[str]]:
        """Process a single note.

        Args:
            note_path: Path to the note file

        Returns:
            Tuple of (result dict or None, error message or None)
        """
        try:
            content = note_path.read_text(encoding="utf-8")
            content_stripped = content.strip()

            # Check if note is too short - process as index note
            if len(content_stripped) < 50:
                logger.info(f"  📄 Processing as index note: {note_path.name}")
                result = self._extract_from_title(note_path, content_stripped)
                return result, None

            # Strip frontmatter before sending to Gemini API
            # Frontmatter can cause timeout issues with certain content
            body_content = self._strip_frontmatter(content_stripped)

            # Log if frontmatter was stripped
            if body_content != content_stripped:
                original_len = len(content_stripped)
                stripped_len = len(body_content)
                logger.debug(
                    f"  📋 Stripped frontmatter: {original_len} → {stripped_len} chars"
                )

            # Clean Obsidian syntax (embedded images, wikilinks)
            # These can cause timeout issues with Gemini API
            cleaned_content = self._clean_obsidian_syntax(body_content)

            # Log if Obsidian syntax was cleaned
            if cleaned_content != body_content:
                original_len = len(body_content)
                cleaned_len = len(cleaned_content)
                logger.debug(
                    f"  🧹 Cleaned Obsidian syntax: {original_len} → {cleaned_len} chars"
                )

            # Clean URLs to prevent API timeouts
            # URLs in content can cause Gemini API to hang
            url_cleaned_content = self._clean_urls(cleaned_content)

            # Log if URLs were cleaned
            if url_cleaned_content != cleaned_content:
                original_len = len(cleaned_content)
                cleaned_len = len(url_cleaned_content)
                logger.debug(f"  🔗 Cleaned URLs: {original_len} → {cleaned_len} chars")

            result = self.extract_topics(url_cleaned_content)

            # Add metadata
            result["metadata"] = {
                "file_path": str(note_path),
                "file_name": note_path.name,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "model": self.config.gemini_model,
            }

            return result, None

        except Exception as e:
            return None, str(e)

    def _extract_from_title(self, note_path: Path, content: str) -> Dict:
        """Extract topics from note title for short/index notes.

        Uses folder-based CDU inference and generates topics from title keywords.
        Does not call Gemini API - processes locally.

        Args:
            note_path: Path to the note
            content: Note content (may be very short or empty)

        Returns:
            Result dictionary with topics and CDU
        """
        filename = note_path.stem
        folder_path = str(note_path.parent)

        # Infer CDU from folder and title
        cdu_primary = infer_cdu_fallback(str(note_path))
        cdu_description = get_cdu_description(cdu_primary) if cdu_primary else None

        # Generate topics from filename keywords
        topics = self._generate_topics_from_filename(filename)

        # Build result
        result = {
            "topics": topics,
            "cdu_primary": cdu_primary,
            "cdu_secondary": [],
            "cdu_description": cdu_description,
            "content_summary": f"Index note: {filename}",
            "metadata": {
                "file_path": str(note_path),
                "file_name": note_path.name,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "model": "local-inference",
                "is_index_note": True,
            },
        }

        return result

    def _generate_topics_from_filename(self, filename: str) -> List[Dict]:
        """Generate topics from filename keywords.

        Args:
            filename: Note filename (without extension)

        Returns:
            List of topic dictionaries
        """
        # Clean filename: replace separators with spaces
        clean_name = filename.replace("_", " ").replace("-", " ").lower()

        # Split into words
        words = clean_name.split()

        # Generate topics from meaningful words (skip common words)
        skip_words = {
            "a",
            "o",
            "e",
            "de",
            "do",
            "da",
            "em",
            "no",
            "na",
            "para",
            "por",
            "com",
            "sem",
            "um",
            "uma",
            "os",
            "as",
            "e",
            "ou",
            "the",
            "a",
            "an",
            "of",
            "to",
            "in",
            "for",
            "on",
            "at",
            "by",
        }

        topics = []
        topic_names = set()

        # Add words from filename as topics
        for word in words:
            if word not in skip_words and len(word) > 2:
                # Convert to snake_case and remove accents
                topic_name = remove_accents(word.replace(" ", "_"))
                if topic_name not in topic_names:
                    topics.append(
                        {
                            "name": topic_name,
                            "weight": 8,  # High weight for index notes
                            "confidence": 0.85,
                        }
                    )
                    topic_names.add(topic_name)

        # If no topics found, add a generic one
        if not topics:
            topics.append(
                {
                    "name": "index_note",
                    "weight": 5,
                    "confidence": 0.5,
                }
            )

        # Limit to max 10 topics
        return topics[:10]

    def process_directory(self, directory: Path, dry_run: bool = False) -> List[Dict]:
        """Process all markdown files in a directory.

        Args:
            directory: Directory to process
            dry_run: If True, don't actually call API

        Returns:
            List of results
        """
        results = []
        md_files = list(directory.rglob("*.md"))

        # Exclude .obsidian folder
        md_files = [f for f in md_files if ".obsidian" not in str(f)]

        logger.info(f"Found {len(md_files)} markdown files in {directory}")

        for i, note_path in enumerate(md_files, 1):
            logger.info(f"[{i}/{len(md_files)}] Processing: {note_path.name}")

            if dry_run:
                logger.info(f"  [DRY-RUN] Would extract topics from {note_path.name}")
                results.append(
                    {"file": str(note_path), "status": "dry-run", "topics": []}
                )
                continue

            result, error = self.process_note(note_path)

            if error:
                logger.error(f"  ❌ Failed: {error}")
                results.append(
                    {"file": str(note_path), "status": "error", "error": error}
                )
            elif result:
                logger.info(f"  ✅ Success: {len(result.get('topics', []))} topics")
                results.append(
                    {"file": str(note_path), "status": "success", "data": result}
                )
            else:
                logger.error(f"  ❌ Failed: No result returned")
                results.append(
                    {
                        "file": str(note_path),
                        "status": "error",
                        "error": "No result returned",
                    }
                )

            # Small delay between API calls
            time.sleep(0.5)

        return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract topics from Obsidian vault notes"
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        help="Test with specific directory (optional, default: vault complete)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log only, don't call API"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/logs/topics",
        help="Output directory for logs",
    )

    args = parser.parse_args()

    # Setup logging
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine target directory
    settings = Settings()
    if args.test_dir:
        target_dir = Path(settings.vault_path) / args.test_dir
        if not target_dir.exists():
            print(f"❌ Directory not found: {target_dir}")
            sys.exit(1)
    else:
        target_dir = Path(settings.vault_path)

    print(f"🚀 Topic Extraction")
    print(f"   Target: {target_dir}")
    print(f"   Dry-run: {args.dry_run}")
    print(f"   Output: {output_dir}")
    print()

    try:
        # Initialize extractor
        config = TopicConfig(log_dir=output_dir)
        extractor = TopicExtractor(config)

        # Process notes
        results = extractor.process_directory(target_dir, dry_run=args.dry_run)

        # Save results
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"topic_extraction_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "config": {
                        "dry_run": args.dry_run,
                        "target_dir": str(target_dir),
                        "model": config.gemini_model,
                    },
                    "results": results,
                    "summary": {
                        "total": len(results),
                        "success": sum(1 for r in results if r["status"] == "success"),
                        "error": sum(1 for r in results if r["status"] == "error"),
                        "dry_run": sum(1 for r in results if r["status"] == "dry-run"),
                    },
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print()
        print("=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Total files: {len(results)}")
        print(f"Success: {sum(1 for r in results if r['status'] == 'success')}")
        print(f"Error: {sum(1 for r in results if r['status'] == 'error')}")
        print(f"Output: {output_file}")
        print("=" * 60)

        sys.exit(0)

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
