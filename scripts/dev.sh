#!/bin/bash
# ========================================
# AI Trading Bot - Developer Scripts (Bash)
# Quick commands for development workflow
# ========================================

# Set development environment
export APP_ENV="dev"
export DEV_CONSOLE="1"
export LOG_LEVEL="DEBUG"
export PYTHONUNBUFFERED="1"
export PYTHONPATH="."
export CONSOLE_LOG="1"
export LOG_EMOJI="1"

# ========================================
# UTF-8 ENCODING SETUP
# ========================================

# Set UTF-8 environment variables
export PYTHONUTF8="1"
export PYTHONIOENCODING="utf-8"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"

# Configure terminal for UTF-8
echo "✅ UTF-8 encoding active (Bash)"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ========================================
# PYTHON DETECTION
# ========================================

function get_python_path() {
    local venv_path="$1"
    local no_venv="$2"
    
    if [[ "$no_venv" == "true" ]]; then
        # Use system Python
        if command -v python3 &> /dev/null; then
            echo "python3"
        elif command -v python &> /dev/null; then
            echo "python"
        else
            echo "python3"  # Default
        fi
    else
        # Use virtual environment
        if [[ -n "$venv_path" ]]; then
            if [[ -f "$venv_path/bin/activate" ]]; then
                echo "$venv_path/bin/python"
            else
                echo "python3"  # Fallback
            fi
        else
            # Auto-detect venv
            if [[ -f "venv/bin/activate" ]]; then
                echo "venv/bin/python"
            elif [[ -f ".venv/bin/activate" ]]; then
                echo ".venv/bin/python"
            else
                echo "python3"  # Fallback
            fi
        fi
    fi
}

# ========================================
# QUICK COMMANDS
# ========================================

function start_trading() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "🚀 Starting trading bot (scheduler mode)..."
    $python_cmd -u main.py
}

function start_trading_once() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "🚀 Starting trading bot (single run)..."
    $python_cmd -u main.py --once
}

function start_scheduler() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "⏰ Starting scheduler only..."
    $python_cmd -u infrastructure/scheduler.py
}

function watch_logs() {
    echo "📋 Watching logs..."
    if [[ -d "logs" ]]; then
        tail -f logs/*.log
    else
        echo "No logs directory found"
    fi
}

function test_health() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "🏥 Running health check..."
    $python_cmd -c "
import sys
sys.path.append('.')
from infrastructure.health import check_health
check_health()
"
}

function show_python() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "🐍 Python configuration:"
    echo "  Command: $python_cmd"
    echo "  Version: $($python_cmd --version)"
    echo "  Path: $(which $python_cmd)"
    echo "  Encoding: $PYTHONIOENCODING"
}

function install_req() {
    local python_cmd=$(get_python_path "$1" "$2")
    echo "📦 Installing requirements..."
    $python_cmd -m pip install -r requirements.txt
}

function stop_bot() {
    echo "🛑 Stopping bot processes..."
    pkill -f "python.*main.py" || true
    pkill -f "python.*scheduler.py" || true
    echo "Bot processes stopped"
}

# ========================================
# MAIN MENU
# ========================================

function show_menu() {
    echo "========================================="
    echo " AI TRADING BOT - DEV MENU (Bash)"
    echo "========================================="
    echo "Quick Commands:"
    echo "  1. start_trading            - Start trading bot (scheduler mode)"
    echo "  2. start_trading_once       - Single run test"
    echo "  3. start_scheduler          - Start scheduler only"
    echo "  4. watch_logs               - Live log viewer"
    echo "  5. test_health              - System health check"
    echo "  6. show_python              - Show Python configuration"
    echo "  7. install_req              - Install requirements.txt"
    echo "  8. stop_bot                 - Stop bot processes"
    echo ""
    echo "Options:"
    echo "  -VenvPath <path>            - Use specific venv"
    echo "  -NoVenv                     - Use system Python"
    echo ""
    echo "Environment:"
    echo "  APP_ENV          = $APP_ENV"
    echo "  LOG_LEVEL        = $LOG_LEVEL"
    echo "  DEV_CONSOLE      = $DEV_CONSOLE"
    echo "  PYTHONUNBUFFERED = $PYTHONUNBUFFERED"
    echo "  PYTHONIOENCODING = $PYTHONIOENCODING"
    echo ""
}

# Show menu if script is sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    show_menu
else
    echo "✅ Development environment loaded (Bash)"
    echo "💡 Use 'show_menu' to see available commands"
fi