"""Markdown generator for Obsidian output."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.output.templates import (
    DEFAULT_FRONTMATTER_TEMPLATE,
    DEFAULT_BODY_TEMPLATE,
)
from src.utils.config import Settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MarkdownGenerator:
    """Generate Obsidian Markdown files from validated matches.

    This class creates formatted Markdown files with:
    - YAML frontmatter with validation metadata
    - Book chunk excerpts with context
    - Obsidian wikilinks to validated notes
    - Summary table of all connections

    Attributes:
        config: Application settings.
        output_dir: Directory to save generated Markdown files.

    Example:
        >>> generator = MarkdownGenerator(Settings())
        >>> output_path = generator.generate_book_file(
        ...     book_title="Rhythms for Life",
        ...     book_path="/path/to/book.pdf",
        ...     validated_chunks=[...],
        ... )
        >>> print(f"Generated: {output_path}")
    """

    def __init__(
        self,
        config: Optional[Settings] = None,
        output_dir: str = "data/processed",
    ):
        """Initialize Markdown generator.

        Args:
            config: Application settings. If None, uses default.
            output_dir: Directory to save generated files.
        """
        self.config = config or Settings()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MarkdownGenerator initialized with output_dir: {self.output_dir}")

    def generate_book_file(
        self,
        book_title: str,
        book_path: str,
        validated_chunks: List[Dict[str, Any]],
        output_filename: Optional[str] = None,
    ) -> Path:
        """Generate a single Markdown file for a processed book.

        Args:
            book_title: Title of the book.
            book_path: Original PDF path.
            validated_chunks: List of chunks with validated matches.
            output_filename: Optional custom filename.

        Returns:
            Path to generated Markdown file.

        Example:
            >>> generator = MarkdownGenerator()
            >>> path = generator.generate_book_file(
            ...     book_title="Test Book",
            ...     book_path="/path/to/book.pdf",
            ...     validated_chunks=[...],
            ... )
            >>> path.exists()
            True
        """
        if output_filename is None:
            safe_title = "".join(
                c for c in book_title if c.isalnum() or c in " -_"
            ).strip()
            output_filename = f"{safe_title}_Conexoes.md"

        output_path = self.output_dir / output_filename

        content = self._build_markdown_content(book_title, book_path, validated_chunks)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated Markdown file: {output_path} ({len(content)} chars)")

        return output_path

    def _build_markdown_content(
        self,
        book_title: str,
        book_path: str,
        validated_chunks: List[Dict[str, Any]],
    ) -> str:
        """Build complete Markdown content with frontmatter and body.

        Args:
            book_title: Title of the book.
            book_path: Path to original PDF.
            validated_chunks: List of validated chunks.

        Returns:
            Complete Markdown content as string.
        """
        frontmatter = self._generate_frontmatter(
            book_title, book_path, validated_chunks
        )
        body = self._generate_body(book_title, validated_chunks)

        return f"{frontmatter}\n{body}"

    def _generate_frontmatter(
        self,
        book_title: str,
        book_path: str,
        validated_chunks: List[Dict[str, Any]],
    ) -> str:
        """Generate YAML frontmatter with validation metadata.

        Args:
            book_title: Title of the book.
            book_path: Path to original PDF.
            validated_chunks: List of validated chunks.

        Returns:
            YAML frontmatter as string.
        """
        total_chunks = len(validated_chunks)
        chunks_with_matches = sum(
            1 for c in validated_chunks if c.get("validated_matches")
        )
        total_matches = sum(
            len(c.get("validated_matches", [])) for c in validated_chunks
        )

        frontmatter = f"""---
validation_engine: ollama
validation_model: {self.config.validation_model}
validation_status: approved
book_title: {book_title}
book_path: {book_path}
processed_date: {datetime.now().strftime("%Y-%m-%d")}
rerank_threshold: {self.config.rerank_threshold}
total_chunks: {total_chunks}
chunks_with_matches: {chunks_with_matches}
total_validated_matches: {total_matches}
tags:
  - #book-connections
  - #rag-validated
  - #ollama-approved
