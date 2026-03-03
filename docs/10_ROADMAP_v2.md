# 🚀 Roadmap v2.0 - Topic Classification & Taxonomy System

**Created:** 2026-03-03  
**Version:** 2.0.0 (planned)  
**Status:** 📋 PLANNING  
**Baseline:** v1.1.0 (Sprints 01-06 COMPLETE)

---

## 🎯 Objetivo da v2.0

Evoluir o sistema RAG de **embedding-based** para **topic-based classification** com:

1. **Classificação de Tópicos via Gemini** (cloud, não Ollama local)
2. **Properties no Frontmatter** de cada nota do vault
3. **Matching por Sobreposição de Tópicos** (não apenas embedding)
4. **Cache de Tradução** (evitar retraduções de capítulos)
5. **Integração com Dataview/Bases** do Obsidian

---

## 📊 Comparação: v1.0 vs v2.0

| Aspecto | v1.0 (Atual) | v2.0 (Planejado) |
|---------|--------------|------------------|
| **Retrieval** | Embedding (bge-m3) | Topics + Embedding (híbrido) |
| **Validação** | Ollama local (llama3.2) | Gemini 2.5 Flash-Lite |
| **Matching** | Similaridade vetorial | Sobreposição de tópicos + pesos |
| **Cache** | ChromaDB apenas | Properties no vault + ChromaDB |
| **Tradução** | Sempre via Gemini | Cache-first (não retraduzir) |
| **Output** | 1 arquivo por livro | 1 pasta + 1 arquivo/capítulo |
| **Dataview** | Limitado | Full integration (properties) |
| **Custo API** | ~$0.05/livro | ~$0.03/livro (com cache) |

---

## 📋 Sprint Roadmap v2.0

| Sprint | Descrição | Dependência | Tempo Est. | Status |
|--------|-----------|-------------|------------|--------|
| **Sprint 07** | Topic Extractor (Gemini) | Sprint 06 | 4-6 horas | ⏭️ READY |
| **Sprint 08** | Vault Properties Writer | Sprint 07 | 3-4 horas | ⏭️ BLOCKED |
| **Sprint 09** | Topic Matching Engine | Sprint 08 | 4-6 horas | ⏭️ BLOCKED |
| **Sprint 10** | Translation Cache System | Sprint 07 | 2-3 horas | ⏭️ BLOCKED |
| **Sprint 11** | Hybrid Retrieval (v1+v2) | Sprint 09+10 | 4-6 horas | ⏭️ BLOCKED |
| **Sprint 12** | Dataview Integration | Sprint 08 | 2-3 horas | ⏭️ BLOCKED |

**Total Estimado:** ~18-25 horas de desenvolvimento

---

## 🏗️ Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: CLASSIFICAÇÃO INICIAL                │
│  3570 notas do vault → Gemini 2.5 Flash-Lite                    │
│  Prompt: "Extraia 10 tópicos principais com peso 5-10"          │
│  Output: Properties no frontmatter de cada nota                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: PROCESSAMENTO DE CAPÍTULO             │
│  1. Capítulo do livro → Gemini (extrai 10 tópicos + pesos)      │
│  2. Loop sobre 3570 notas (local, rápido)                       │
│     - Calcular similaridade de tópicos (nome + peso)            │
│     - Top-20 notas com mais assuntos similares                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: VALIDAÇÃO FINAL                      │
│  Top-10 notas → Gemini com capítulo                             │
│  Prompt: "Estas notas são semanticamente relacionadas?"         │
│  Output: Matches aprovados (approved=true)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Sprint 07: Topic Extractor (Gemini)

### Objetivo
Extrair 10 tópicos principais de cada nota do vault com pesos (5-10).

### Input/Output
```yaml
# Input
note_content: str (conteúdo completo da nota)

# Output
topics:
  - name: colonialidade_do_poder
    weight: 10
    confidence: 0.95
  - name: eurocentrismo
    weight: 8
    confidence: 0.89
  # ... até 10 tópicos
```

### Arquivos
```
src/
└── topics/
    ├── __init__.py
    ├── topic_extractor.py      # Gemini call
    ├── topic_validator.py      # Validate topic consistency
    └── taxonomy_manager.py     # CDD/CDU integration (opcional)
```

### Critérios de Aceite
- [ ] Gemini 2.5 Flash-Lite configurado (não 2.0)
- [ ] Retorna exatamente 10 tópicos por nota
- [ ] Pesos entre 5-10 (inteiro)
- [ ] Confidence entre 0.0-1.0 (float)
- [ ] Tópicos em português (snake_case)
- [ ] Teste com 100 notas primeiro (não vault completo)

