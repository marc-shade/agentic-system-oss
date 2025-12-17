#!/bin/bash
# Start optional services for the agentic system
# Usage: ./start-services.sh [qdrant|redis|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$ROOT_DIR/data"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect container runtime
detect_runtime() {
    if command -v docker &>/dev/null; then
        echo "docker"
    elif command -v podman &>/dev/null; then
        echo "podman"
    else
        echo ""
    fi
}

RUNTIME=$(detect_runtime)

start_qdrant() {
    echo -e "${CYAN}Starting Qdrant...${NC}"

    if [ -z "$RUNTIME" ]; then
        echo -e "${RED}No container runtime found. Install Docker or Podman.${NC}"
        echo "Alternatively, download Qdrant binary from:"
        echo "https://github.com/qdrant/qdrant/releases"
        return 1
    fi

    # Create data directory
    mkdir -p "$DATA_DIR/qdrant"

    # Check if already running
    if $RUNTIME ps --format '{{.Names}}' | grep -q '^qdrant$'; then
        echo -e "${YELLOW}Qdrant is already running${NC}"
        return 0
    fi

    # Remove stopped container if exists
    $RUNTIME rm -f qdrant 2>/dev/null || true

    # Start Qdrant
    $RUNTIME run -d --name qdrant \
        -p 6333:6333 \
        -p 6334:6334 \
        -v "$DATA_DIR/qdrant:/qdrant/storage" \
        qdrant/qdrant

    # Wait for startup
    echo -n "Waiting for Qdrant to start..."
    for i in {1..30}; do
        if curl -s http://localhost:6333/health | grep -q '"status":"ok"'; then
            echo -e " ${GREEN}Ready${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo -e " ${RED}Failed to start${NC}"
    return 1
}

start_redis() {
    echo -e "${CYAN}Starting Redis...${NC}"

    if [ -z "$RUNTIME" ]; then
        echo -e "${RED}No container runtime found. Install Docker or Podman.${NC}"
        echo "Alternatively, install Redis via package manager:"
        echo "  macOS: brew install redis && brew services start redis"
        echo "  Linux: sudo dnf install redis && sudo systemctl start redis"
        return 1
    fi

    # Create data directory
    mkdir -p "$DATA_DIR/redis"

    # Check if already running
    if $RUNTIME ps --format '{{.Names}}' | grep -q '^redis$'; then
        echo -e "${YELLOW}Redis is already running${NC}"
        return 0
    fi

    # Remove stopped container if exists
    $RUNTIME rm -f redis 2>/dev/null || true

    # Start Redis
    $RUNTIME run -d --name redis \
        -p 6379:6379 \
        -v "$DATA_DIR/redis:/data" \
        redis:alpine redis-server --appendonly yes

    # Wait for startup
    echo -n "Waiting for Redis to start..."
    for i in {1..15}; do
        if $RUNTIME exec redis redis-cli ping 2>/dev/null | grep -q 'PONG'; then
            echo -e " ${GREEN}Ready${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo -e " ${RED}Failed to start${NC}"
    return 1
}

stop_service() {
    local name=$1
    echo -e "${CYAN}Stopping $name...${NC}"

    if [ -z "$RUNTIME" ]; then
        echo -e "${RED}No container runtime found${NC}"
        return 1
    fi

    if $RUNTIME stop "$name" 2>/dev/null; then
        $RUNTIME rm "$name" 2>/dev/null || true
        echo -e "${GREEN}$name stopped${NC}"
    else
        echo -e "${YELLOW}$name was not running${NC}"
    fi
}

show_status() {
    echo -e "${CYAN}Service Status:${NC}"
    echo ""

    # Qdrant
    echo -n "  Qdrant: "
    if curl -s http://localhost:6333/health 2>/dev/null | grep -q '"status":"ok"'; then
        echo -e "${GREEN}Running${NC} (http://localhost:6333)"
    else
        echo -e "${YELLOW}Not running${NC}"
    fi

    # Redis
    echo -n "  Redis:  "
    if redis-cli ping 2>/dev/null | grep -q 'PONG'; then
        echo -e "${GREEN}Running${NC} (localhost:6379)"
    elif [ -n "$RUNTIME" ] && $RUNTIME exec redis redis-cli ping 2>/dev/null | grep -q 'PONG'; then
        echo -e "${GREEN}Running${NC} (localhost:6379, container)"
    else
        echo -e "${YELLOW}Not running${NC}"
    fi

    echo ""
}

usage() {
    echo "Usage: $0 [command] [service]"
    echo ""
    echo "Commands:"
    echo "  start [service]  Start service(s)"
    echo "  stop [service]   Stop service(s)"
    echo "  status           Show service status"
    echo ""
    echo "Services:"
    echo "  qdrant          Vector database (port 6333)"
    echo "  redis           Caching layer (port 6379)"
    echo "  all             All services"
    echo ""
    echo "Examples:"
    echo "  $0 start all     Start all services"
    echo "  $0 start qdrant  Start Qdrant only"
    echo "  $0 stop redis    Stop Redis"
    echo "  $0 status        Show status"
}

# Main
case "${1:-status}" in
    start)
        case "${2:-all}" in
            qdrant)
                start_qdrant
                ;;
            redis)
                start_redis
                ;;
            all)
                start_qdrant
                start_redis
                ;;
            *)
                echo -e "${RED}Unknown service: $2${NC}"
                usage
                exit 1
                ;;
        esac
        echo ""
        show_status
        ;;
    stop)
        case "${2:-all}" in
            qdrant)
                stop_service qdrant
                ;;
            redis)
                stop_service redis
                ;;
            all)
                stop_service qdrant
                stop_service redis
                ;;
            *)
                echo -e "${RED}Unknown service: $2${NC}"
                usage
                exit 1
                ;;
        esac
        ;;
    status)
        show_status
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        usage
        exit 1
        ;;
esac
