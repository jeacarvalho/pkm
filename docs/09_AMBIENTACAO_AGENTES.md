# Contexto do Projeto: Obsidian RAG Connector

## Visao Geral

**Projeto:** Sistema RAG (Retrieval-Augmented Generation) para conectar livros (PDF) a um vault do Obsidian com 3000+ notas.

**Repositorio:** https://github.com/jeacarvalho/pkm

**Objetivo:** Processar livros PDF por capitulo, validar conexoes semanticas com notas do vault via Ollama, e gerar arquivos Markdown organizados no Obsidian.

---

## Status Atual das Sprints

| Sprint | Status | Descricao |
|--------|--------|-----------|
| Sprint 00 | ✅ COMPLETE | Documentacao base (5 arquivos MD) |
| Sprint 01 | ✅ COMPLETE | Vault Indexing (3570 notas → 10144 chunks no ChromaDB) |
| Sprint 02 | ✅ COMPLETE | PDF Ingestion (PyMuPDF + Gemini translation) |
| Sprint 03 | ✅ COMPLETE | Retrieval + Re-Ranker (Top-20 → Top-5) |
| Sprint 04 | ✅ COMPLETE | Ollama Validation (JSON estruturado, approved=true apenas) |
| Sprint 05 | ✅ COMPLETE | Output Generation (Markdown com frontmatter) |
| **Sprint 06** | ✅ COMPLETE | Chapter-Based Processing + Vault Integration |

---

## Sprint 06 (Implementado)

**Objetivo:** Mudar processamento de chunks (512 tokens) para **capitulos definidos manualmente** via arquivo `capitulos.txt`.

**Entrada:**
- PDF do livro
- `capitulos.txt` com formato: `pagina_inicio,pagina_fim` (uma linha por capitulo)

**Saida:**
- Pasta no vault: `/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros/{NOME_LIVRO}/`
- 1 arquivo MD por capitulo: `00_Capitulo_01.md`, `01_Capitulo_02.md`, etc.
- Cada capitulo tem Top 5 matches validados pelo Ollama

**Exemplo de `capitulos.txt`:**
```
1,15
16,32
33,48
49,65
```

---

## Arquivos Implementados (Sprint 06)

| Arquivo | Descricao |
|---------|-----------|
| `src/ingestion/chapter_parser.py` | Parser para arquivo capitulos.txt |
| `src/output/vault_writer.py` | Escrita de capitulos no vault |
| `src/utils/config.py` | Novas configuracoes (books_vault_path, chapter_validation_top_k) |
| `src/validation/pipeline.py` | Novo metodo process_chapter() |

---

## Como Usar (Sprint 06)

```bash
# Processar livro por capitulos
python3 -m src.ingestion.pdf_processor \
  --book "/caminho/livro.pdf" \
  --chapters "data/test/capitulos.txt" \
  --book-name "Nome_Livro" \
  --vault-path "/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros"
```

---

## Configuracoes

| Variavel | Valor Padrao | Descricao |
|----------|--------------|-----------|
| `books_vault_path` | `/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros` | Pasta para salvar livros processados |
| `chapter_validation_top_k` | 5 | Numero de matches validados por capitulo |
| `use_chapter_processing` | false | Modo de processamento por capitulo |

---

## Fluxo de Execucao

1. Parser ler `capitulos.txt` e validar intervalos de paginas
2. Extrair texto de cada capitulo via PyPDF2
3. Detectar idioma e traduzir se necessario (Gemini)
4. Validar capitulo contra vault via Ollama (top 5 matches)
5. Gerar arquivo MD por capitulo com frontmatter + conexoes
6. Salvar em pasta do livro no vault

---

## Testes

| Teste | Status |
|-------|--------|
| `tests/unit/test_chapter_processing.py` | ✅ Implementado |
| ChapterParser | ✅ Validacao de intervalos |
| VaultWriter | ✅ Escrita de capitulos |

---

## Referencias

- **Tag v1.0.0:** Baseline funcional completo
- **Tag v1.1.0:** Sprint 06 - Chapter-based processing
