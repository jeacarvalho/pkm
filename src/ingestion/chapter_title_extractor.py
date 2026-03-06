"""Chapter title extraction utilities."""

import re
from typing import Dict, List


class ChapterTitleExtractor:
    """Extract chapter titles from PDF first pages."""

    @staticmethod
    def extract(first_page_text: str, chapter_num: int) -> str:
        """Extract chapter title from first page text.

        Looks for patterns like:
        - "CHAPTER X: Title" or "Chapter X"
        - Lines in UPPERCASE at the beginning
        - First significant line of text

        Args:
            first_page_text: Text extracted from first page of chapter
            chapter_num: Chapter number (0-indexed)

        Returns:
            Chapter title string or "Chapter X" if not found
        """
        if not first_page_text:
            return f"Chapter {chapter_num + 1}"

        lines = first_page_text.strip().split("\n")
        lines = [line.strip() for line in lines if line.strip()]

        if not lines:
            return f"Chapter {chapter_num + 1}"

        # Strategy 1: Look for "CHAPTER X" pattern
        for line in lines[:5]:
            match = re.match(
                r"^(?:CHAPTER|Capítulo|Cap[ií]tulo)\s+\d+[:\s]+(.+)",
                line,
                re.IGNORECASE,
            )
            if match:
                title = match.group(1).strip()
                if len(title) > 3:
                    return title

        # Strategy 2: Look for first significant line
        for line in lines[:3]:
            line = line.strip()
            if len(line) < 5 or line.isdigit() or re.match(r"^\d+\.\d+$", line):
                continue
            if len(line) < 20 and line.isupper():
                continue
            return line

        return f"Chapter {chapter_num + 1}"


def extract_chapter_title(first_page_text: str, chapter_num: int) -> str:
    """Convenience function for chapter title extraction."""
    return ChapterTitleExtractor.extract(first_page_text, chapter_num)
