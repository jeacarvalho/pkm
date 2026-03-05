#!/bin/bash
# Script para processar pasta 40 COMO CONHECEMOS com Topic Classification
# Versão completa (sem limite)

# Mudar para o diretório do projeto (onde está o .env)
cd "$(dirname "$0")/.."

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   TOPIC CLASSIFICATION - 70 ECONOMIA (Completo)   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Configurações
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
VAULT_DIR="/home/s015533607/MEGAsync/Minhas_notas"
TEST_DIR="70 ECONOMIA"

echo "📁 Pasta: $TEST_DIR"
echo "📂 Vault: $VAULT_DIR"
echo ""

# Contar notas
NOTE_COUNT=$(find "$VAULT_DIR/$TEST_DIR" -name "*.md" -not -path "*/.obsidian/*" | wc -l)
echo "📝 Total de notas encontradas: $NOTE_COUNT"
echo ""

# FASE 1: DRY-RUN (Obrigatório - teste sem modificar)
echo "════════════════════════════════════════════════════════════"
echo "🔍 FASE 1: DRY-RUN (Teste sem modificar notas)"
echo "════════════════════════════════════════════════════════════"
echo ""

python3 -m src.topics.topic_extractor \
    --test-dir "$TEST_DIR" \
    --dry-run

echo ""
echo "⚠️  Verifique acima se não há erros graves!"
echo ""
read -p "Deseja continuar com processamento REAL? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelado pelo usuário"
    exit 0
fi

# FASE 2: Processamento REAL
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 FASE 2: PROCESSAMENTO REAL (Modificará as notas!)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "⏱️  Tempo estimado: 5-10 minutos (76 notas × ~5-8s cada)"
echo "💰 Custo estimado: ~$0.01 USD (76 notas × ~100 tokens)"
echo ""
read -p "Pressione ENTER para começar..."

# Executar processamento real
python3 -m src.topics.topic_extractor \
    --test-dir "$TEST_DIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ PROCESSAMENTO CONCLUÍDO!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📊 Verifique os resultados:"
echo "   - Logs: data/logs/topics/writer.log"
echo "   - Notas modificadas: $VAULT_DIR/$TEST_DIR"
echo ""
echo "🔄 Para reverter alterações (se necessário):"
echo "   git checkout -- data/logs/topics/"
echo "   # E restaurar notas do backup"
echo ""
