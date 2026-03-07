#!/bin/bash
# Test Production Daily Sync Script v2.1 - Dry Run Mode
# Testa o sistema de sincronização diária sem fazer alterações reais

set -e  # Exit on error
set -u  # Treat unset variables as error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_PATH="/home/s015533607/MEGAsync/Minhas_notas"
LOG_DIR="$PROJECT_ROOT/data/logs/test"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/test_dry_run_${TIMESTAMP}.log"

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
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    
    # Check vault directory
    if [ ! -d "$VAULT_PATH" ]; then
        log_error "Vault directory not found: $VAULT_PATH"
        exit 1
    fi
    
    log_success "All dependencies checked"
}

setup_logging() {
    log_info "Setting up logging..."
    mkdir -p "$LOG_DIR"
    log_success "Log directory: $LOG_DIR"
}

run_dry_run_test() {
    log_info "Starting Daily Sync v2.1 - DRY RUN MODE..."
    
    # Set PYTHONPATH for system Python
    export PYTHONPATH="$PROJECT_ROOT"
    
    # Run daily sync with dry_run=True
    cd "$PROJECT_ROOT"
    
    log_info "Running daily sync with dry_run=True and force_all=True..."
    python3 -c "
import os
import sys
from pathlib import Path

sys.path.insert(0, '$PROJECT_ROOT')

from src.topics.daily_sync import DailySync
from src.topics.config import topics_config

# Configure for dry run
topics_config.dry_run = True
topics_config.limit = 0  # Unlimited

daily_sync = DailySync(topics_config)
vault_path = Path('$VAULT_PATH')

print('🚀 Starting Daily Sync v2.1 - DRY RUN MODE')
print(f'📅 Date: $(date +\"%Y-%m-%d %H:%M:%S\")')
print(f'📁 Vault: {vault_path}')

# Process notes in dry-run mode
print('\\n🔍 Processing notes in dry-run mode...')
modified_notes = daily_sync.process_notes(vault_path, force_all=True)

print(f'📊 Process Results:')
print(f'  - Modified notes: {len(modified_notes)}')

if modified_notes:
    print('\\n📝 Modified notes (would be updated):')
    for note in modified_notes[:10]:  # Show first 10
        print(f'  - {Path(note).name}')
    if len(modified_notes) > 10:
        print(f'  ... and {len(modified_notes) - 10} more')

# Test processing one note to ensure API works
if modified_notes:
    print('\\n🧪 Testing API with one note...')
    test_note = modified_notes[0]
    print(f'  Testing: {Path(test_note).name}')
    
    # Import topic extractor for testing
    from src.topics.topic_extractor import TopicExtractor
    extractor = TopicExtractor(topics_config)
    
    try:
        # Read note content
        with open(test_note, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract topics (dry run - won't save)
        topics = extractor.extract_topics(content)
        print(f'  ✅ API test successful! Extracted topics: {topics}')
    except Exception as e:
        print(f'  ❌ API test failed: {e}')
" 2>&1 | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        log_success "Dry run test completed successfully"
    else
        log_error "Dry run test failed with exit code: $exit_code"
        return 1
    fi
}

test_git_status() {
    log_info "Testing git status in vault..."
    
    cd "$VAULT_PATH"
    
    if [ -d ".git" ]; then
        log_info "Vault is a git repository"
        
        # Show git status
        log_info "Git status:"
        git status --short 2>&1 | tee -a "$LOG_FILE"
        
        # Show last commit
        log_info "Last commit:"
        git log -1 --oneline 2>&1 | tee -a "$LOG_FILE"
        
        log_success "Git status test completed"
    else
        log_warning "Vault is not a git repository"
    fi
}

main() {
    log_info "=== Production Daily Sync Test - DRY RUN ==="
    log_info "Timestamp: $(date)"
    log_info "Project: $PROJECT_ROOT"
    log_info "Vault: $VAULT_PATH"
    
    # Setup
    check_dependencies
    setup_logging
    
    # Track overall success
    local overall_success=true
    
    # Step 1: Run dry run test
    if run_dry_run_test; then
        log_success "Step 1: Dry run test completed"
    else
        log_error "Step 1: Dry run test failed"
        overall_success=false
    fi
    
    # Step 2: Test git status
    if test_git_status; then
        log_success "Step 2: Git status test completed"
    else
        log_warning "Step 2: Git status test had warnings"
    fi
    
    # Final status
    if $overall_success; then
        log_success "=== Production Daily Sync Test Completed Successfully ==="
        exit 0
    else
        log_error "=== Production Daily Sync Test Completed with Errors ==="
        exit 1
    fi
}

# Run main function
main "$@"