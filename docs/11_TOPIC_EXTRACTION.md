# Topic Extraction - Guia de Uso

## Visão Geral

O módulo `src/topics/` extrai 10 tópicos principais + classificação CDU de cada nota do vault usando Gemini 2.5 Flash-Lite.

## Instalação

Não requer instalação adicional. O módulo usa as mesmas dependências do projeto.

## Configuração

Variáveis de ambiente no `.env`:

```bash
# Já configurado no .env
GEMINI_API_KEY=your_api_key_here
TOPICS_GEMINI_MODEL=gemini-2.5-flash-lite
TOPICS_LOG_DIR=data/logs/topics
```

## Uso

### 1. Teste com Dry-Run (recomendado primeiro)

```bash
cd /home/s015533607/Documentos/desenv/pkm
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.topics.topic_extractor --test-dir "30 LIDERANCA" --dry-run
```

**Saída esperada:**
```
🚀 Topic Extraction
   Target: /home/s015533607/MEGAsync/Minhas_notas/30 LIDERANCA
   Dry-run: True
   
Found 101 markdown files...
[1/101] Processing: empatia.md
  [DRY-RUN] Would extract topics from empatia.md
...
```

### 2. Extração em Subdiretório (teste piloto)

```bash
python3 -m src.topics.topic_extractor \
    --test-dir "30 LIDERANCA" \
    --output-dir data/logs/topics
```

**Processa apenas 101 notas** da pasta "30 LIDERANCA".

### 3. Extração do Vault Completo

```bash
python3 -m src.topics.topic_extractor \
    --output-dir data/logs/topics
```

**Processa todas as 3570 notas** (~$0.34 USD).

## Schema de Saída

Cada nota gera um JSON:

```json
{
  "topics": [
    {
      "name": "diferenca_planejado_executado",
      "weight": 10,
      "confidence": 0.98
    },
    ...
  ],
  "cdu_primary": "658.012",
  "cdu_secondary": ["305.8"],
  "cdu_description": "Gestão e organização",
  "metadata": {
    "file_path": "/path/to/note.md",
    "file_name": "note.md",
    "processed_at": "2026-03-04T...",
    "model": "gemini-2.5-flash-lite"
  }
}
```

## Campos

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `name` | string | snake_case, português |
| `weight` | int | 5-10 (importância) |
| `confidence` | float | 0.0-1.0 |
| `cdu_primary` | string | CDU primária (ex: "321.1") |
| `cdu_secondary` | array | CDUs secundárias |

## Validação

O sistema valida automaticamente:
- ✅ Exatamente 10 tópicos
- ✅ Pesos entre 5-10
- ✅ Confidence entre 0.0-1.0
- ✅ Nomes em snake_case (acentos são removidos automaticamente)
- ✅ Formatos CDU válidos (aceita múltiplos níveis: 330.341.5)
- ✅ JSON estrito (sem markdown)
- ✅ Notas curtas processadas como "index notes"

Se a validação falhar, o Gemini tenta novamente (até 3x).

## Notas Curtas (< 50 caracteres)

Notas com pouco conteúdo são processadas como **index notes**:
- ✅ Extrai tópicos do **nome do arquivo**
- ✅ Inferiu CDU da **pasta**
- ✅ Não chama API Gemini (economiza tokens)
- ✅ Marca como `is_index_note: true`
- ✅ Model: `local-inference`

**Exemplo:**
```json
{
  "topics": [{"name": "pib", "weight": 8, "confidence": 0.85}],
  "cdu_primary": "330",
  "cdu_description": "Economia",
  "metadata": {
    "is_index_note": true,
    "model": "local-inference"
  }
}
```

## Normalização Automática

### Acentos em Nomes de Tópicos
Nomes com acentos são normalizados automaticamente:
- `estabilidade_macroeconômica` → `estabilidade_macroeconomica`
- `governança_situacional` → `governanca_situacional`

