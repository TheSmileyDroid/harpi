#!/bin/bash

# Harpi Discord Bot Runner Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_MODE="gunicorn"
RESTART_DELAY=5

# Functions
print_usage() {
    echo -e "${BLUE}Harpi Discord Bot Runner${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mode MODE       Run mode: 'gunicorn', 'flask', 'test' (default: gunicorn)"
    echo "  -p, --port PORT       Port to bind to (default: 8000)"
    echo "  -h, --host HOST       Host to bind to (default: 0.0.0.0)"
    echo "  -r, --restart         Auto-restart on failure (only for flask mode)"
    echo "  -d, --debug           Enable debug mode"
    echo "  --help                Show this help message"
    echo ""
    echo "Modes:"
    echo "  gunicorn    Production server with Discord bot"
    echo "  flask       Development server with Discord bot"
    echo "  test        Run connection tests"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run with gunicorn (production)"
    echo "  $0 -m flask -r             # Run with Flask development server with auto-restart"
    echo "  $0 -m test                  # Run connection tests"
    echo "  $0 -m gunicorn -p 5000      # Run gunicorn on port 5000"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_error ".env file not found! Please create it with your Discord token."
        exit 1
    fi

    # Check if Discord token is set
    if ! grep -q "DISCORD_TOKEN=" .env; then
        log_error "DISCORD_TOKEN not found in .env file!"
        exit 1
    fi

    # Check Python dependencies based on mode
    if [ "$MODE" = "gunicorn" ] && ! python3 -c "import gunicorn" 2>/dev/null; then
        log_error "Gunicorn not installed. Install with: pip install gunicorn or uv add gunicorn"
        exit 1
    fi

    if ! python3 -c "import flask, discord" 2>/dev/null; then
        log_error "Required Python packages not installed. Run: pip install -r requirements.txt or uv sync --upgrade"
        exit 1
    fi

    log_info "Dependencies check passed ✓"
}

run_gunicorn() {
    log_info "Starting Harpi with Gunicorn (Production Mode)"
    log_info "Server will be available at http://${HOST}:${PORT}"
    log_info "Bot status: http://${HOST}:${PORT}/status"
    log_info "Press Ctrl+C to stop"

    exec gunicorn --config gunicorn_config.py --bind "${HOST}:${PORT}" app:app
}

run_flask() {
    log_info "Starting Harpi with Flask Development Server"
    log_info "Server will be available at http://${HOST}:${PORT}"
    log_info "Bot status: http://${HOST}:${PORT}/status"

    if [ "$DEBUG" = true ]; then
        uv run flask -b ${HOST}:${PORT} --app app run --debug || true
    else
        uv run flask -b ${HOST}:${PORT}  --app app run || true
    fi
}

run_test() {
    log_info "Running Harpi connection tests..."
    python3 test_bot.py
}

cleanup() {
    log_info "Cleaning up..."
    # Kill any background processes if needed
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Parse command line arguments
MODE="$DEFAULT_MODE"
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
AUTO_RESTART=false
DEBUG=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -r|--restart)
            AUTO_RESTART=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate mode
case $MODE in
    gunicorn|flask|test)
        ;;
    *)
        log_error "Invalid mode: $MODE"
        print_usage
        exit 1
        ;;
esac

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
log_info "Starting Harpi Discord Bot Runner..."
log_info "Mode: $MODE"
if [ "$MODE" != "test" ]; then
    log_info "Host: $HOST"
    log_info "Port: $PORT"
fi
if [ "$DEBUG" = true ]; then
    log_info "Debug: enabled"
fi

# Check dependencies
check_dependencies

# Run based on mode
case $MODE in
    gunicorn)
        run_gunicorn
        ;;
    flask)
        run_flask
        ;;
    test)
        run_test
        ;;
esac
