"""Markdown templates for Obsidian output."""

DEFAULT_FRONTMATTER_TEMPLATE = """---
validation_engine: ollama
validation_model: {validation_model}
validation_status: {validation_status}
book_title: {book_title}
book_path: {book_path}
processed_date: {processed_date}
rerank_threshold: {rerank_threshold}
total_chunks: {total_chunks}
chunks_with_matches: {chunks_with_matches}
total_validated_matches: {total_validated_matches}
tags:
  - #book-connections
  - #rag-validated
  - #ollama-approved
---"""

DEFAULT_BODY_TEMPLATE = """# Conexões Validadas: {book_title}

**Gerado em:** {generated_date}
**Chunks processados:** {total_chunks}
**Chunks com matches:** {chunks_with_matches}

---

{chapter_sections}

---

## Resumo das Conexões

{summary_table}"""

CHAPTER_TEMPLATE = """## {chapter_title}

{chunk_sections}"""

CHUNK_TEMPLATE = """### Trecho do Livro

> {chunk_text}

### Notas Relacionadas (Validadas)

{match_sections}"""

MATCH_TEMPLATE = """#### [[{note_title}]]

- **Re-Rank Score:** {rerank_score}
- **Confiança Ollama:** {confidence}/100
- **Motivo:** {reason}"""

SUMMARY_TABLE_HEADER = """| Nota | Menções | Confiança Média | Score Médio |
|------|---------|-----------------|-------------|"""

SUMMARY_TABLE_ROW = "| [[{note_title}]] | {count} | {avg_confidence} | {avg_score} |"
