"""Parse capitulos.txt file and validate chapter ranges."""

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Chapter:
    """Represents a chapter with its page range."""

    num: int
    start_page: int
    end_page: int

    @property
    def page_range(self) -> str:
        """Get page range as string."""
        return f"{self.start_page}-{self.end_page}"


class ChapterParser:
    """Parse capitulos.txt file and validate chapter ranges."""

    def __init__(self):
        self.chapters: List[Chapter] = []

    def parse(self, filepath: str) -> List[Chapter]:
        """Parse file and return list of Chapter objects.

        Supports formats:
        - "1: 18,33" (chapter: start,end)
        - "18,33" (start,end - auto-numbered)
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Chapter file not found: {filepath}")

        chapters = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                try:
                    # Check for "chapter: start,end" format
                    if ":" in line:
                        parts = line.split(":")
                        chapter_label = parts[0].strip()
                        page_part = parts[1].strip()

                        # Try to extract chapter number from label
                        try:
                            chapter_num = int(chapter_label) - 1  # Convert to 0-indexed
                        except ValueError:
                            chapter_num = len(chapters)  # Fallback to auto-numbering

                        # Parse page range
                        page_parts = page_part.split(",")
                        if len(page_parts) != 2:
                            raise ValueError(
                                f"Invalid format at line {line_num}: expected 'start,end'"
                            )
                        start_page = int(page_parts[0].strip())
                        end_page = int(page_parts[1].strip())
                    else:
                        # Parse inicio,fim format (auto-numbered)
                        parts = line.split(",")
                        if len(parts) != 2:
                            raise ValueError(
                                f"Invalid format at line {line_num}: expected 'inicio,fim'"
                            )

                        start_page = int(parts[0].strip())
                        end_page = int(parts[1].strip())
                        chapter_num = len(chapters)

                    if start_page <= 0 or end_page <= 0:
                        raise ValueError(
                            f"Page numbers must be positive at line {line_num}"
                        )

                    if start_page > end_page:
                        raise ValueError(
                            f"Start page cannot be greater than end page at line {line_num}"
                        )

                    chapter = Chapter(
                        num=chapter_num, start_page=start_page, end_page=end_page
                    )
                    chapters.append(chapter)

                except ValueError as e:
                    if "invalid literal for int()" in str(e):
                        raise ValueError(
                            f"Invalid page number format at line {line_num}: {line}"
                        )
                    else:
                        raise e

        self.chapters = chapters
        return chapters

    def validate(self, chapters: List[Chapter]) -> bool:
        """Validate no overlaps and consecutive pages."""
        if not chapters:
            return True

        # Sort chapters by start page
        sorted_chapters = sorted(chapters, key=lambda x: x.start_page)

        for i in range(len(sorted_chapters) - 1):
            current = sorted_chapters[i]
            next_chapter = sorted_chapters[i + 1]

            # Check for overlap
            if current.end_page >= next_chapter.start_page:
                raise ValueError(
                    f"Overlap detected: Chapter {current.num} ({current.page_range}) "
                    f"overlaps with Chapter {next_chapter.num} ({next_chapter.page_range})"
                )

            # Check for gaps (optional warning)
            if current.end_page + 1 < next_chapter.start_page:
                print(
                    f"WARNING: Gap detected between Chapter {current.num} (ended at page {current.end_page}) "
                    f"and Chapter {next_chapter.num} (started at page {next_chapter.start_page})"
                )

        return True

    def get_total_pages(self) -> int:
        """Return total pages covered by all chapters."""
        if not self.chapters:
            return 0
        return (
            max(chapter.end_page for chapter in self.chapters) if self.chapters else 0
        )
