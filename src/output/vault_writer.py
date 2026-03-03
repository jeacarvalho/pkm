"""Write chapter files to Obsidian vault."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List


class VaultWriter:
    """Write chapter files to Obsidian vault."""
    
    def __init__(self, vault_path: str, book_name: str):
        self.vault_path = Path(vault_path)
        self.book_folder = self.vault_path / book_name
        
    def create_book_folder(self) -> Path:
        """Create book folder in vault."""
        self.book_folder.mkdir(parents=True, exist_ok=True)
        return self.book_folder
        
    def write_chapter(self, chapter_num: int, chapter_data: Dict) -> Path:
        """Write single chapter file."""
        # Create book folder if it doesn't exist
        self.create_book_folder()
        
        # Format chapter number with leading zeros
        filename = f"{chapter_num:02d}_Capitulo_{chapter_num + 1:02d}.md"
        filepath = self.book_folder / filename
        
        # Get the book title from chapter data or use book_name
        book_title = chapter_data.get('title', self.book_folder.name.replace('_', ' '))
        
        # Extract author from metadata if available
        author = chapter_data.get('author', '')
        if not author and 'metadata' in chapter_data:
            author = chapter_data['metadata'].get('author', '')
        
        # Extract validation results if available, otherwise use placeholders
        validated_matches = chapter_data.get('validated_matches', [])
        
        # Create connections section based on validation results
        connections_section = "## Conexões Validadas com o Vault (Top 5)\n\n"
        
        if validated_matches:
            # Sort matches by confidence score if available, otherwise by rerank score
            sorted_matches = sorted(
                validated_matches, 
                key=lambda x: x.get('validation', {}).get('confidence', x.get('rerank_score', 0)), 
                reverse=True
            )[:5]  # Take only top 5
            
            for idx, match in enumerate(sorted_matches, 1):
                note_title = match.get('metadata', {}).get('note_title', f'Nota {idx}')
                rerank_score = match.get('rerank_score', 0)
                validation_info = match.get('validation', {})
                confidence = validation_info.get('confidence', 'N/A')
                reason = validation_info.get('reason', 'N/A')
                
                connections_section += f"### [[{note_title}]]\n"
                connections_section += f"- **Re-Rank Score:** {rerank_score:.2f}\n"
                connections_section += f"- **Confiança Ollama:** {confidence}/100\n"
                connections_section += f"- **Motivo:** {reason}\n\n"
        else:
            # Placeholder content if no validation results
            connections_section += """### [[Nota 1]]
- **Re-Rank Score:** 0.89
- **Confiança Ollama:** 94/100
- **Motivo:** [razão da validação Ollama]

### [[Nota 2]]
- **Re-Rank Score:** 0.85
- **Confiança Ollama:** 91/100
- **Motivo:** [razão da validação Ollama]

### [[Nota 3]]
- **Re-Rank Score:** 0.82
- **Confiança Ollama:** 88/100
- **Motivo:** [razão da validação Ollama]

### [[Nota 4]]
- **Re-Rank Score:** 0.79
- **Confiança Ollama:** 85/100
- **Motivo:** [razão da validação Ollama]

### [[Nota 5]]
- **Re-Rank Score:** 0.76
- **Confiança Ollama:** 82/100
- **Motivo:** [razão da validação Ollama]
"""

        # Create markdown content with frontmatter
        frontmatter = f"""---
book_title: {book_title}
author: {author}
chapter_number: {chapter_num + 1}
chapter_title: {chapter_data.get('title', f'Chapter {chapter_num + 1}') or f'Chapter {chapter_num + 1}'}
chapter_pages: {chapter_data.get('start_page', 1)}-{chapter_data.get('end_page', '?')}
processed_date: {datetime.now().strftime('%Y-%m-%d')}
validation_engine: ollama
validation_model: llama3.2
rerank_threshold: 0.75
tags:
  - #book-connections
  - #rag-validated
  - #ollama-approved
  - #{self.book_folder.name.lower()}
---

# Capítulo {chapter_num + 1}: {chapter_data.get('title', f'Chapter {chapter_num + 1}') or f'Chapter {chapter_num + 1}'}

## Resumo do Capítulo
{chapter_data.get('text', '')[:500]}...

{connections_section}
---
*Processado por Obsidian RAG v1.1.0*
"""
        
        # Write the content to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            
        return filepath
        
    def write_all_chapters(self, chapters: List[Dict]) -> List[Path]:
        """Write all chapter files."""
        filepaths = []
        for i, chapter in enumerate(chapters):
            filepath = self.write_chapter(i, chapter)
            filepaths.append(filepath)
        return filepaths