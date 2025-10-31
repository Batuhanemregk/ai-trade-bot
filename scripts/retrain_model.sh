#!/bin/bash
# ML Model Yeniden Eğitim Scripti
# Bash script for manual model retraining

FREQUENCY="weekly"
RUN_ONCE=false
SHOW_HISTORY=false
SHOW_NEXT=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --frequency)
            FREQUENCY="$2"
            shift 2
            ;;
        --run-once)
            RUN_ONCE=true
            shift
            ;;
        --show-history)
            SHOW_HISTORY=true
            shift
            ;;
        --show-next)
            SHOW_NEXT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --frequency weekly|monthly    Retrain frequency (default: weekly)"
            echo "  --run-once                   Run retrain once and exit"
            echo "  --show-history               Show retrain history"
            echo "  --show-next                  Show next retrain time"
            echo "  -h, --help                   Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

function start_model_retrain() {
    echo -e "${CYAN}🚀 Starting ML Model Retraining...${NC}"
    echo -e "${CYAN}===============================================${NC}"
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Run retrain
    if [ "$RUN_ONCE" = true ]; then
        echo -e "${YELLOW}📊 Running one-time retrain...${NC}"
        python -m ml.auto_retrain_scheduler --frequency "$FREQUENCY" --run-once
    else
        echo -e "${YELLOW}🔄 Starting auto-retrain scheduler...${NC}"
        echo -e "${GREEN}Frequency: $FREQUENCY${NC}"
        echo -e "${RED}Press Ctrl+C to stop${NC}"
        python -m ml.auto_retrain_scheduler --frequency "$FREQUENCY"
    fi
}

function show_retrain_history() {
    echo -e "${CYAN}📋 Retrain History${NC}"
    echo -e "${CYAN}=================${NC}"
    
    if [ -f "reports/retrain_history.jsonl" ]; then
        tail -n 10 "reports/retrain_history.jsonl" | while read -r line; do
            if [ -n "$line" ]; then
                retrain_id=$(echo "$line" | python -c "import sys, json; print(json.load(sys.stdin)['retrain_id'])" 2>/dev/null)
                status=$(echo "$line" | python -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
                start_time=$(echo "$line" | python -c "import sys, json; print(json.load(sys.stdin)['start_time'])" 2>/dev/null)
                
                if [ "$status" = "SUCCESS" ]; then
                    echo -e "✅ $start_time - $retrain_id - $status"
                else
                    echo -e "❌ $start_time - $retrain_id - $status"
                fi
            fi
        done
    else
        echo -e "${YELLOW}No retrain history found.${NC}"
    fi
}

function show_next_retrain() {
    echo -e "${CYAN}⏰ Next Retrain Schedule${NC}"
    echo -e "${CYAN}=======================${NC}"
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    python -c "
from ml.auto_retrain_scheduler import AutoRetrainScheduler
scheduler = AutoRetrainScheduler('$FREQUENCY')
print('Next retrain:', scheduler.get_next_retrain_time())
"
}

# Main logic
if [ "$SHOW_HISTORY" = true ]; then
    show_retrain_history
elif [ "$SHOW_NEXT" = true ]; then
    show_next_retrain
else
    start_model_retrain
fi

echo -e "\n${GREEN}✅ Script completed!${NC}"

