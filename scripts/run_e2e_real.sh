#!/bin/bash
# E2E Real Trading Test Runner - Bash Script
# Gerçek OKX API'leri ile uçtan uca test koşucu.
# Mock kullanmaz, gerçek verilerle test eder.

set -euo pipefail

# Script configuration
SCRIPT_NAME="E2E Real Trading Test"
SCRIPT_VERSION="1.0.0"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_RUNNER="$PROJECT_ROOT/tests/e2e/e2e_real_runner.py"
REPORTS_DIR="$PROJECT_ROOT/reports/e2e"
LOGS_DIR="$REPORTS_DIR/logs"

# Default parameters
MODE="paper"
SYMBOLS="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP"
TIMEFRAMES="5m,15m,1h"
DURATION=30
FAIL_FAST=false
VERBOSE=false
CONFIG_FILE=".env.e2e"

# Color functions
print_color() {
    local color=$1
    local message=$2
    case $color in
        "red") echo -e "\033[31m$message\033[0m" ;;
        "green") echo -e "\033[32m$message\033[0m" ;;
        "yellow") echo -e "\033[33m$message\033[0m" ;;
        "blue") echo -e "\033[34m$message\033[0m" ;;
        "magenta") echo -e "\033[35m$message\033[0m" ;;
        "cyan") echo -e "\033[36m$message\033[0m" ;;
        *) echo "$message" ;;
    esac
}

print_success() {
    print_color "green" "✅ $1"
}

print_warning() {
    print_color "yellow" "⚠️ $1"
}

print_error() {
    print_color "red" "❌ $1"
}

print_info() {
    print_color "cyan" "ℹ️ $1"
}

# Help function
show_help() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

Usage: $0 [OPTIONS]

Options:
    -m, --mode MODE           Trading mode: paper or live (default: paper)
    -s, --symbols SYMBOLS     Test symbols (comma-separated) (default: BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP)
    -t, --timeframes TF       Test timeframes (comma-separated) (default: 5m,15m,1h)
    -d, --duration MINUTES    Test duration in minutes (default: 30)
    -f, --fail-fast          Stop on first critical error
    -v, --verbose            Verbose logging
    -c, --config FILE        Environment configuration file (default: .env.e2e)
    -h, --help               Show this help message

Examples:
    $0 --mode paper --duration 20
    $0 --mode paper --symbols "BTC-USDT-SWAP,ETH-USDT-SWAP" --verbose
    $0 --mode live --duration 60 --fail-fast

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -s|--symbols)
                SYMBOLS="$2"
                shift 2
                ;;
            -t|--timeframes)
                TIMEFRAMES="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -f|--fail-fast)
                FAIL_FAST=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate parameters
validate_params() {
    print_info "Validating parameters..."
    
    # Validate mode
    if [[ "$MODE" != "paper" && "$MODE" != "live" ]]; then
        print_error "Invalid mode: $MODE. Must be 'paper' or 'live'"
        exit 1
    fi
    
    # Validate duration
    if [[ $DURATION -lt 5 || $DURATION -gt 120 ]]; then
        print_error "Duration must be between 5 and 120 minutes"
        exit 1
    fi
    
    # Warning for live mode
    if [[ "$MODE" == "live" && "$FAIL_FAST" == "false" ]]; then
        print_warning "Live mode detected - consider using --fail-fast for safety"
    fi
    
    print_success "Parameters validated"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python not found. Please install Python 3.8+ and ensure it's in PATH"
        exit 1
    fi
    
    # Use python3 if available, otherwise python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Python found: $PYTHON_VERSION"
    
    # Check if E2E runner exists
    if [[ ! -f "$E2E_RUNNER" ]]; then
        print_error "E2E runner not found: $E2E_RUNNER"
        exit 1
    fi
    print_success "E2E runner found"
    
    # Check if E2E runner is executable
    if [[ ! -x "$E2E_RUNNER" ]]; then
        chmod +x "$E2E_RUNNER"
        print_info "Made E2E runner executable"
    fi
}

# Create directories
create_directories() {
    print_info "Creating directories..."
    
    mkdir -p "$REPORTS_DIR"
    mkdir -p "$LOGS_DIR"
    
    print_success "Directories created: $REPORTS_DIR"
}

