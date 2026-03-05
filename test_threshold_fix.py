#!/usr/bin/env python3
"""Test the topic matcher with threshold=5.0"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig


def test_threshold():
    """Test topic matching with threshold=5.0"""

    # Load test chapter topics
    test_file = Path("data/test/capitulo_01_topics.json")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    with open(test_file, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)

    print(f"Loaded chapter data with {len(chapter_data)} topics")

    # Create config and topic matcher
    config = TopicConfig()
    matcher = TopicMatcher(config)

    # Test with threshold=5.0
    print("\n=== Testing with threshold=5.0 ===")
    result = matcher.run(
        chapter_topics_path=test_file,
        vault_dir=Path("/home/s015533607/MEGAsync/Minhas_notas"),
        output_path=None,
        top_k=5,
        threshold=5.0,
    )

    print(f"Matches found: {len(result.get('matches', []))}")

    if "matches" in result and result["matches"]:
        print("\nTop matches:")
        for i, match in enumerate(result["matches"][:5], 1):
            print(
                f"{i}. {match.get('note_path', 'N/A')} - Score: {match.get('score', 0):.2f}"
            )
    else:
        print("No matches found with threshold=5.0")

    # Also test with threshold=0.0 for comparison
    print("\n=== Testing with threshold=0.0 (for comparison) ===")
    result_zero = matcher.run(
        chapter_topics_path=test_file,
        vault_dir=Path("/home/s015533607/MEGAsync/Minhas_notas"),
        output_path=None,
        top_k=5,
        threshold=0.0,
    )

    print(f"Matches found: {len(result_zero.get('matches', []))}")

    if "matches" in result_zero and result_zero["matches"]:
        print("\nTop matches with threshold=0.0:")
        for i, match in enumerate(result_zero["matches"][:5], 1):
            print(
                f"{i}. {match.get('note_path', 'N/A')} - Score: {match.get('score', 0):.2f}"
            )


if __name__ == "__main__":
    test_threshold()
