# Configuração do Cron Job para Daily Sync v2.1

## Visão Geral
Este documento descreve como configurar o cron job para execução automática do sistema de sincronização diária de tópicos.

## Scripts Criados

### 1. `production_daily_sync.sh`
Script principal de produção que:
- Executa o Daily Sync v2.1 com `force_all=True`
- Processa notas novas e modificadas
- Faz operações git no vault (add, commit, push)
- Gerencia logs e notificações
- Limpa logs antigos

### 2. `cron_daily_sync_production.sh`
Script wrapper para cron job que:
- Configura ambiente de execução
- Redireciona logs para arquivo
- Executa o script principal
- Limpa logs antigos (7 dias)

## Configuração do Cron Job

### Método 1: Configuração Manual (Recomendado)

1. **Abra o crontab:**
   ```bash
   crontab -e
   ```

2. **Adicione a linha abaixo (executa às 2:00 AM todos os dias):**
   ```bash
   # Daily Sync v2.1 - Topic Classification
   0 2 * * * /bin/bash /home/s015533607/Documentos/desenv/pkm/scripts/cron_daily_sync_production.sh
   ```

3. **Para execução a cada hora (teste):**
   ```bash
   # Executa a cada hora (para testes)
   0 * * * * /bin/bash /home/s015533607/Documentos/desenv/pkm/scripts/cron_daily_sync_production.sh
   ```

### Método 2: Usando Script de Configuração

Execute o script de configuração:
```bash
cd /home/s015533607/Documentos/desenv/pkm
./scripts/setup_cron.sh
```

## Verificação da Configuração

1. **Verifique o crontab atual:**
   ```bash
   crontab -l
   ```

2. **Verifique logs do cron:**
   ```bash
   # Logs do sistema
   tail -f /var/log/syslog | grep CRON
   
   # Logs da aplicação
   tail -f /home/s015533607/Documentos/desenv/pkm/data/logs/cron/cron_*.log
   ```

## Teste Manual

Antes de configurar o cron, teste manualmente:

1. **Teste o script principal:**
   ```bash
   cd /home/s015533607/Documentos/desenv/pkm
   ./scripts/production_daily_sync.sh
   ```

2. **Teste o script do cron:**
   ```bash
   cd /home/s015533607/Documentos/desenv/pkm
   ./scripts/cron_daily_sync_production.sh
   ```

## Estrutura de Logs

```
data/logs/
├── production/
│   ├── daily_sync_YYYYMMDD_HHMMSS.log  # Logs principais
│   └── failures_YYYYMMDD_HHMMSS.log    # Logs de falhas
└── cron/
    └── cron_YYYYMMDD_HHMMSS.log        # Logs do cron job
```

**Retenção de logs:**
- Logs de produção: 30 dias
- Logs do cron: 7 dias

## Monitoramento

### 1. Status do Último Run
```bash
# Verifique o último log
ls -la /home/s015533607/Documentos/desenv/pkm/data/logs/production/
tail -50 /home/s015533607/Documentos/desenv/pkm/data/logs/production/daily_sync_*.log
```

### 2. Verificação Git
```bash
cd /home/s015533607/MEGAsync/Minhas_notas
git log --oneline -5
```

### 3. Status do Vault
```bash
cd /home/s015533607/Documentos/desenv/pkm
export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -c "
import os
from pathlib import Path
import sys
sys.path.insert(0, '/home/s015533607/Documentos/desenv/pkm')
from src.topics.daily_sync import DailySync
from src.topics.config import topics_config

daily_sync = DailySync(topics_config)
vault_path = Path('/home/s015533607/MEGAsync/Minhas_notas')

new_notes, modified_notes = daily_sync.scan_vault(vault_path)
all_notes_without_tc = daily_sync._find_all_notes_without_tc(vault_path)

print(f'📊 Status do Vault:')
print(f'📝 Notas novas sem topic_classification: {len(new_notes)}')
print(f'🔄 Notas modificadas precisando reindex: {len(modified_notes)}')
print(f'📭 Total notas sem topic_classification: {len(all_notes_without_tc)}')
"
```

## Solução de Problemas

### 1. Cron não executa
- Verifique permissões: `chmod +x /home/s015533607/Documentos/desenv/pkm/scripts/*.sh`
- Verifique PATH no cron: Adicione `PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin` no crontab
- Verifique logs do sistema: `grep CRON /var/log/syslog`

### 2. Git operations falham
- Verifique se o vault é um repositório git: `cd /home/s015533607/MEGAsync/Minhas_notas && git status`
- Configure git user se necessário:
  ```bash
  cd /home/s015533607/MEGAsync/Minhas_notas
  git config user.name "Daily Sync Bot"
  git config user.email "bot@example.com"
  ```

### 3. API timeouts
- Aumente `api_delay` em `src/topics/config.py`
- Verifique conexão com internet
- Verifique quota da API Gemini

### 4. Logs não são criados
- Verifique permissões: `mkdir -p /home/s015533607/Documentos/desenv/pkm/data/logs`
- Verifique espaço em disco: `df -h`

## Notificações (Opcional)

Para adicionar notificações:

1. **Email:** Configure `sendmail` ou use `mail` command
2. **Slack:** Adicione webhook no script
3. **Telegram:** Use bot API

Exemplo de notificação por email no script:
```bash
# No final do production_daily_sync.sh
if [ $overall_success = true ]; then
    echo "Daily sync completed successfully" | mail -s "Daily Sync Success" user@example.com
else
    echo "Daily sync failed - check logs" | mail -s "Daily Sync Failed" user@example.com
fi
```

## Backup e Recuperação

### Backup do Failure Tracker
```bash
cp ~/.pkm_failure_tracker.json ~/.pkm_failure_tracker.json.backup
```

### Restauração
```bash
cp ~/.pkm_failure_tracker.json.backup ~/.pkm_failure_tracker.json
```

## Atualização

Para atualizar o sistema:

1. **Puxe as mudanças:**
   ```bash
   cd /home/s015533607/Documentos/desenv/pkm
   git pull
   ```

2. **Reinicie o cron job (opcional):**
   ```bash
   # O cron job continuará funcionando automaticamente
   ```

3. **Teste as mudanças:**
   ```bash
   ./scripts/production_daily_sync.sh --test
   ```