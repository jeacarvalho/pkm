#!/bin/bash
# ============================================================
# Script para processar TODO o vault e gerar topic_classification
# no frontmatter de todas as notas que ainda não foram processadas
#
# Uso: ./scripts/process_vault_topics.sh
# ============================================================

set -e

export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm

VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="/home/s015533607/Documentos/desenv/pkm/data/logs/topics"

echo "============================================"
echo "  PROCESSAMENTO COMPLETO DO VAULT"
echo "  $(date)"
echo "============================================"
echo ""

# Passo 1: Extrair tópicos de todas as notas
echo "📚 PASSO 1: Extraindo tópicos via Gemini..."
echo "   (Isso pode levar várias horas para o vault inteiro)"
echo ""

python3 -m src.topics.topic_extractor \
    --output-dir "$LOG_DIR" \
    2>&1 | tee "$LOG_DIR/extraction_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "✅ Extração concluída!"
echo ""

# Passo 2: Gravar topics no frontmatter das notas
echo "✍️  PASSO 2: Gravando topics no frontmatter..."
echo ""

python3 -m src.topics.vault_writer \
    --vault-dir "$VAULT_PATH" \
    2>&1 | tee "$LOG_DIR/writer_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "============================================"
echo "  PROCESSAMENTO CONCLUÍDO!"
echo "  $(date)"
echo "============================================"
