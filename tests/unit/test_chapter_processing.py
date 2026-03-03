"""Tests for chapter processing functionality."""

import tempfile
import os
from pathlib import Path
from src.ingestion.chapter_parser import ChapterParser, Chapter


def test_chapter_parser_valid_format():
    """Test parser with valid capitulos.txt format."""
    # Create temporary file with valid content
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("1,15\n")
        f.write("16,32\n")
        f.write("33,50\n")
        temp_file = f.name

    try:
        parser = ChapterParser()
        chapters = parser.parse(temp_file)
        
        assert len(chapters) == 3
        
        # Check first chapter
        assert chapters[0].num == 0
        assert chapters[0].start_page == 1
        assert chapters[0].end_page == 15
        
        # Check second chapter
        assert chapters[1].num == 1
        assert chapters[1].start_page == 16
        assert chapters[1].end_page == 32
        
        # Check third chapter
        assert chapters[2].num == 2
        assert chapters[2].start_page == 33
        assert chapters[2].end_page == 50
        
    finally:
        os.unlink(temp_file)


def test_chapter_parser_with_comments():
    """Test parser handles comments and empty lines."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("# This is a comment\n")
        f.write("1,15\n")
        f.write("\n")  # Empty line
        f.write("16,32\n")
        f.write("# Another comment\n")
        f.write("33,50\n")
        temp_file = f.name

    try:
        parser = ChapterParser()
        chapters = parser.parse(temp_file)
        
        assert len(chapters) == 3
        assert chapters[0].start_page == 1
        assert chapters[1].start_page == 16
        assert chapters[2].start_page == 33
        
    finally:
        os.unlink(temp_file)


def test_chapter_parser_invalid_format():
    """Test parser raises exception for invalid format."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("1,2,3\n")  # Invalid format
        temp_file = f.name

    try:
        parser = ChapterParser()
        try:
            parser.parse(temp_file)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "expected 'inicio,fim'" in str(e)
            
    finally:
        os.unlink(temp_file)


def test_chapter_parser_negative_pages():
    """Test parser raises exception for negative page numbers."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("-1,15\n")  # Negative start page
        temp_file = f.name

    try:
        parser = ChapterParser()
        try:
            parser.parse(temp_file)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be positive" in str(e)
            
    finally:
        os.unlink(temp_file)


def test_chapter_parser_start_greater_than_end():
    """Test parser raises exception when start page > end page."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("15,1\n")  # Start > End
        temp_file = f.name

    try:
        parser = ChapterParser()
        try:
            parser.parse(temp_file)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "cannot be greater than end page" in str(e)
            
    finally:
        os.unlink(temp_file)


def test_chapter_parser_overlapping_ranges():
    """Test validation detects overlapping chapter ranges."""
    parser = ChapterParser()
    chapters = [
        Chapter(num=0, start_page=1, end_page=15),
        Chapter(num=1, start_page=10, end_page=20)  # Overlaps with first chapter
    ]
    
    try:
        parser.validate(chapters)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Overlap detected" in str(e)


def test_chapter_parser_gap_warning(capsys):
    """Test validation detects gaps between chapters."""
    parser = ChapterParser()
    chapters = [
        Chapter(num=0, start_page=1, end_page=15),
        Chapter(num=1, start_page=20, end_page=30)  # Gap between 15 and 20
    ]
    
    # This should produce a warning
    parser.validate(chapters)
    
    captured = capsys.readouterr()
    assert "Gap detected" in captured.out


def test_chapter_parser_consecutive_ranges():
    """Test validation passes for consecutive chapter ranges."""
    parser = ChapterParser()
    chapters = [
        Chapter(num=0, start_page=1, end_page=15),
        Chapter(num=1, start_page=16, end_page=30),  # Consecutive to first chapter
        Chapter(num=2, start_page=31, end_page=45)   # Consecutive to second chapter
    ]
    
    # Should not raise any exceptions
    result = parser.validate(chapters)
    assert result is True


def test_get_total_pages():
    """Test getting total pages covered by all chapters."""
    parser = ChapterParser()
    chapters = [
        Chapter(num=0, start_page=1, end_page=15),
        Chapter(num=1, start_page=16, end_page=30),
        Chapter(num=2, start_page=31, end_page=45)
    ]
    parser.chapters = chapters
    
    total = parser.get_total_pages()
    assert total == 45


def test_get_total_pages_empty():
    """Test getting total pages when no chapters exist."""
    parser = ChapterParser()
    
    total = parser.get_total_pages()
    assert total == 0


def test_chapter_page_range_property():
    """Test the page_range property of Chapter class."""
    chapter = Chapter(num=0, start_page=1, end_page=15)
    assert chapter.page_range == "1-15"
    
    chapter = Chapter(num=1, start_page=100, end_page=200)
    assert chapter.page_range == "100-200"