### CDU Multi-Nível
CDUs profundas são preservadas:
- `330.341.5` → válido (3 níveis)
- `1.23.456.7890` → válido (4 níveis)
- `32` → normalizado para `32.0`

## Custo

| Cenário | Notas | Custo Aproximado |
|---------|-------|------------------|
| Teste Piloto | 100 | ~$0.01 USD |
| Vault Completo | 3570 | ~$0.34 USD |

**Gemini 2.5 Flash-Lite:**
- Input: $0.075 / 1M tokens
- Output: $0.30 / 1M tokens

## Logs

Logs são salvos em `data/logs/topics/`:

- `topic_extraction_YYYYMMDD_HHMMSS.json` - Resultados
- `extraction.log` - Log detalhado
- `errors.log` - Erros de API

## Troubleshooting

### Erro: "GEMINI_API_KEY not configured"
```bash
# Verifique se .env tem a chave
cat .env | grep GEMINI
```

### Erro: "Validation error: weight X not in range"
O Gemini às vezes retorna pesos inválidos. O sistema tenta 3x automaticamente.

### Erro: "JSON decode error"
O Gemini retornou texto em vez de JSON. O sistema tenta novamente.

## Exemplo de Uso em Python

```python
from src.topics.topic_extractor import TopicExtractor
from src.topics.config import TopicsConfig

# Inicializar
config = TopicsConfig()
extractor = TopicExtractor(config)

# Extrair de uma nota
from pathlib import Path
result, error = extractor.process_note(Path('/path/to/note.md'))

if not error:
    print(f"CDU: {result['cdu_primary']}")
    for topic in result['topics']:
        print(f"  - {topic['name']} (weight: {topic['weight']})")
```

## Testes

Execute o script de teste:

```bash
bash scripts/test_topic_extractor.sh
```

Ou teste manualmente:

```bash
# Testar uma nota específica
python3 -c "
from pathlib import Path
from src.topics.topic_extractor import TopicExtractor

extractor = TopicExtractor()
result, error = extractor.process_note(
    Path('/home/s015533607/MEGAsync/Minhas_notas/30 LIDERANCA/Lacuna de alinhamento.md')
)

if not error:
    print(f'Topicos: {len(result[\"topics\"])}')
    print(f'CDU: {result[\"cdu_primary\"]}')
"
```

## Limitações

1. **1 nota por vez:** Batch size fixo em 1 para evitar rate limit
2. **Rate limit:** Pequeno delay (0.5s) entre chamadas
3. **Notas curtas:** Ignoradas se < 50 caracteres
4. **Tamanho máximo:** Notas truncadas em 5000 caracteres

## Troubleshooting

### Problema: "No topic JSON found" ao rodar vault_writer

**Causa:** O vault_writer não consegue encontrar os JSONs de extração.

**Solução:**
1. Verificar se o JSON existe: `ls -la data/logs/topics/topic_extraction_*.json`
2. Verificar se o campo "file" tem o path correto (precisa ter path completo do vault)
3. Rodar vault_writer novamente:
   ```bash
   python3 -m src.topics.vault_writer --vault-dir /home/s015533607/MEGAsync/Minhas_notas
   ```

### Problema: Matches não aparecem no capítulo

**Causa 1:** Threshold muito alto
- Verificar `src/ingestion/pdf_processor.py` - threshold deve ser 0.0

**Causa 2:** Fuzzy threshold muito alto
- Verificar `src/topics/topic_matcher.py` - fuzzy_threshold deve ser 40

**Causa 3:** Vault não tem notas relevantes
- O sistema só encontra matches se houver notas com topic_classification sobre tema similar
- Para testar: verificar quantas notas têm topic_classification
- Executar topic_extractor em mais notas do vault

---

## Próximos Passos

Ver `docs/10_ROADMAP_v2.md` para:
- Sprint 08: Vault Properties Writer
- Sprint 09: Topic Matching Engine
- Sprint 10: Translation Cache

---

**Última atualização:** 2026-03-05
**Versão:** 1.3.1
