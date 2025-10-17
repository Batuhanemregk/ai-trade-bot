#!/bin/bash
# Safe Scheduler Starter for Linux/Mac
# Checks prerequisites before starting

set -e

echo ""
echo "========================================"
echo "   AiBotBS Scheduler - Safe Start"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "[ERROR] Virtual environment not activated!"
    echo ""
    echo "Please activate venv first:"
    echo "  source venv/bin/activate"
    echo ""
    exit 1
fi

echo "[OK] Virtual environment: Active"
echo ""

# Check environment variables
if [[ -z "$OKX_API_KEY" ]]; then
    echo "[ERROR] OKX_API_KEY not set!"
    echo ""
    echo "Please create .env file with API credentials."
    echo ""
    exit 1
fi

echo "[OK] Environment variables: Set"
echo ""

# Check configuration
python scripts/check_yaml.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Configuration validation failed!"
    echo ""
    echo "Please check configs/policy.yaml"
    echo ""
    exit 1
fi

echo "[OK] Configuration: Valid"
echo ""

# Run tests
echo "Running scheduler tests..."
python scripts/test_scheduler.py
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Scheduler tests failed!"
    echo ""
    echo "Please fix issues before running."
    echo ""
    exit 1
fi

echo ""
echo "========================================"
echo "   All Checks Passed!"
echo "========================================"
echo ""

# Ask for confirmation
read -p "Start scheduler? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting scheduler..."
echo ""
echo "Press Ctrl+C to stop gracefully"
echo ""

# Start scheduler
python -m infrastructure.scheduler_runner

echo ""
echo "Scheduler stopped."

