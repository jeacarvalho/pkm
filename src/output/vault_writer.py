"""Write chapter files to Obsidian vault."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from src.utils.config import settings


class VaultWriter:
    """Write chapter files to Obsidian vault."""

    def __init__(self, vault_path: str, book_name: str):
        # vault_path already includes "100 ARQUIVOS E REFERENCIAS/Livros"
        self.vault_path = Path(vault_path)
        self.book_folder = self.vault_path / book_name

    def create_book_folder(self) -> Path:
        """Create book folder in vault."""
        self.book_folder.mkdir(parents=True, exist_ok=True)
        return self.book_folder

    def write_chapter(self, chapter_num: int, chapter_data: Dict) -> Path:
        """Write single chapter file with full translated content."""
        self.create_book_folder()

        filename = f"{chapter_num:02d}_Capitulo_{chapter_num + 1:02d}.md"
        filepath = self.book_folder / filename

        content = self._build_markdown(chapter_num, chapter_data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Written: {filepath}")
        return filepath

    def _build_markdown(self, chapter_num: int, chapter_data: Dict) -> str:
        """Build Markdown with full translated content + validated matches."""
        lines = []

        # Frontmatter
        lines.append("---")
        lines.append(f"book_title: {chapter_data.get('book_title', 'Unknown')}")
        lines.append(f"author: {chapter_data.get('author', '')}")
        lines.append(f"chapter_number: {chapter_num + 1}")
        lines.append(
            f"chapter_title: {chapter_data.get('title', f'Chapter {chapter_num + 1}')}"
        )
        lines.append(
            f"chapter_pages: {chapter_data.get('start_page', '?')}-{chapter_data.get('end_page', '?')}"
        )
        lines.append(f"processed_date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"validation_engine: gemini")
        lines.append(f"validation_model: {settings.validation_model}")
        lines.append(f"rerank_threshold: {chapter_data.get('rerank_threshold', 0.75)}")
        lines.append(f"translation_cached: {chapter_data.get('was_cached', False)}")
        lines.append("tags:")
        lines.append("  - #book-connections")
        lines.append("  - #rag-validated")
        lines.append("  - #gemini-approved")
        lines.append(f"  - #{self.book_folder.name.lower()}")

        # Add topic classification if available
        topic_classification = chapter_data.get("topic_classification")
        if topic_classification:
            lines.append("topic_classification:")

            # Add topics
            topics = topic_classification.get("topics", [])
            if topics:
                lines.append("  topics:")
                for topic in topics[:10]:  # Limit to top 10 topics
                    name = topic.get("name", "")
                    weight = topic.get("weight", 5)
                    confidence = topic.get("confidence", 0.0)
                    lines.append(f"    - name: {name}")
                    lines.append(f"      weight: {weight}")
                    lines.append(f"      confidence: {confidence}")

            # Add CDU information
            cdu_primary = topic_classification.get("cdu_primary")
            if cdu_primary:
                lines.append(f"  cdu_primary: {cdu_primary}")

            cdu_secondary = topic_classification.get("cdu_secondary", [])
            if cdu_secondary:
                lines.append(f"  cdu_secondary: {cdu_secondary}")

            cdu_description = topic_classification.get("cdu_description")
            if cdu_description:
                lines.append(f"  cdu_description: {cdu_description}")

            extraction_date = topic_classification.get("extraction_date")
            if extraction_date:
                lines.append(f"  extraction_date: {extraction_date}")

        # Add thematic connections if available
        thematic_connections = chapter_data.get("thematic_connections")
        if thematic_connections:
            lines.append("thematic_connections:")
            for connection in thematic_connections[:10]:  # Limit to top 10 connections
                note_path = connection.get("note_path", "")
                score = connection.get("score", 0.0)  # Changed from similarity to score
                matched_topics = connection.get("matched_topics", [])
                lines.append(f"  - note_path: {note_path}")
                lines.append(f"    score: {score}")  # Changed from similarity to score
                lines.append(f"    matched_topics: {matched_topics}")

        lines.append("---")
        lines.append("")

        # Title
        lines.append(
            f"# Capítulo {chapter_num + 1}: {chapter_data.get('title', f'Capítulo {chapter_num + 1}')}"
        )
        lines.append("")

        # FULL TRANSLATED CONTENT (not summary!)
        lines.append("## Conteúdo Traduzido")
        lines.append("")
        lines.append(chapter_data.get("chapter_text", "").strip())
        lines.append("")
        lines.append("---")
        lines.append("")

        # Thematic connections (Top 5)
        lines.append("## Conexões Validadas com o Vault (Top 5)")
        lines.append("")

        thematic_connections = chapter_data.get("thematic_connections", [])
        if thematic_connections:
            # Filter out self-references (chapter matching with itself)
            filtered_connections = []
            for conn in thematic_connections:
                note_path = conn.get("note_path", "")
                # Skip if note_path contains the current book directory
                if "Livros/" in note_path and self.book_folder.name in note_path:
                    continue
                filtered_connections.append(conn)

            # Take top 5 filtered connections
            for connection in filtered_connections[:5]:
                note_title = connection.get("note_title", "Unknown")
                score = connection.get("score", 0.0)
                matched_topics = connection.get("matched_topics", [])

                lines.append(f"### [[{note_title}]]")
                lines.append("")
                lines.append(f"- **Score de Similaridade Temática:** {score}")
                lines.append(f"- **Tópicos Correspondentes:** {len(matched_topics)}")
                if matched_topics:
                    lines.append(
                        f"- **Exemplo de Match:** {matched_topics[0].get('chapter_topic', '')} → {matched_topics[0].get('vault_topic', '')}"
                    )
                lines.append("")
        else:
            lines.append("*Nenhuma conexão temática encontrada para este capítulo*")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(
            f"*Processado por Obsidian RAG v1.1.1 | Validação: Gemini 2.0 Flash*"
        )

        return "\n".join(lines)

    def write_all_chapters(self, chapters: List[Dict]) -> List[Path]:
        """Write all chapter files."""
        filepaths = []
        for i, chapter in enumerate(chapters):
            filepath = self.write_chapter(i, chapter)
            filepaths.append(filepath)
        return filepaths
