#!/bin/bash
# Run Telegram bot tests
# Usage: ./scripts/ci_tg.sh [test_file]

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing..."
    pip install pytest pytest-asyncio
fi

# Run Telegram tests
if [ -z "$1" ]; then
    echo "Running all Telegram tests..."
    pytest tests/telegram/ -v --tb=short
else
    echo "Running specific test: $1"
    pytest "$1" -v --tb=short
fi

echo "✅ Telegram tests completed"

