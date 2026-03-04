"""Topic extractor using Gemini API."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.topics.config import TopicsConfig
from src.topics.topic_validator import TopicValidator, TopicValidationError
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


class TopicExtractor:
    """Extract topics from Obsidian notes using Gemini."""

    def __init__(self, config: TopicsConfig = None):
        """Initialize topic extractor.

        Args:
            config: Topic extraction configuration
        """
        self.config = config or TopicsConfig()
        self.validator = TopicValidator(self.config)

        # Get API key from main settings
        from src.utils.config import Settings

        settings = Settings()
        self.gemini_api_key = settings.gemini_api_key

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        self.client = genai.Client(api_key=self.gemini_api_key)
        logger.info(
            f"Initialized TopicExtractor with model: {self.config.gemini_model}"
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_topics(self, note_content: str) -> Dict[str, Any]:
        """Extract topics from note content.

        Args:
            note_content: Content of the note

        Returns:
            Dictionary with topics and CDU classification
        """
        # Truncate if too long
        truncated = note_content[: self.config.max_note_length]

        prompt = TOPIC_EXTRACTION_PROMPT.format(note_content=truncated)

        try:
            response = self.client.models.generate_content(
                model=self.config.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0, response_mime_type="application/json"
                ),
            )

            # Parse JSON response
            result = json.loads(response.text)

            # Validate result
            self.validator.validate_full_result(result)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise
        except TopicValidationError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def process_note(self, note_path: Path) -> Tuple[Optional[Dict], Optional[str]]:
        """Process a single note.

        Args:
            note_path: Path to the note file

        Returns:
            Tuple of (result dict or None, error message or None)
        """
        try:
            content = note_path.read_text(encoding="utf-8")

            # Skip if empty or too short
            if len(content.strip()) < 50:
                return None, "Note too short (< 50 chars)"

            result = self.extract_topics(content)

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
            else:
                logger.info(f"  ✅ Success: {len(result.get('topics', []))} topics")
                results.append(
                    {"file": str(note_path), "status": "success", "data": result}
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
        config = TopicsConfig(log_dir=output_dir)
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
