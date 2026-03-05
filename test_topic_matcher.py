#!/usr/bin/env python3
"""
Test script to verify TopicMatcher functionality
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig


def test_topic_matcher():
    """Test if TopicMatcher finds notes with topic_classification"""

    # Create test chapter topics (similar to leadership topics)
    test_chapter_topics = [
        {"name": "gestao_de_pessoas", "weight": 10, "confidence": 0.98},
        {"name": "lideranca", "weight": 9, "confidence": 0.95},
        {"name": "planejamento_estrategico", "weight": 8, "confidence": 0.92},
    ]

    # Save test topics to file
    test_file = Path("test_chapter_topics.json")
    import json

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(
            {"topics": test_chapter_topics, "chapter_title": "Test Chapter"},
            f,
            indent=2,
        )

    print(f"📝 Created test file: {test_file}")

    # Create matcher
    config = TopicConfig()
    matcher = TopicMatcher(config)

    # Test with correct vault directory (entire vault)
    vault_dir = Path("/home/s015533607/MEGAsync/Minhas_notas")
    print(f"📁 Testing with vault directory: {vault_dir}")
    print(f"📁 Directory exists: {vault_dir.exists()}")

    # Run matching
    result = matcher.run(
        chapter_topics_path=test_file,
        vault_dir=vault_dir,
        output_path=None,
        top_k=10,
        threshold=0.0,  # Low threshold to see all matches
    )

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Chapter: {result.get('chapter', 'Unknown')}")
        print(f"📊 Total notes scanned: {result.get('total_notes_scanned', 0)}")
        print(f"📊 Notes with topics: {result.get('notes_with_topics', 0)}")
        print(f"📊 Total matches found: {result.get('total_matches_found', 0)}")

        if result.get("matches"):
            print(f"\n🏆 Top matches:")
            for i, match in enumerate(result["matches"][:5], 1):
                print(
                    f"  {i}. {match.get('note_title', 'Unknown')} (score: {match.get('score', 0)})"
                )
        else:
            print(f"\n⚠️ No matches found")

    # Clean up
    if test_file.exists():
        test_file.unlink()

    return result


if __name__ == "__main__":
    test_topic_matcher()
