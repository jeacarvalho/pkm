"""Topic extraction service for chapters."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

from src.topics.topic_extractor import TopicExtractor
from src.topics.config import TopicConfig
from src.utils.logging import get_logger


logger = get_logger(__name__)


class TopicExtractionService:
    """Service responsible only for extracting topics from chapters.

    Responsibilities:
    - Extract topics from translated chapter text
    - Save topic JSON for each chapter
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize topic extraction service.

        Args:
            output_dir: Directory to save topic JSONs
        """
        self.output_dir = output_dir or Path("data/logs/topics")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extractor
        config = TopicConfig()
        self.extractor = TopicExtractor(config)

        logger.info("TopicExtractionService initialized")

    def extract_topics(self, chapter_data: Dict) -> Dict:
        """Extract topics from a single chapter.

        Args:
            chapter_data: Chapter data with 'chapter_text', 'chapter_num', 'title'

        Returns:
            Chapter data with added topic_classification
        """
        chapter_num = chapter_data["chapter_num"]
        chapter_text = chapter_data.get("chapter_text", "")
        title = chapter_data.get("title", f"Chapter {chapter_num + 1}")

        if not chapter_text:
            logger.warning(f"Empty chapter text for chapter {chapter_num}")
            chapter_data["topic_classification"] = None
            return chapter_data

        try:
            logger.info(f"Extracting topics for chapter {chapter_num}...")

            topics_result = self.extractor.extract_topics(chapter_text)

            chapter_data["topic_classification"] = {
                "topics": topics_result.get("topics", []),
                "cdu_primary": topics_result.get("cdu_primary"),
                "cdu_secondary": topics_result.get("cdu_secondary", []),
                "cdu_description": topics_result.get("cdu_description"),
                "content_summary": topics_result.get("content_summary"),
            }

            # Save to JSON
            self._save_topics_json(chapter_num, title, topics_result)

            return chapter_data

        except Exception as e:
            logger.error(f"Topic extraction failed for chapter {chapter_num}: {e}")
            chapter_data["topic_classification"] = None
            return chapter_data

    def _save_topics_json(
        self, chapter_num: int, title: str, topics_result: Dict
    ) -> None:
        """Save topics to JSON file.

        Args:
            chapter_num: Chapter number
            title: Chapter title
            topics_result: Topics result from extractor
        """
        output_file = self.output_dir / f"chapter_{chapter_num:02d}_topics.json"

        data = {"chapter_num": chapter_num, "chapter_title": title, **topics_result}

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved topics to {output_file}")

    def process_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Process all chapters for topic extraction.

        Args:
            chapters: List of chapter data

        Returns:
            List of chapters with added topic_classification
        """
        logger.info(f"Extracting topics for {len(chapters)} chapters...")

        processed = []
        for chapter in tqdm(chapters, desc="Extracting topics"):
            processed_chapter = self.extract_topics(chapter)
            processed.append(processed_chapter)

        return processed
