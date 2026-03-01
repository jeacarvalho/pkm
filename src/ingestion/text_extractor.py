"""Text extraction utilities for PDF processing using PyMuPDF."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from src.utils.exceptions import PDFExtractionError


def extract_text_from_pdf(
    pdf_path: Path, start_page: Optional[int] = None, end_page: Optional[int] = None
) -> List[Dict[str, str]]:
    """Extract text from PDF file by pages.

    Args:
        pdf_path: Path to PDF file.
        start_page: Starting page number (0-indexed). If None, start from beginning.
        end_page: Ending page number (exclusive). If None, go to end.

    Returns:
        List of dicts with page number and text content.

    Raises:
        PDFExtractionError: If PDF cannot be opened or read.

    Example:
        >>> pages = extract_text_from_pdf(Path("book.pdf"))
        >>> len(pages)
        300
    """
    try:
        doc = fitz.open(str(pdf_path))
        pages = []

        # Determine page range
        start = start_page or 0
        end = end_page or len(doc)

        for page_num in range(start, min(end, len(doc))):
            page = doc[page_num]

            # Get text with formatting preserved
            text = page.get_text("text")

            # Also try to extract any table of contents info
            links = page.get_links()

            pages.append(
                {
                    "page_number": page_num + 1,  # 1-indexed for user display
                    "text": text,
                    "char_count": len(text),
                    "has_links": len(links) > 0,
                }
            )

        doc.close()
        return pages

    except Exception as e:
        raise PDFExtractionError(f"Failed to extract text from {pdf_path}: {e}") from e


def extract_toc(pdf_path: Path) -> List[Dict[str, str]]:
    """Extract table of contents from PDF.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        List of dicts with level, title, and page number.
    """
    try:
        doc = fitz.open(str(pdf_path))
        toc = doc.get_toc()
        doc.close()

        return [
            {"level": level, "title": title, "page": page} for level, title, page in toc
        ]
    except Exception as e:
        raise PDFExtractionError(f"Failed to extract TOC from {pdf_path}: {e}") from e


def get_pdf_metadata(pdf_path: Path) -> Dict[str, Optional[str]]:
    """Extract metadata from PDF file.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        Dict with metadata fields.
    """
    try:
        doc = fitz.open(str(pdf_path))
        metadata = doc.metadata
        doc.close()

        return {
            "title": metadata.get("title"),
            "author": metadata.get("author"),
            "subject": metadata.get("subject"),
            "creator": metadata.get("creator"),
            "producer": metadata.get("producer"),
            "creation_date": metadata.get("creationDate"),
            "modification_date": metadata.get("modDate"),
            "page_count": metadata.get("page_count"),
        }
    except Exception as e:
        raise PDFExtractionError(f"Failed to get metadata from {pdf_path}: {e}") from e


def extract_chapters(
    pdf_path: Path, toc: Optional[List[Dict]] = None
) -> List[Dict[str, str]]:
    """Extract text organized by chapters using TOC.

    If no TOC available, falls back to page-by-page extraction.

    Args:
        pdf_path: Path to PDF file.
        toc: Optional pre-extracted TOC.

    Returns:
        List of dicts with chapter title and text.
    """
    if toc is None:
        try:
            toc = extract_toc(pdf_path)
        except PDFExtractionError:
            toc = []

    if not toc:
        # No TOC available, return pages as "chapters"
        pages = extract_text_from_pdf(pdf_path)
        return [
            {
                "title": f"Page {p['page_number']}",
                "text": p["text"],
                "page_start": p["page_number"],
                "page_end": p["page_number"],
            }
            for p in pages
        ]

    # Extract text by chapters using TOC
    chapters = []
    doc = fitz.open(str(pdf_path))

    for i, entry in enumerate(toc):
        level = entry["level"]
        title = entry["title"]
        page = entry["page"]

        # Determine end page (next chapter or end of document)
        if i + 1 < len(toc):
            end_page = toc[i + 1]["page"]
        else:
            end_page = len(doc)

        # Extract text for this chapter
        text_parts = []
        for page_num in range(page - 1, min(end_page - 1, len(doc))):
            text_parts.append(doc[page_num].get_text("text"))

        chapters.append(
            {
                "title": title,
                "level": level,
                "text": "\n".join(text_parts),
                "page_start": page,
                "page_end": end_page - 1,
                "char_count": sum(len(part) for part in text_parts),
            }
        )

    doc.close()
    return chapters


def extract_text_by_range(pdf_path: Path, start_page: int, end_page: int) -> str:
    """Extract text from a specific page range.

    Args:
        pdf_path: Path to PDF file.
        start_page: Starting page (0-indexed).
        end_page: Ending page (exclusive).

    Returns:
        Concatenated text from the range.
    """
    pages = extract_text_from_pdf(pdf_path, start_page, end_page)
    return "\n\n".join(p["text"] for p in pages)
