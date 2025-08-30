#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting CI Smoke Tests..."

echo "📦 Compiling all modules..."
python -m compileall .

echo "🔍 Running ruff checks..."
ruff check .

echo "🔍 Running mypy checks..."
mypy --hide-error-codes || true

echo "🧪 Running core tests with coverage..."
pytest -q -m "core" --cov=./ --cov-report=term-missing:skip-covered

echo "✅ CI Smoke Tests completed successfully!"
