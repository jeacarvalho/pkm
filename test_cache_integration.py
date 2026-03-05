#!/usr/bin/env python3
"""Test cache integration in pdf_processor."""

import sys
import logging

sys.path.insert(0, "/home/s015533607/Documentos/desenv/pkm")

from src.ingestion.pdf_processor import PDFProcessor
from src.utils.config import settings

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_cache_integration():
    """Test that cache integration works in PDFProcessor."""
    print("🧪 Testing Cache Integration in PDFProcessor")
    print("=" * 60)

    # Initialize processor with cache
    processor = PDFProcessor(
        api_key=settings.gemini_api_key,
        target_language="pt",
        enable_translation=True,
        use_chapter_mode=True,
        chapters_file="data/test/quijano_capitulos.txt",
        vault_path=str(settings.vault_path / "100 ARQUIVOS E REFERENCIAS/Livros"),
        book_name="Anibal_Quijano_v3",
        force_retranslate=False,  # Cache should be used
        skip_validation=True,
    )

    print(f"Processor initialized:")
    print(f"  - Book name: {processor.book_name}")
    print(f"  - Vault path: {processor.vault_path}")
    print(f"  - Force retranslate: {processor.force_retranslate}")
    print(f"  - Enable translation: {processor.enable_translation}")

    # Check if cache was initialized
    if hasattr(processor, "cache") and processor.cache:
        print("✅ Cache initialized in PDFProcessor")

        # Test cache status for chapter 1
        status = processor.cache.check_cache_status(chapter_num=1)
        print(f"\nCache status for chapter 1:")
        print(f"  - File exists: {status['file_exists']}")
        print(f"  - Has content: {status['has_content']}")
        print(f"  - Cached: {status['cached']}")
        print(f"  - File path: {status['file_path']}")
    else:
        print("❌ Cache NOT initialized in PDFProcessor")

    print("\n" + "=" * 60)
    print("✅ Cache integration test completed!")


if __name__ == "__main__":
    test_cache_integration()
