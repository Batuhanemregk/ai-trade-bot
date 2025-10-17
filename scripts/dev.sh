#!/bin/bash
# ========================================
# AI Trading Bot - Developer Scripts
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

# Navigate to project root
cd "$(dirname "$0")/.." || exit 1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# ========================================
# PYTHON DETECTION
# ========================================

get_python_path() {
    local venv_path="$1"
    local no_venv="$2"
    
    # Eğer --no-venv belirtilmişse sistem Python kullan
    if [[ "$no_venv" == "true" ]]; then
        for cmd in python3 python py; do
            if command -v "$cmd" &> /dev/null; then
                echo "$cmd"
                return 0
            fi
        done
        echo -e "${RED}❌ Python bulunamadı! Lütfen Python 3.11+ yükleyin.${NC}" >&2
        return 1
    fi
    
    # Eğer venv_path belirtilmişse
    if [[ -n "$venv_path" ]]; then
        local venv_python="$venv_path/bin/python"
        if [[ -f "$venv_python" ]]; then
            echo "$venv_python"
            return 0
        fi
        echo -e "${RED}❌ Venv bulunamadı: $venv_path${NC}" >&2
        return 1
    fi
    
    # Varsayılan venv konumlarını kontrol et
    for venv in venv/.venv; do
        if [[ -f "$venv/bin/python" ]]; then
            echo "$venv/bin/python"
            return 0
        fi
    done
    
    # Venv bulunamadıysa sistem Python kullan
    echo -e "${YELLOW}⚠️  Venv bulunamadı, sistem Python kullanılıyor...${NC}" >&2
    for cmd in python3 python py; do
        if command -v "$cmd" &> /dev/null; then
            echo "$cmd"
            return 0
        fi
    done
    
    echo -e "${RED}❌ Python bulunamadı! Lütfen venv oluşturun veya Python 3.11+ yükleyin.${NC}" >&2
    return 1
}

# ========================================
# FUNCTIONS
# ========================================

show_banner() {
    local title="$1"
    local color="${2:-$CYAN}"
    echo ""
    echo -e "${color}========================================${NC}"
    echo -e "${color} $title${NC}"
    echo -e "${color}========================================${NC}"
    echo ""
}

show_python() {
    local venv_path=""
    local no_venv="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv-path) venv_path="$2"; shift 2 ;;
            --no-venv) no_venv="true"; shift ;;
            *) shift ;;
        esac
    done
    
    show_banner "🐍 PYTHON CONFIGURATION" "$CYAN"
    
    local python_cmd
    if python_cmd=$(get_python_path "$venv_path" "$no_venv"); then
        echo -e "${YELLOW}Python executable:${NC} $python_cmd"
        
        local version
        version=$($python_cmd --version 2>&1)
        echo -e "${YELLOW}Version:${NC} $version"
        
        local location
        location=$($python_cmd -c "import sys; print(sys.executable)" 2>&1)
        echo -e "${YELLOW}Location:${NC} $location"
        echo ""
    else
        echo -e "${RED}❌ Python yapılandırması başarısız${NC}"
        return 1
    fi
}

install_req() {
    local venv_path=""
    local no_venv="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv-path) venv_path="$2"; shift 2 ;;
            --no-venv) no_venv="true"; shift ;;
            *) shift ;;
        esac
    done
    
    show_banner "📦 INSTALLING REQUIREMENTS" "$MAGENTA"
    
    local python_cmd
    if python_cmd=$(get_python_path "$venv_path" "$no_venv"); then
        echo -e "${CYAN}Using Python: $python_cmd${NC}"
        echo ""
        
        $python_cmd -m pip install --upgrade pip
        $python_cmd -m pip install -r requirements.txt
        
        echo ""
        echo -e "${GREEN}✅ Requirements installed successfully!${NC}"
    else
        return 1
    fi
}

