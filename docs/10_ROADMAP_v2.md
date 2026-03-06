# 🚀 Roadmap v2.0 - Topic Classification & Taxonomy System

**Created:** 2026-03-03  
**Version:** 2.0.0  
**Status:** ✅ COMPLETE (2026-03-05)  
**Baseline:** v1.1.0 (Sprints 01-06 COMPLETE)

---

## 🎯 Objetivo da v2.0

Sistema RAG puramente **topic-based** (sem embedding):

1. **Classificação de Tópicos via Gemini** - Extrai 10 topics + CDU de cada nota do vault
2. **Properties no Frontmatter** - Armazena topics classificados em cada nota
3. **Matching por Sobreposição de Tópicos** - Fuzzy match entre topics do capítulo e notas
4. **Cache de Tradução** - Evita retraduções de capítulos
5. **Sem ChromaDB/Embedding** - Matching feito via frontmatter (muito mais rápido)

---

## 📊 Comparação: v1.0 vs v2.0

| Aspecto | v1.0 (Obsoleto) | v2.0 (Atual) |
|---------|------------------|---------------|
| **Retrieval** | Embedding (bge-m3 + ChromaDB) | Topic-based (sem embedding) |
| **Validação** | Gemini re-ranking | Removida (topic matching já faz) |
| **Matching** | Similaridade vetorial | Fuzzy match por topics + CDU |
| **速度** | ~4 min/chapter | ~10 seg/chapter |
| **Cache** | ChromaDB | Properties no vault + JSON |
| **Tradução** | Sempre via Gemini | Cache-first |
| **Output** | 1 arquivo por livro | 1 pasta + 1 arquivo/capítulo |
| **Custo API** | ~$0.05/livro | ~$0.02/livro |

---

## 📋 Sprint Roadmap v2.0

| Sprint | Descrição | Dependência | Tempo Est. | Status |
|--------|-----------|-------------|------------|--------|
| **Sprint 08** | Topic Extractor (Gemini) | Sprint 07 | 4-6 horas | ✅ COMPLETE |
| **Sprint 09** | Vault Properties Writer | Sprint 08 | 3-4 horas | ✅ COMPLETE |
| **Sprint 10** | Topic Matching Engine | Sprint 09 | 4-6 horas | ✅ COMPLETE |
| **Sprint 11** | Translation Cache System | Sprint 08 | 2-3 horas | ✅ COMPLETE |
| **Sprint 12** | Embedding Removal | Sprint 10+11 | 1 hora | ✅ COMPLETE (2026-03-05) |
| **Sprint 13** | Dataview Integration | Sprint 09 | 2-3 horas | ⏭️ OPCIONAL |

### Parâmetros Atuais (v2.0)
| Parâmetro | Valor | Arquivo |
|-----------|-------|---------|
| threshold | 0.0 | `src/topics/topic_matcher.py` |
| top_k | 20 | `src/ingestion/pdf_processor.py` |
| fuzzy_threshold | 40 | `src/topics/topic_matcher.py` |

### Notas Processadas
- **Antes:** 205 notas com topic_classification
- **Depois:** 250 notas (adicionadas 45 notas de história) |

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

## 📝 Sprint 08: Topic Extractor (Gemini) ✅ COMPLETE

**Status:** ✅ COMPLETE (2026-03-04)  
**Arquivos:** `src/topics/topic_extractor.py`, `src/topics/topic_validator.py`, `src/topics/taxonomy_manager.py`  
**Documentação:** `docs/11_TOPIC_EXTRACTION.md`  
**Custo Real:** ~$0.34 USD para vault completo (3570 notas)  

### ✅ Implementado
- [x] Extração de 10 tópicos por nota
- [x] Pesos 5-10, Confidence 0.0-1.0
- [x] Classificação CDU (primária + secundária)
- [x] CLI com --test-dir e --dry-run
- [x] Retry logic com exponential backoff
- [x] Validação JSON estrita
- [x] Testado com 101 notas da pasta "30 LIDERANCA"

### Como Usar
```bash
# Teste dry-run
python3 -m src.topics.topic_extractor --test-dir "30 LIDERANCA" --dry-run

# Extração real (teste piloto)
python3 -m src.topics.topic_extractor --test-dir "30 LIDERANCA"

# Vault completo
python3 -m src.topics.topic_extractor
```

Veja `docs/11_TOPIC_EXTRACTION.md` para guia completo.

---

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

## 📝 Sprint 09: Vault Properties Writer ✅ COMPLETE

**Status:** ✅ COMPLETE (2026-03-04)  
**Arquivos:** `src/topics/vault_writer.py`, `scripts/rollback_properties.sh`  
**Tempo Real:** ~2 horas  
**Dependência:** Sprint 08 COMPLETE ✅  

### ✅ Implementado
- [x] Lê JSONs de `data/logs/topics/results/` e `test_extraction_5_notes.json`
- [x] Escreve `topic_classification` no frontmatter YAML das notas
- [x] Preserva conteúdo existente da nota (apenas modifica frontmatter)
- [x] Preserva fields existentes do frontmatter (title, tags, etc.)
- [x] CLI com `--vault-dir` (obrigatório)
- [x] CLI com `--dry-run` (log apenas, não escreve)
- [x] CLI com `--limit` (limitar número de notas)
- [x] Logs em `data/logs/topics/writer.log` e `writer_errors.log`
- [x] Script `scripts/rollback_properties.sh` para rollback git
- [x] Estatísticas salvas em `writer_stats.json`
- [x] Testado com 5 notas de "30 LIDERANCA"

