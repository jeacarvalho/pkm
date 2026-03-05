#!/usr/bin/env python3
"""Test translation cache system."""

import sys

sys.path.insert(0, "/home/s015533607/Documentos/desenv/pkm")

from src.topics.translation_cache import TranslationCache


def test_cache():
    """Test the translation cache system."""
    print("🧪 Testing Translation Cache System")
    print("=" * 50)

    # Initialize cache
    vault_path = "/home/s015533607/MEGAsync/Minhas_notas"
    book_name = "Anibal_Quijano_v3"
    cache = TranslationCache(vault_path, book_name, force_retranslate=False)

    # Test 1: Check for existing chapter
    print("\n1. Testing cache check for existing chapter...")
    chapter_num = 1  # Chapter 2 (0-indexed)

    cached_content = cache.get_cached_translation(chapter_num)

    if cached_content:
        print(f"   ✅ Found cached translation for {book_name} chapter {chapter_num}")
        print(f"   Content length: {len(cached_content)} characters")
        print(f"   First 200 chars: {cached_content[:200]}...")
    else:
        print(
            f"   ❌ No cached translation found for {book_name} chapter {chapter_num}"
        )

    # Test 2: Check for non-existent chapter
    print("\n2. Testing cache check for non-existent chapter...")
    # Create cache for non-existent book
    non_existent_cache = TranslationCache(
        vault_path, "NonExistentBook", force_retranslate=False
    )
    chapter_num = 0

    cached_content = non_existent_cache.get_cached_translation(chapter_num)

    if cached_content:
        print(
            f"   ❌ Unexpectedly found cached translation for NonExistentBook chapter {chapter_num}"
        )
    else:
        print(
            f"   ✅ Correctly no cached translation for NonExistentBook chapter {chapter_num}"
        )

    # Test 3: Test cache status
    print("\n3. Testing cache status check...")
    status = cache.check_cache_status(chapter_num=1)
    print(f"   Cache initialized: True")
    print(f"   Vault path: {cache.vault_path}")
    print(f"   Force retranslate: {status['force_retranslate']}")
    print(f"   File exists: {status['file_exists']}")
    print(f"   Has content: {status['has_content']}")
    print(f"   Cached: {status['cached']}")
    print(f"   File path: {status['file_path']}")

    print("\n" + "=" * 50)
    print("✅ Cache system test completed!")


if __name__ == "__main__":
    test_cache()
