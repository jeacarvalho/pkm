# 🚀 Contexto do Projeto: Obsidian RAG Connector

## 📌 Visão Geral

**Projeto:** Sistema RAG (Retrieval-Augmented Generation) para conectar livros (PDF) a um vault do Obsidian com 3000+ notas.

**Repositório:** https://github.com/jeacarvalho/pkm

**Objetivo:** Processar livros PDF por capítulo, validar conexões semânticas com notas do vault via Ollama, e gerar arquivos Markdown organizados no Obsidian.

---

## ✅ Status Atual das Sprints

| Sprint | Status | Descrição |
|--------|--------|-----------|
| Sprint 00 | ✅ COMPLETE | Documentação base (5 arquivos MD) |
| Sprint 01 | ✅ COMPLETE | Vault Indexing (3570 notas → 10144 chunks no ChromaDB) |
| Sprint 02 | ✅ COMPLETE | PDF Ingestion (PyMuPDF + Gemini translation) |
| Sprint 03 | ✅ COMPLETE | Retrieval + Re-Ranker (Top-20 → Top-5) |
| Sprint 04 | ✅ COMPLETE | Ollama Validation (JSON estruturado, approved=true apenas) |
| Sprint 05 | ✅ COMPLETE | Output Generation (Markdown com frontmatter) |
| **Sprint 06** | ⏭️ **EM ANDAMENTO** | **Chapter-Based Processing + Vault Integration** |

---

## 🎯 Sprint 06 (Tarefa Atual)

**Objetivo:** Mudar processamento de chunks (512 tokens) para **capítulos definidos manualmente** via arquivo `capitulos.txt`.

**Entrada:**
- PDF do livro
- `capitulos.txt` com formato: `pagina_inicio,pagina_fim` (uma linha por capítulo)

**Saída:**
- Pasta no vault: `/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros/{NOME_LIVRO}/`
- 1 arquivo MD por capítulo: `00_Capitulo_01.md`, `01_Capitulo_02.md`, etc.
- Cada capítulo tem Top 5 matches validados pelo Ollama

**Exemplo de `capitulos.txt`:**