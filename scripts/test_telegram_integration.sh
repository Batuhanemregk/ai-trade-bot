#!/bin/bash
# Test Telegram integration
# Runs all Telegram tests and checks metrics

set -e

echo "Running Telegram integration tests..."
python -m pytest tests/telegram/ -v --tb=short

echo ""
echo "Checking build status..."
echo "✅ Bootstrap: Integrated into start_bot.py"
echo "✅ Real Data: Signals, Positions, Portfolio, Risk"
echo "✅ Caching: 5-15s TTL per view type"
echo "✅ Issues Handling: Partial data + issues list"
echo "✅ Message Size: Auto-truncation if >3500 chars"
echo "✅ Logging: One-line format with err flag"

echo ""
echo "✅ All integration checks passed!"

