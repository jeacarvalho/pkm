#!/bin/bash
# Production Daily Sync Script v2.1
# Executa o sistema de sincronização diária e faz commit das alterações no vault

set -e  # Exit on error
set -u  # Treat unset variables as error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="$PROJECT_ROOT/data/logs/production"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/daily_sync_${TIMESTAMP}.log"
FAILURE_LOG="$LOG_DIR/failures_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" >> "$FAILURE_LOG"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        log_error "Git not found"
        exit 1
    fi
    
    # Check vault directory
    if [ ! -d "$VAULT_PATH" ]; then
        log_error "Vault directory not found: $VAULT_PATH"
        exit 1
    fi
    
    # Check if vault is a git repository
    if [ ! -d "$VAULT_PATH/.git" ]; then
        log_error "Vault is not a git repository: $VAULT_PATH"
        exit 1
    fi
    
    log_success "All dependencies checked"
}

setup_logging() {
    log_info "Setting up logging..."
    mkdir -p "$LOG_DIR"
    log_success "Log directory: $LOG_DIR"
}

run_daily_sync() {
    log_info "Starting Daily Sync v2.1..."

    # Set PYTHONPATH for system Python
    export PYTHONPATH="$PROJECT_ROOT"

    # Run daily sync in production mode
    cd "$PROJECT_ROOT"

    log_info "Running daily sync in PRODUCTION mode..."
    python3 -c "
import os
import sys
from pathlib import Path

sys.path.insert(0, '$PROJECT_ROOT')

from src.topics.daily_sync import DailySync
from src.topics.config import topics_config

# Configure for production
topics_config.dry_run = False
topics_config.limit = 0  # Unlimited

daily_sync = DailySync(topics_config)
vault_path = Path('$VAULT_PATH')

print('🚀 Starting Daily Sync v2.1 - Production Mode')
print(f'📅 Date: $(date +\"%Y-%m-%d %H:%M:%S\")')
print(f'📁 Vault: {vault_path}')
print('📋 Processing:')
print('   - ALL notes without topic_classification')
print('   - Notes modified YESTERDAY that need reindexing')

# Process notes in production mode
modified_notes = daily_sync.process_notes(vault_path, production_mode=True)

print(f'✅ Processing complete!')
print(f'📝 Notes processed: {len(modified_notes)}')

if modified_notes:
    print('\\nModified notes:')
    for note in modified_notes[:20]:  # Show first 20
        print(f'  - {Path(note).name}')
    if len(modified_notes) > 20:
        print(f'  ... and {len(modified_notes) - 20} more')
else:
    print('📭 No notes needed processing')
" 2>&1 | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        log_success "Daily sync completed successfully"
    else
        log_error "Daily sync failed with exit code: $exit_code"
        return 1
    fi
}

git_operations() {
    log_info "Starting git operations for vault..."
    
    cd "$VAULT_PATH"
    
    # Check if there are any changes
    if git status --porcelain | grep -q .; then
        log_info "Changes detected in vault"
        
        # Show what changed
        log_info "Changes summary:"
        git status --short | tee -a "$LOG_FILE"
        
        # Add all changes
        log_info "Adding changes to git..."
        git add . 2>&1 | tee -a "$LOG_FILE"
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            log_success "Changes added to git"
        else
            log_error "Failed to add changes to git"
            return 1
        fi
        
        # Create commit message
        COMMIT_MSG="Daily Sync $(date +'%Y-%m-%d %H:%M:%S') - Topic classification updates"
        
        # Commit changes
        log_info "Committing changes..."
        git commit -m "$COMMIT_MSG" 2>&1 | tee -a "$LOG_FILE"
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            log_success "Changes committed"
        else
            log_error "Failed to commit changes"
            return 1
        fi
        
        # Push to remote
        log_info "Pushing to remote repository..."
        git push 2>&1 | tee -a "$LOG_FILE"
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            log_success "Changes pushed to remote"
        else
            log_error "Failed to push changes"
            return 1
        fi
        
    else
        log_info "No changes detected in vault"
    fi
}

cleanup_old_logs() {
    log_info "Cleaning up old logs..."
    
    # Keep logs from last 30 days
    find "$LOG_DIR" -name "daily_sync_*.log" -mtime +30 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "failures_*.log" -mtime +30 -delete 2>/dev/null || true
    
    log_success "Old logs cleaned up"
}

send_notification() {
    local status=$1
    local message=$2
    
    # Simple notification - can be extended with email, Slack, etc.
    log_info "Notification: $message"
    
    # Example: Send to system log
    logger -t "daily_sync" "$message"
}

main() {
    log_info "=== Production Daily Sync Started ==="
    log_info "Timestamp: $(date)"
    log_info "Project: $PROJECT_ROOT"
    log_info "Vault: $VAULT_PATH"
    
    # Setup
    check_dependencies
    setup_logging
    
    # Track overall success
    local overall_success=true
    
    # Step 1: Run daily sync
    if run_daily_sync; then
        log_success "Step 1: Daily sync completed"
    else
        log_error "Step 1: Daily sync failed"
        overall_success=false
    fi
    
    # Step 2: Git operations (even if sync failed, commit any partial changes)
    if git_operations; then
        log_success "Step 2: Git operations completed"
    else
        log_error "Step 2: Git operations failed"
        overall_success=false
    fi
    
    # Step 3: Cleanup
    cleanup_old_logs
    
    # Final status
    if $overall_success; then
        log_success "=== Production Daily Sync Completed Successfully ==="
        send_notification "success" "Daily sync completed successfully"
        exit 0
    else
        log_error "=== Production Daily Sync Completed with Errors ==="
        send_notification "error" "Daily sync completed with errors - check logs"
        exit 1
    fi
}

# Run main function
main "$@"