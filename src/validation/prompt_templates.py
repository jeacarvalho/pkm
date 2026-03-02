"""Prompt templates for Ollama validation."""

SYSTEM_PROMPT = """Você é um curador cético de conhecimento pessoal.
Sua tarefa é validar conexões semânticas entre trechos de livros e notas do Obsidian.

REGRAS CRÍTICAS:
1. Seja EXIGENTE - rejeite matches fracos ou superficiais
2. Só aprove se houver relação semântica CLARA e DIRETA
3. Considere o contexto completo da nota, não apenas palavras-chave
4. Similaridade temática não é suficiente - precisa haver conexão conceitual

FORMATO DE RESPOSTA:
Responda APENAS com JSON válido, sem markdown, sem code blocks, sem texto adicional.
Use esta estrutura:
{"approved": boolean, "confidence": integer, "reason": "explicação"}

Exemplo de resposta correta:
{"approved": true, "confidence": 85, "reason": "O conceito de antifragilidade no livro é diretamente aplicável à nota sobre resiliência"}

Exemplo de resposta ERRADA:
```json
{"approved": true}
```

NÃO use code blocks. NÃO use markdown. Apenas JSON puro."""


def build_validation_prompt(
    book_chunk: str,
    note_content: str,
    note_title: str,
    rerank_score: float,
) -> str:
    """Build validation prompt with all context.

    Args:
        book_chunk: Text from the book chapter.
        note_content: Full content of the Obsidian note.
        note_title: Title of the note.
        rerank_score: Score from re-ranker (0.0-1.0).

    Returns:
        Formatted prompt string.
    """
    # Truncate to avoid context overflow
    truncated_chunk = book_chunk[:2000] if len(book_chunk) > 2000 else book_chunk
    truncated_note = note_content[:3000] if len(note_content) > 3000 else note_content

    return f"""Valide esta conexão:

Livro: {truncated_chunk}

Nota "{note_title}": {truncated_note}

Score: {rerank_score:.3f}

Responda apenas JSON: {{"approved": bool, "confidence": 0-100, "reason": "texto"}}"""


FALLBACK_RESPONSE = {
    "approved": False,
    "confidence": 0,
    "reason": "Failed to parse validation response",
}
