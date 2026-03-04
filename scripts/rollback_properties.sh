#!/bin/bash
# Rollback Properties - Sprint 09
# Reverte mudanças no frontmatter via git

set -e

echo "🔄 Vault Properties Rollback"
echo "=============================="
echo ""

# Verifica se está em repositório git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Mostra status atual
echo "📊 Current git status:"
git status --short docs/ data/logs/topics/ 2>/dev/null || echo "  (no changes in docs/ or data/logs/topics/)"

# Lista commits recentes
echo ""
echo "📜 Recent commits:"
git log --oneline -5

# Pergunta confirmação
echo ""
read -p "⚠️ Rollback último commit? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled"
    exit 0
fi

# Executa rollback
echo ""
echo "🔄 Rolling back..."
git reset --hard HEAD~1

echo ""
echo "✅ Rollback complete"
echo "📊 Verify with: git status"
echo ""
echo "⚠️ Notas do vault NÃO foram revertidas (o vault está fora do git)"
echo "⚠️ Para reverter notas do vault, use o script restore_topics.py"
