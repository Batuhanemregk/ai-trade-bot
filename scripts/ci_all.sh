#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Full CI Tests..."

echo "📦 Compiling all modules..."
python -m compileall .

echo "🔍 Running ruff checks..."
ruff check .

echo "🧪 Running all tests with coverage..."
pytest -q -m "core or glue" --maxfail=1 --cov=./ --cov-report=term-missing:skip-covered

echo "✅ Full CI Tests completed successfully!"