# Load environment configuration
load_environment() {
    print_info "Loading environment configuration..."
    
    local env_file="$PROJECT_ROOT/$CONFIG_FILE"
    
    if [[ -f "$env_file" ]]; then
        print_success "Environment file found: $env_file"
        
        # Load environment variables from file
        set -a  # automatically export all variables
        source "$env_file"
        set +a  # stop automatically exporting
        
        print_success "Environment variables loaded"
    else
        print_warning "Environment file not found: $env_file (using system environment variables)"
    fi
}

# Validate environment variables
validate_environment() {
    print_info "Validating environment variables..."
    
    local required_vars=("OKX_API_KEY" "OKX_API_SECRET" "OKX_API_PASSPHRASE")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
    
    print_success "Environment variables validated"
}

# Build command arguments
build_command() {
    print_info "Building command arguments..."
    
    local args=(
        "$E2E_RUNNER"
        "--mode" "$MODE"
        "--symbols" "$SYMBOLS"
        "--timeframes" "$TIMEFRAMES"
        "--duration" "$DURATION"
    )
    
    if [[ "$FAIL_FAST" == "true" ]]; then
        args+=("--fail-fast")
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        args+=("--verbose")
    fi
    
    # Build command line
    COMMAND_LINE="$PYTHON_CMD ${args[*]}"
    print_info "Command: $COMMAND_LINE"
}

# Run E2E test
run_e2e_test() {
    print_info "Starting E2E test..."
    print_color "white" "Mode: $MODE"
    print_color "white" "Symbols: $SYMBOLS"
    print_color "white" "Timeframes: $TIMEFRAMES"
    print_color "white" "Duration: $DURATION minutes"
    print_color "white" "Fail Fast: $FAIL_FAST"
    print_color "white" "Verbose: $VERBOSE"
    echo
    
    # Change to project root directory
    cd "$PROJECT_ROOT"
    
    # Record start time
    START_TIME=$(date +%s)
    
    # Execute the E2E runner
    if $COMMAND_LINE; then
        # Success
        END_TIME=$(date +%s)
        DURATION_SEC=$((END_TIME - START_TIME))
        
        print_success "E2E test completed successfully!"
        print_info "Duration: ${DURATION_SEC}s"
        
        # Show report location
        local report_file="$REPORTS_DIR/E2E_REPORT.md"
        if [[ -f "$report_file" ]]; then
            print_success "Report generated: $report_file"
        fi
        
        # Show artifacts
        print_info "Generated artifacts:"
        if [[ -d "$REPORTS_DIR" ]]; then
            ls -la "$REPORTS_DIR" | grep -v "^d" | awk '{print "  - " $9}' | grep -v "^  - $"
        fi
        
        return 0
    else
        # Failure
        END_TIME=$(date +%s)
        DURATION_SEC=$((END_TIME - START_TIME))
        
        print_error "E2E test failed with exit code: $?"
        print_info "Duration: ${DURATION_SEC}s"
        
        # Show log file if it exists
        local log_file="$LOGS_DIR/e2e_test.log"
        if [[ -f "$log_file" ]]; then
            print_info "Check log file for details: $log_file"
        fi
        
        return 1
    fi
}

# Cleanup function
cleanup() {
    print_info "Cleaning up..."
    # Any cleanup tasks can be added here
}

# Main function
main() {
    # Set up error handling
    trap 'print_error "Script execution failed at line $LINENO"; cleanup; exit 1' ERR
    
    print_color "magenta" "🚀 $SCRIPT_NAME v$SCRIPT_VERSION"
    print_color "magenta" "=================================================="
    
    # Parse arguments
    parse_args "$@"
    
    # Validate parameters
    validate_params
    
    # Check prerequisites
    check_prerequisites
    
    # Create directories
    create_directories
    
    # Load environment
    load_environment
    
    # Validate environment
    validate_environment
    
    # Build command
    build_command
    
    # Run E2E test
    local exit_code=0
    run_e2e_test || exit_code=$?
    
    # Cleanup
    cleanup
    
    # Exit with appropriate code
    exit $exit_code
}

# Run main function
main "$@"


