#!/bin/bash
# Test script for Topic Extractor

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Topic Extractor Test Suite"
echo "=========================================="
echo ""

# Setup
export PYTHONPATH="$PROJECT_ROOT"
cd "$PROJECT_ROOT"

echo "1. Testing module import..."
python3 -c "
from src.topics import TopicExtractor, TopicValidator, CDUManager
print('   ✓ Module imported successfully')
"

echo ""
echo "2. Testing CDU validation..."
python3 -c "
from src.topics.taxonomy_manager import CDUManager

test_codes = ['321.1', '305.8', '658.012', 'invalid', '123']
for code in test_codes:
    is_valid = CDUManager.validate_cdu_format(code)
    status = '✓' if is_valid else '✗'
    print(f'   {status} {code}')
"

echo ""
echo "3. Testing topic validator..."
python3 -c "
from src.topics.topic_validator import TopicValidator, TopicValidationError

validator = TopicValidator()

# Test valid topics
valid_topics = [
    {'name': f'topico_{i}', 'weight': 5 + (i % 6), 'confidence': 0.9}
    for i in range(10)
]

try:
    validator.validate_topics(valid_topics)
    print('   ✓ Valid topics accepted')
except TopicValidationError as e:
    print(f'   ✗ Failed: {e}')

# Test invalid weight
try:
    invalid = [{'name': 'test', 'weight': 4, 'confidence': 0.9}]
    validator.validate_topics(invalid)
    print('   ✗ Should reject weight 4')
except TopicValidationError:
    print('   ✓ Rejected invalid weight')
"

echo ""
echo "4. Testing dry-run mode..."
python3 -m src.topics.topic_extractor \
    --test-dir "30 LIDERANCA" \
    --dry-run \
    --output-dir data/logs/topics 2>&1 | grep -E "(Found|Processing|DRY-RUN)" | head -5

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
echo ""
echo "To run real extraction on 1 note:"
echo "  python3 -m src.topics.topic_extractor --test-dir '30 LIDERANCA'"
echo ""
echo "To run on entire vault:"
echo "  python3 -m src.topics.topic_extractor"
