"""Write chapter files to Obsidian vault."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List


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
        lines.append(f"validation_model: {self.config.validation_model}")
        lines.append(f"rerank_threshold: {chapter_data.get('rerank_threshold', 0.75)}")
        lines.append(f"translation_cached: {chapter_data.get('was_cached', False)}")
        lines.append("tags:")
        lines.append("  - #book-connections")
        lines.append("  - #rag-validated")
        lines.append("  - #gemini-approved")
        lines.append(f"  - #{self.book_folder.name.lower()}")
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

        # Validated matches
        lines.append("## Conexões Validadas com o Vault (Top 5)")
        lines.append("")

        validated_matches = chapter_data.get("validated_matches", [])
        if validated_matches:
            for match in validated_matches[:5]:
                note_title = match.get("metadata", {}).get("note_title", "Unknown")
                rerank_score = match.get("rerank_score", 0.0)
                validation = match.get("validation", {})
                confidence = validation.get("confidence", 0)
                reason = validation.get("reason", "Sem motivo")

                lines.append(f"### [[{note_title}]]")
                lines.append("")
                lines.append(f"- **Re-Rank Score:** {rerank_score:.3f}")
                lines.append(f"- **Confiança Gemini:** {confidence}/100")
                lines.append(f"- **Motivo:** {reason}")
                lines.append("")
        else:
            lines.append(
                "*Nenhuma conexão validada para este capítulo (use --validate para executar validação)*"
            )
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