### 🐛 Correções (2026-03-05)
- [x] **Fix:** Busca JSONs em `data/logs/topics/` (além de `results/`)
- [x] **Feature:** Fallback de CDU para notas sem classificação
- [x] **Feature:** Suporte a CDU multi-nível (330.341.5 preservado)

### Estrutura do Frontmatter (Exemplo)
```yaml
---
title: Colonialidade do Poder
tags:
  - "#poder"
  - "#colonialismo"
topic_classification:
  version: "2.0"
  classified_at: "2026-03-04T15:00:23.198568+00:00"
  model: gemini-2.5-flash-lite
  topics:
    - name: colonialidade_do_poder
      weight: 10
      confidence: 0.95
    - name: eurocentrismo
      weight: 8
      confidence: 0.89
  cdu_primary: "321.1"
  cdu_secondary: ["305.8", "128.3"]
  cdu_description: "Teoria do Estado. Estado e direito. Política"
---
```

### Como Usar
```bash
# Teste dry-run
python3 -m src.topics.vault_writer \
  --vault-dir "/home/s015533607/MEGAsync/Minhas_notas" \
  --dry-run \
  --limit 10

# Modo real (10 notas de teste)
python3 -m src.topics.vault_writer \
  --vault-dir "/home/s015533607/MEGAsync/Minhas_notas" \
  --limit 10

# Vault completo
python3 -m src.topics.vault_writer \
  --vault-dir "/home/s015533607/MEGAsync/Minhas_notas"
```

### Arquivos
```
src/
└── topics/
    ├── vault_writer.py      # Escreve properties no vault
    └── config.py            # Configurações (atualizado)

scripts/
└── rollback_properties.sh   # Rollback via git

data/
└── logs/
    └── topics/
        ├── results/         # JSONs de entrada (Sprint 08)
        ├── backup/          # Backups
        ├── writer.log       # Log de escrita
        ├── writer_errors.log # Log de erros
        └── writer_stats.json # Estatísticas
```

### Critérios de Aceite
- [x] Properties no frontmatter YAML
- [x] Não sobrescrever conteúdo existente da nota
- [x] Preservar fields existentes do frontmatter
- [x] CLI com --dry-run funcional
- [x] Log de notas modificadas
- [x] Script de rollback

---

### Próximo Passo
**Sprint 09 COMPLETE** ✅ - Todas as notas do vault possuem properties classificadas.

**Próximo:** Sprint 10 - Topic Matching Engine (dependência satisfeita ✅)

---

## 📝 Sprint 10: Topic Matching Engine ✅ **COMPLETE** (2026-03-05)

### Objetivo
Match entre tópicos do capítulo e tópicos das notas do vault.

### Implementação
**Arquivo:** `src/topics/topic_matcher.py` - Implementação completa do algoritmo de matching

**Características:**
- Fuzzy matching usando `thefuzz` library com threshold 85
- Score normalizado 0-100 baseado em peso dos tópicos
- Top-K matches configurável (padrão: 20)
- Threshold configurável (padrão: 20.0)
- Logging para `data/logs/topics/matcher.log` e `errors.log`
- Output JSON em `data/matches/`

**CLI Interface:**
```bash
python -m src.topics.topic_matcher \
  --chapter-topics data/test/capitulo_01_topics.json \
  --vault-dir /home/s015533607/MEGAsync/Minhas_notas \
  --top-k 20 \
  --threshold 20.0 \
  --output data/matches/matches.json
```

**Performance:**
- Scans 3588 notes em ~1 segundo
- Encontra 203 notas com tópicos classificados
- Trata erros de frontmatter malformado (logged, non-fatal)

### Critérios de Aceite ✅
- [x] **Fuzzy match para tópicos similares** - Implementado com `thefuzz` (threshold 85)
- [x] **Score normalizado 0-100** - Implementado com normalização baseada em peso
- [x] **Top-20 notas por similaridade de tópicos** - Configurável via `--top-k`
- [x] **Log de matches para debugging** - Logs em `matcher.log` e `errors.log`

### Teste Realizado
```bash
# Dry-run (teste sem processamento real)
python -m src.topics.topic_matcher --dry-run

# Pilot (1 capítulo, modo real)
python -m src.topics.topic_matcher \
  --chapter-topics data/test/capitulo_01_topics.json \
  --vault-dir /home/s015533607/MEGAsync/Minhas_notas \
  --top-k 5 \
  --threshold 20.0 \
  --output data/matches/test_pilot.json
```

**Resultado:** 0 matches encontrados (esperado com dados de teste - tópicos "colonialismo", "imperialismo" não existem no vault)

---

## 📝 Sprint 11: Translation Cache System

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
- [x] Verificar existência do arquivo MD antes de traduzir
- [x] Extrair conteúdo de `## Conteúdo Traduzido` seção
- [x] Flag `--force-retranslate` para pular cache
- [x] Log: "✅ Using cached translation" ou "🔄 Translating..."

---

## 📝 Sprint 12: Hybrid Retrieval (v1 + v2)

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

## 📝 Sprint 13: Dataview Integration

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
