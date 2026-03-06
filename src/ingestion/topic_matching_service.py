"""Topic matching service for finding vault connections."""

from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig
from src.utils.logging import get_logger


logger = get_logger(__name__)


class TopicMatchingService:
    """Service responsible only for matching chapters to vault notes.

    Responsibilities:
    - Find similar notes in vault based on topic classification
    - Return top-k matches for each chapter
    """

    def __init__(
        self,
        vault_path: str,
        top_k: int = 20,
        threshold: float = 0.0,
    ):
        """Initialize topic matching service.

        Args:
            vault_path: Path to Obsidian vault
            top_k: Number of top matches to return
            threshold: Minimum score threshold
        """
        self.vault_path = Path(vault_path)
        self.top_k = top_k
        self.threshold = threshold

        # Initialize matcher
        config = TopicConfig()
        config.match_top_k = top_k
        config.match_threshold = threshold

        self.matcher = TopicMatcher(config)

        logger.info(
            f"TopicMatchingService initialized (top_k={top_k}, threshold={threshold})"
        )

    def match_chapter(self, chapter_data: Dict) -> Dict:
        """Match a chapter to vault notes.

        Args:
            chapter_data: Chapter data with topic_classification

        Returns:
            Chapter data with added thematic_connections
        """
        chapter_num = chapter_data["chapter_num"]
        title = chapter_data.get("title", f"Chapter {chapter_num + 1}")
        topic_classification = chapter_data.get("topic_classification")

        if not topic_classification or not topic_classification.get("topics"):
            logger.warning(f"No topics found for chapter {chapter_num}")
            chapter_data["thematic_connections"] = []
            return chapter_data

        # Prepare chapter topics for matching
        chapter_topics = topic_classification.get("topics", [])

        # Get chapter info for matching
        chapter_topics_data = {
            "topics": chapter_topics,
            "cdu_primary": topic_classification.get("cdu_primary"),
            "cdu_secondary": topic_classification.get("cdu_secondary", []),
        }

        try:
            logger.info(f"Finding thematic connections for chapter {chapter_num}...")

            # Run matching
            matched = self.matcher.match_chapter_to_vault(
                chapter_topics=chapter_topics,  # List of topic dicts
                vault_dir=self.vault_path,
                top_k=self.top_k,
                threshold=self.threshold,
            )

            # Format matches
            connections = []
            for match in matched:
                connections.append(
                    {
                        "note_title": match.get("note_title", "Unknown"),
                        "note_path": match.get("note_path", ""),
                        "score": match.get("score", 0),
                        "matched_topics": match.get("matched_topics", []),
                        "cdu_match": match.get("cdu_bonus", False),
                    }
                )

            chapter_data["thematic_connections"] = connections
            logger.info(
                f"Found {len(connections)} connections for chapter {chapter_num}"
            )

            return chapter_data

        except Exception as e:
            logger.error(f"Topic matching failed for chapter {chapter_num}: {e}")
            chapter_data["thematic_connections"] = []
            return chapter_data

    def process_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Process all chapters for topic matching.

        Args:
            chapters: List of chapter data with topic_classification

        Returns:
            List of chapters with added thematic_connections
        """
        logger.info(f"Matching {len(chapters)} chapters to vault...")

        processed = []
        for chapter in tqdm(chapters, desc="Finding connections"):
            processed_chapter = self.match_chapter(chapter)
            processed.append(processed_chapter)

        return processed