run_trading() {
    local once=""
    local timeout=""
    local dry_run=""
    local venv_path=""
    local no_venv="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --once) once="--once"; shift ;;
            --timeout) timeout="--timeout $2"; shift 2 ;;
            --dry-run) export TRADING_MODE="DRY_RUN"; shift ;;
            --venv-path) venv_path="$2"; shift 2 ;;
            --no-venv) no_venv="true"; shift ;;
            *) shift ;;
        esac
    done
    
    show_banner "🤖 STARTING TRADING BOT (DEV MODE)" "$GREEN"
    
    local python_cmd
    if ! python_cmd=$(get_python_path "$venv_path" "$no_venv"); then
        return 1
    fi
    
    echo -e "${CYAN}Python: $python_cmd${NC}"
    echo -e "${YELLOW}Environment:${NC}"
    echo "  APP_ENV       = $APP_ENV"
    echo "  LOG_LEVEL     = $LOG_LEVEL"
    echo "  DEV_CONSOLE   = $DEV_CONSOLE"
    echo "  TRADING_MODE  = ${TRADING_MODE:-PAPER}"
    echo ""
    
    $python_cmd -u -m infrastructure.runtime trading --console --debug $once $timeout
}

run_scheduler() {
    local no_detach=""
    local venv_path=""
    local no_venv="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-detach) no_detach="--no-detach"; shift ;;
            --venv-path) venv_path="$2"; shift 2 ;;
            --no-venv) no_venv="true"; shift ;;
            *) shift ;;
        esac
    done
    
    show_banner "⏰ STARTING SCHEDULER (DEV MODE)" "$CYAN"
    
    local python_cmd
    if ! python_cmd=$(get_python_path "$venv_path" "$no_venv"); then
        return 1
    fi
    
    echo -e "${CYAN}Python: $python_cmd${NC}"
    echo -e "${YELLOW}Environment:${NC}"
    echo "  APP_ENV       = $APP_ENV"
    echo "  LOG_LEVEL     = $LOG_LEVEL"
    echo "  DEV_CONSOLE   = $DEV_CONSOLE"
    echo ""
    
    $python_cmd -u -m infrastructure.scheduler_runner --console --debug $no_detach
}

run_backtest() {
    local days="${1:-90}"
    local symbol="${2:-BTC-USDT}"
    
    show_banner "📊 RUNNING BACKTEST (DEV MODE)" "$MAGENTA"
    
    echo -e "${YELLOW}Parameters:${NC}"
    echo "  Days   = $days"
    echo "  Symbol = $symbol"
    echo ""
    
    python3 -u scripts/full_bot_backtest.py --days "$days" --symbol "$symbol"
}