### Prompt Gemini (Template)
```
Você é um curador de conhecimento pessoal.
Extraia os 10 tópicos principais desta nota.

REGRAS:
1. Retorne APENAS JSON válido
2. Cada tópico: name (str), weight (5-10), confidence (0.0-1.0)
3. Tópicos em português, snake_case
4. Seja específico (evite tópicos genéricos como "filosofia")

CONTEÚDO DA NOTA:
{note_content[:5000]}

Responda em JSON:
{"topics": [{"name": "...", "weight": 10, "confidence": 0.95}, ...]}
```

### Custo Estimado
```
3570 notas × ~500 tokens/nota = ~1.785M tokens (input)
3570 notas × ~200 tokens/nota = ~714K tokens (output)

Gemini 2.5 Flash-Lite Pricing:
- Input: $0.075 / 1M tokens
- Output: $0.30 / 1M tokens

Custo Total:
- Input: 1.785 × $0.075 = $0.13
- Output: 0.714 × $0.30 = $0.21
- TOTAL: ~$0.34 USD (uma única vez!)
```

---

## 📝 Sprint 08: Vault Properties Writer

### Objetivo
Escrever tópicos no frontmatter das notas do vault.

### Estrutura de Properties
```yaml
---
# Existing
title: Colonialidade do Poder
tags:
  - #poder
  - #colonialismo

# NEW v2.0
topic_classification:
  version: 2.0
  classified_at: 2026-03-03T23:59:00Z
  model: gemini-2.5-flash-lite
  topics:
    - name: colonialidade_do_poder
      weight: 10
      confidence: 0.95
    - name: eurocentrismo
      weight: 8
      confidence: 0.89
  cdd_primary: 320.1  # Opcional: classificação CDD/CDU
  cdd_secondary:
    - 305.8
    - 128.3
---
```

### Arquivos
```
src/
└── topics/
    └── vault_writer.py         # Write properties to vault
```

### Critérios de Aceite
- [ ] Properties no frontmatter YAML
- [ ] Não sobrescrever conteúdo existente da nota
- [ ] Backup antes de modificar notas
- [ ] Log de notas modificadas
- [ ] Reversível (script de rollback)

---

## 📝 Sprint 09: Topic Matching Engine

### Objetivo
Match entre tópicos do capítulo e tópicos das notas do vault.

### Algoritmo
```python
def match_topics(chapter_topics, vault_note_topics):
    """
    chapter_topics: [{"name": "...", "weight": 10}, ...]
    vault_note_topics: [{"name": "...", "weight": 8}, ...]
    """
    score = 0
    matched = []
    
    for ch_topic in chapter_topics:
        for vt_topic in vault_note_topics:
            # Fuzzy match de nomes
            if fuzzy_match(ch_topic["name"], vt_topic["name"]):
                score += min(ch_topic["weight"], vt_topic["weight"])
                matched.append({
                    "chapter_topic": ch_topic["name"],
                    "vault_topic": vt_topic["name"],
                    "score": min(ch_topic["weight"], vt_topic["weight"])
                })
    
    # Normalizar score (0-100)
    max_possible = sum(t["weight"] for t in chapter_topics)
    normalized_score = (score / max_possible) * 100
    
    return {
        "score": normalized_score,
        "matched_topics": matched,
        "total_chapter_topics": len(chapter_topics),
        "total_matched": len(matched)
    }
```

### Arquivos
```
src/
└── topics/
    └── topic_matcher.py        # Matching algorithm
```

### Critérios de Aceite
- [ ] Fuzzy match para tópicos similares (colonialismo ≈ colonialidade)
- [ ] Score normalizado 0-100
- [ ] Top-20 notas por similaridade de tópicos
- [ ] Log de matches para debugging

---

## 📝 Sprint 10: Translation Cache System

### Objetivo
Não retraduzir capítulos já processados.

### Fluxo
```
1. Verificar se capítulo existe no vault
2. SE existir → Carregar conteúdo traduzido do MD
3. SE não existir → Traduzir via Gemini + Salvar no vault
```

### Arquivos
```
src/
└── topics/
    └── translation_cache.py    # Cache logic
```

### Critérios de Aceite
- [ ] Verificar existência do arquivo MD antes de traduzir
- [ ] Extrair conteúdo de `## Conteúdo Traduzido` seção
- [ ] Flag `--force-retranslate` para pular cache
- [ ] Log: "✅ Using cached translation" ou "🔄 Translating..."

