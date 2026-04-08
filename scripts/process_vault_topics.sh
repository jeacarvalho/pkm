#!/bin/bash
# ============================================================
# Script para processar o vault e gerar topic_classification
# apenas para notas que ainda NÃO foram processadas
#
# Uso: ./scripts/process_vault_topics.sh
# ============================================================

set -e

export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm

VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="/home/s015533607/Documentos/desenv/pkm/data/logs/topics"

echo "============================================"
echo "  PROCESSAMENTO DO VAULT"
echo "  $(date)"
echo "============================================"
echo ""

# Processar apenas notas sem topic_classification
echo "📚 Processando notas sem classificação..."
echo "   (Notas já classificadas serão ignoradas)"
echo ""

python3 -m src.topics.daily_sync \
    --vault-dir "$VAULT_PATH" \
    --only-missing \
    2>&1 | tee "$LOG_DIR/daily_sync_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "============================================"
echo "  PROCESSAMENTO CONCLUÍDO!"
echo "  $(date)"
echo "============================================"
