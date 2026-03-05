#!/bin/bash
# Script para processar pasta com Topic Classification
# 1. Extrai tópicos (topic_extractor)
# 2. Grava no frontmatter (vault_writer)

cd "$(dirname "$0")/.."

echo "╔════════════════════════════════════════════════════════════╗"
echo "║ TOPIC CLASSIFICATION - COMPLETO ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
VAULT_DIR="/home/s015533607/MEGAsync/Minhas_notas"
TEST_DIR="40 COMO CONHECEMOS"

echo "📁 Pasta: $TEST_DIR"
echo "📂 Vault: $VAULT_DIR"
echo ""

NOTE_COUNT=$(find "$VAULT_DIR/$TEST_DIR" -name "*.md" -not -path "*/.obsidian/*" | wc -l)
echo "📝 Total de notas encontradas: $NOTE_COUNT"
echo ""

# FASE 1: EXTRAÇÃO (Dry-run)
echo "════════════════════════════════════════════════════════════"
echo "🔍 FASE 1: EXTRAÇÃO DE TÓPICOS (Dry-run)"
echo "══════════════════════════════════════════════════════"
echo ""

python3 -m src.topics.topic_extractor \
    --test-dir "$TEST_DIR" \
    --dry-run

echo ""
echo "⚠️ Verifique acima se não há erros graves!"
echo ""
read -p "Deseja continuar com EXTRAÇÃO REAL? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelado pelo usuário"
    exit 0
fi

# FASE 2: EXTRAÇÃO REAL
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 FASE 2: EXTRAÇÃO REAL (Chamará API Gemini)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "⏱️ Tempo estimado: 5-10 minutos"
echo "💰 Custo estimado: ~$0.02 USD"
echo ""
read -p "Pressione ENTER para começar..." 

python3 -m src.topics.topic_extractor \
    --test-dir "$TEST_DIR"

echo ""
echo "✅ Extração concluída!"
echo ""

# FASE 3: ESCRITA NO VAULT (Dry-run)
echo "════════════════════════════════════════════════════════════"
echo "🔍 FASE 3: ESCRITA NO FRONTMATTER (Dry-run)"
echo "════════════════════════════════════════════════════════════"
echo ""

python3 -m src.topics.vault_writer \
    --vault-dir "$VAULT_DIR/$TEST_DIR" \
    --dry-run

echo ""
echo "⚠️ Verifique as alterações acima antes de confirmar!"
echo ""
read -p "Deseja aplicar as alterações no vault? (yes/no): " confirm2

if [ "$confirm2" != "yes" ]; then
    echo "❌ Cancelado pelo usuário"
    exit 0
fi

# FASE 4: ESCRITA REAL
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 FASE 4: ESCRITA REAL (Modificará as notas!)"
echo "════════════════════════════════════════════════════════════"
echo ""

python3 -m src.topics.vault_writer \
    --vault-dir "$VAULT_DIR/$TEST_DIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ PROCESSAMENTO COMPLETO CONCLUÍDO!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📊 Resultados:"
echo " - Logs: data/logs/topics/writer.log"
echo " - Notas modificadas: $VAULT_DIR/$TEST_DIR"
echo ""