---"""

        return frontmatter

    def _generate_body(
        self,
        book_title: str,
        validated_chunks: List[Dict[str, Any]],
    ) -> str:
        """Generate Markdown body content.

        Args:
            book_title: Title of the book.
            validated_chunks: List of validated chunks.

        Returns:
            Markdown body as string.
        """
        lines = []

        lines.append(f"# Conexões Validadas: {book_title}")
        lines.append("")
        lines.append(f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Chunks processados:** {len(validated_chunks)}")
        chunks_with = sum(1 for c in validated_chunks if c.get("validated_matches"))
        lines.append(f"**Chunks com matches:** {chunks_with}")
        lines.append("")
        lines.append("---")
        lines.append("")

        chunks_by_chapter = self._group_by_chapter(validated_chunks)

        for chapter, chunks in chunks_by_chapter.items():
            lines.append(f"## {chapter}")
            lines.append("")

            for chunk_data in chunks:
                chunk_content = self._format_chunk(chunk_data)
                lines.append(chunk_content)
                lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Resumo das Conexões")
        lines.append("")
        lines.append(self._generate_summary_table(validated_chunks))

        return "\n".join(lines)

    def _group_by_chapter(
        self, validated_chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group chunks by chapter.

        Args:
            validated_chunks: List of validated chunks.

        Returns:
            Dictionary mapping chapter names to chunks.
        """
        chapters: Dict[str, List[Dict[str, Any]]] = {}

        for chunk in validated_chunks:
            chapter = chunk.get("chapter_title", "Capítulo Desconhecido")
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(chunk)

        return chapters

    def _format_chunk(self, chunk_data: Dict[str, Any]) -> str:
        """Format a single chunk with its validated matches.

        Args:
            chunk_data: Chunk data with validated matches.

        Returns:
            Formatted chunk as Markdown string.
        """
        lines = []

        chunk_text = chunk_data.get("chunk_text", "")[:500]
        lines.append("### Trecho do Livro")
        lines.append("")
        lines.append(f"> {chunk_text}")
        lines.append("")

        validated_matches = chunk_data.get("validated_matches", [])

        if validated_matches:
            lines.append("### Notas Relacionadas (Validadas)")
            lines.append("")

            for match in validated_matches:
                note_title = match.get("metadata", {}).get("note_title", "Unknown")
                rerank_score = match.get("rerank_score", 0.0)
                validation = match.get("validation", {})
                confidence = validation.get("confidence", 0)
                reason = validation.get("reason", "No reason provided")

                lines.append(f"#### [[{note_title}]]")
                lines.append("")
                lines.append(f"- **Re-Rank Score:** {rerank_score:.3f}")
                lines.append(f"- **Confiança Ollama:** {confidence}/100")
                lines.append(f"- **Motivo:** {reason}")
                lines.append("")
        else:
            lines.append("*Nenhuma nota validada para este trecho*")
            lines.append("")

        return "\n".join(lines)

    def _generate_summary_table(self, validated_chunks: List[Dict[str, Any]]) -> str:
        """Generate summary table of all connections.

        Args:
            validated_chunks: List of validated chunks.

        Returns:
            Markdown table as string.
        """
        lines = []

        lines.append("| Nota | Menções | Confiança Média | Score Médio |")
        lines.append("|------|---------|-----------------|-------------|")

        note_stats: Dict[str, Dict[str, Any]] = {}

        for chunk in validated_chunks:
            for match in chunk.get("validated_matches", []):
                note_title = match.get("metadata", {}).get("note_title", "Unknown")
                rerank_score = match.get("rerank_score", 0.0)
                confidence = match.get("validation", {}).get("confidence", 0)

                if note_title not in note_stats:
                    note_stats[note_title] = {
                        "count": 0,
                        "scores": [],
                        "confidences": [],
                    }

                note_stats[note_title]["count"] += 1
                note_stats[note_title]["scores"].append(rerank_score)
                note_stats[note_title]["confidences"].append(confidence)

        for note_title, stats in sorted(
            note_stats.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            avg_confidence = sum(stats["confidences"]) / len(stats["confidences"])
            lines.append(
                f"| [[{note_title}]] | {stats['count']} | {avg_confidence:.0f} | {avg_score:.3f} |"
            )

        return "\n".join(lines)

    def import_to_vault(
        self,
        markdown_path: Path,
        vault_path: Optional[Path] = None,
    ) -> Path:
        """Import generated Markdown file to Obsidian vault.

        Args:
            markdown_path: Path to generated Markdown file.
            vault_path: Path to Obsidian vault. If None, uses config.

        Returns:
            Path where file was copied.
        """
        if vault_path is None:
            vault_path = self.config.vault_path

        dest_path = vault_path / "BookConnections" / markdown_path.name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(markdown_path, dest_path)

        logger.info(f"Imported to vault: {dest_path}")

        return dest_path