tail_logs() {
    local lines="${1:-50}"
    local follow="$2"
    
    show_banner "📜 VIEWING LOGS" "$YELLOW"
    
    local log_file=$(ls -1t logs/*.log 2>/dev/null | head -n1)
    
    if [[ -n "$log_file" ]]; then
        echo -e "${CYAN}Log file: $(basename "$log_file")${NC}"
        echo ""
        
        if [[ "$follow" == "--follow" ]]; then
            tail -n "$lines" -f "$log_file" | while IFS= read -r line; do
                if echo "$line" | grep -qE "ERROR|CRITICAL"; then
                    echo -e "${RED}$line${NC}"
                elif echo "$line" | grep -q "WARNING"; then
                    echo -e "${YELLOW}$line${NC}"
                elif echo "$line" | grep -q "DEBUG"; then
                    echo -e "\033[0;90m$line${NC}"  # Gray
                else
                    echo "$line"
                fi
            done
        else
            tail -n "$lines" "$log_file" | while IFS= read -r line; do
                if echo "$line" | grep -qE "ERROR|CRITICAL"; then
                    echo -e "${RED}$line${NC}"
                elif echo "$line" | grep -q "WARNING"; then
                    echo -e "${YELLOW}$line${NC}"
                else
                    echo "$line"
                fi
            done
        fi
    else
        echo -e "${RED}No log files found!${NC}"
    fi
}

check_health() {
    local venv_path=""
    local no_venv="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv-path) venv_path="$2"; shift 2 ;;
            --no-venv) no_venv="true"; shift ;;
            *) shift ;;
        esac
    done
    
    show_banner "🏥 HEALTH CHECK" "$GREEN"
    
    echo -e "${YELLOW}Checking system health...${NC}"
    echo ""
    
    # Check Python version
    local python_cmd
    if python_cmd=$(get_python_path "$venv_path" "$no_venv"); then
        local version
        version=$($python_cmd --version 2>&1)
        echo -e "${GREEN}✅ Python: $version ($python_cmd)${NC}"
    else
        echo -e "${RED}❌ Python: Bulunamadı${NC}"
    fi
    
    # Check Python process
    if pgrep -f "python.*infrastructure" > /dev/null; then
        echo -e "${GREEN}✅ Bot Process: RUNNING (PID: $(pgrep -f 'python.*infrastructure'))${NC}"
    else
        echo -e "${RED}❌ Bot Process: NOT RUNNING${NC}"
    fi
    
    # Check Docker
    if command -v docker &> /dev/null && docker ps &> /dev/null; then
        if docker ps --format "{{.Names}}" | grep -qE "prometheus|grafana"; then
            echo -e "${GREEN}✅ Docker: RUNNING${NC}"
            docker ps --format "   └─ {{.Names}}" | grep -E "prometheus|grafana"
        else
            echo -e "${YELLOW}⚠️  Docker: Running but no monitoring containers${NC}"
        fi
    else
        echo -e "${RED}❌ Docker: NOT RUNNING${NC}"
    fi
    
    # Check Metrics endpoint
    if curl -s -f http://localhost:8000/metrics > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Metrics Endpoint: OK (http://localhost:8000/metrics)${NC}"
    else
        echo -e "${RED}❌ Metrics Endpoint: NOT RESPONDING${NC}"
    fi
    
    # Check Prometheus
    if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Prometheus: OK (http://localhost:9090)${NC}"
    else
        echo -e "${RED}❌ Prometheus: NOT RESPONDING${NC}"
    fi
    
    # Check Grafana
    if curl -s -f http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Grafana: OK (http://localhost:3000)${NC}"
    else
        echo -e "${RED}❌ Grafana: NOT RESPONDING${NC}"
    fi
    
    echo ""
}

stop_bot() {
    show_banner "🛑 STOPPING BOT" "$RED"
    
    if pgrep -f "python.*infrastructure" > /dev/null; then
        pkill -9 -f "python.*infrastructure"
        echo -e "${GREEN}✅ Bot processes stopped${NC}"
    else
        echo -e "${YELLOW}ℹ️  No bot processes running${NC}"
    fi
}

clean_logs() {
    local days_old="${1:-7}"
    
    show_banner "🧹 CLEANING OLD LOGS" "$YELLOW"
    
    local old_logs=$(find logs -name "*.log*" -type f -mtime +$days_old 2>/dev/null)
    
    if [[ -n "$old_logs" ]]; then
        local count=$(echo "$old_logs" | wc -l)
        echo -e "${YELLOW}Found $count old log files (>$days_old days)${NC}"
        echo "$old_logs" | while IFS= read -r log; do
            echo "  Removing: $(basename "$log")"
            rm -f "$log"
        done
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    else
        echo -e "${YELLOW}ℹ️  No old logs to clean${NC}"
    fi
}

show_menu() {
    show_banner "🛠️  AI TRADING BOT - DEV MENU" "$CYAN"
    
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo "  run_trading              - Start trading bot (scheduler mode)"
    echo "  run_trading --once       - Single run (test)"
    echo "  run_scheduler            - Start scheduler"
    echo "  tail_logs 50 --follow    - Live log viewer"
    echo "  check_health             - System health check"
    echo "  show_python              - Show Python configuration"
    echo "  install_req              - Install requirements.txt"
    echo "  stop_bot                 - Stop all bot processes"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo -e "  ${GRAY}--venv-path <path>       - Use specific venv${NC}"
    echo -e "  ${GRAY}--no-venv                - Use system Python${NC}"
    echo ""
    echo -e "${GREEN}Environment Variables Set:${NC}"
    echo "  APP_ENV         = $APP_ENV"
    echo "  LOG_LEVEL       = $LOG_LEVEL"
    echo "  DEV_CONSOLE     = $DEV_CONSOLE"
    echo "  PYTHONUNBUFFERED= $PYTHONUNBUFFERED"
    echo ""
    echo -e "${CYAN}Usage: source scripts/dev.sh${NC}"
    echo ""
}

# ========================================
# AUTO-SHOW MENU
# ========================================
show_menu