---

## 📝 Sprint 11: Hybrid Retrieval (v1 + v2)

### Objetivo
Permitir uso de embedding (v1) + topics (v2) simultaneamente.

### Fluxo
```
┌─────────────────────────────────────────────────────────────┐
│  Retrieval Híbrido (Embedding + Topics)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Topic Matching → Top-50 notas (rápido, preciso)       │
│  2. Embedding Search → Top-50 notas (semântico, complementar)│
│  3. Merge + Re-Rank → Top-20 candidatos                    │
│  4. Gemini Validation → Top-5 matches finais                │
└─────────────────────────────────────────────────────────────┘
```

### Arquivos
```
src/
└── retrieval/
    └── hybrid_pipeline.py      # v1 + v2 orchestration
```

### Critérios de Aceite
- [ ] Config flag: `--retrieval-mode topics|embedding|hybrid`
- [ ] Default: `hybrid` (melhor dos dois mundos)
- [ ] Fallback para embedding se topics não disponíveis
- [ ] Performance: < 5s por capítulo

---

## 📝 Sprint 12: Dataview Integration

### Objetivo
Habilitar queries Dataview/Bases com properties dos tópicos.

### Exemplo de Query Dataview
```dataview
TABLE file.name, topic_classification.topics
FROM #book-connections
WHERE contains(topic_classification.topics.name, "colonialidade")
SORT topic_classification.classified_at DESC
```

### Arquivos
```
docs/
└── templates/
    └── dataview_queries.md     # Exemplos de queries
```

### Critérios de Aceite
- [ ] Properties formatadas para Dataview
- [ ] Template de queries no vault
- [ ] Documentação de uso

---

## ⚠️ Riscos e Mitigações

| Risco | Impacto | Mitigação | Status |
|-------|---------|-----------|--------|
| Topics inconsistentes (nomes diferentes) | Alto | Fuzzy matching + taxonomy manager | 📋 Planejado |
| Gemini API rate limit | Médio | Batch processing + backoff | 📋 Planejado |
| Properties corrompem notas | Alto | Backup antes de escrever + rollback | 📋 Planejado |
| Performance lenta (muitas chamadas Gemini) | Médio | Cache de topics + parallel processing | 📋 Planejado |
| v1.0 para de funcionar | Crítico | Manter v1.0 funcional + hybrid mode | 📋 Planejado |

---

## ✅ Critérios de Aceite Gerais (v2.0)

- [ ] **Nenhuma alucinação**: Agente pergunta antes de assumir
- [ ] **Documentação atualizada**: `docs/` reflete status real
- [ ] **Testes end-to-end**: 1 nota processada completa antes de vault
- [ ] **Backup automático**: Antes de mudanças estruturais
- [ ] **Rollback possível**: Script para reverter mudanças
- [ ] **v1.0 preservado**: Embedding pipeline continua funcional
- [ ] **Hybrid mode**: Pode usar v1+v2 simultaneamente

---

## 📊 Timeline Estimada

```
Week 1 (Days 1-5)
├── Sprint 07: Topic Extractor
├── Sprint 08: Vault Properties Writer
└── Status: Topic classification ready

Week 2 (Days 6-10)
├── Sprint 09: Topic Matching Engine
├── Sprint 10: Translation Cache System
└── Status: Matching + Cache ready

Week 3 (Days 11-15)
├── Sprint 11: Hybrid Retrieval
├── Sprint 12: Dataview Integration
└── Status: ALL SPRINTS COMPLETE ✅

Total Project Time: ~3 weeks (15 working days)
```

---

## 📚 Referências

| Documento | Descrição |
|-----------|-----------|
| `docs/02_CURRENT_STATUS.md` | Status atual do projeto (v1.0) |
| `docs/08_SPRINT_DEPENDENCIES.md` | Dependências entre sprints |
| `docs/03_CODING_STANDARDS.md` | Padrões de código |
| `docs/04_DATA_DICTIONARY.md` | Schema de dados (atualizar para v2.0) |
| `docs/RECOVERY.md` | Procedimentos de recovery |

---

## 🏷️ Versionamento

| Tag | Data | Descrição |
|-----|------|-----------|
| v1.0.0 | 2026-03-01 | Baseline funcional completo |
| v1.1.0 | 2026-03-03 | Sprint 06 - Chapter-based processing |
| v2.0.0 | TBD | Topic Classification System |

---

**Última Atualização:** 2026-03-03  
**Próxima Revisão:** Após Sprint 07 complete
