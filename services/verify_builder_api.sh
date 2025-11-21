#!/bin/bash
# Verify Builder Node API Installation

set -e

echo "=== Builder Node API Installation Verification ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_pass() {
    echo -e "${GREEN}✅${NC} $1"
}

check_fail() {
    echo -e "${RED}❌${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠️ ${NC} $1"
}

echo "1. Checking Python dependencies..."
if python3 -c "import fastapi" 2>/dev/null; then
    check_pass "FastAPI installed"
else
    check_fail "FastAPI not installed"
    echo "   Install: pip3.14 install fastapi --user"
    exit 1
fi

if python3 -c "import uvicorn" 2>/dev/null; then
    check_pass "Uvicorn installed"
else
    check_fail "Uvicorn not installed"
    echo "   Install: pip3.14 install uvicorn --user"
    exit 1
fi

if python3 -c "import prometheus_client" 2>/dev/null; then
    check_pass "Prometheus client installed"
else
    check_fail "Prometheus client not installed"
    echo "   Install: pip3.14 install prometheus-client --user"
    exit 1
fi

if python3 -c "import aiofiles" 2>/dev/null; then
    check_pass "Aiofiles installed"
else
    check_fail "Aiofiles not installed"
    echo "   Install: pip3.14 install aiofiles --user"
    exit 1
fi

if python3 -c "import redis" 2>/dev/null; then
    check_pass "Redis client installed"
else
    check_fail "Redis client not installed"
    echo "   Install: pip3.14 install redis --user"
    exit 1
fi

echo ""
echo "2. Checking API files..."

SERVICES_DIR="/home/marc/agentic-system/services"

if [ -f "$SERVICES_DIR/builder-node-api.py" ]; then
    check_pass "builder-node-api.py exists"
else
    check_fail "builder-node-api.py not found"
    exit 1
fi

if [ -f "$SERVICES_DIR/artifact_manager.py" ]; then
    check_pass "artifact_manager.py exists"
else
    check_fail "artifact_manager.py not found"
    exit 1
fi

if [ -f "$SERVICES_DIR/test_builder_api.py" ]; then
    check_pass "test_builder_api.py exists"
else
    check_warn "test_builder_api.py not found"
fi

if [ -f "$SERVICES_DIR/start-builder-api.sh" ]; then
    check_pass "start-builder-api.sh exists"
else
    check_warn "start-builder-api.sh not found"
fi

echo ""
echo "3. Checking directories..."

ARTIFACT_DIR="/home/marc/agentic-system/artifacts"
LOG_DIR="/home/marc/agentic-system/logs"

if [ -d "$ARTIFACT_DIR" ]; then
    check_pass "Artifacts directory exists: $ARTIFACT_DIR"
else
    check_warn "Artifacts directory missing, creating..."
    mkdir -p "$ARTIFACT_DIR"
    check_pass "Created artifacts directory"
fi

if [ -d "$LOG_DIR" ]; then
    check_pass "Logs directory exists: $LOG_DIR"
else
    check_warn "Logs directory missing, creating..."
    mkdir -p "$LOG_DIR"
    check_pass "Created logs directory"
fi

echo ""
echo "4. Checking services..."

# Check Redis
if docker ps | grep -q redis; then
    check_pass "Redis container is running"
elif docker ps -a | grep -q redis; then
    check_warn "Redis container exists but not running"
    echo "   Start: docker start redis"
else
    check_warn "Redis container not found"
    echo "   This is needed for build queue"
fi

# Check if Redis is accessible
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli ping >/dev/null 2>&1; then
        check_pass "Redis is accessible"
    else
        check_warn "Redis not responding to ping"
    fi
fi

echo ""
echo "5. Checking port availability..."

if lsof -i :9000 >/dev/null 2>&1; then
    check_warn "Port 9000 is already in use"
    echo "   Process: $(lsof -i :9000 | tail -1)"
else
    check_pass "Port 9000 is available"
fi

echo ""
echo "6. Testing API module load..."

cd "$SERVICES_DIR"
if python3 -c "
import sys
import importlib.util
spec = importlib.util.spec_from_file_location('builder_api', 'builder-node-api.py')
module = importlib.util.module_from_spec(spec)
sys.exit(0)
" 2>/dev/null; then
    check_pass "API module loads successfully"
else
    check_fail "API module failed to load"
    echo "   Check for syntax errors in builder-node-api.py"
    exit 1
fi

echo ""
echo "7. Checking permissions..."

if [ -x "$SERVICES_DIR/start-builder-api.sh" ]; then
    check_pass "start-builder-api.sh is executable"
else
    check_warn "start-builder-api.sh is not executable"
    chmod +x "$SERVICES_DIR/start-builder-api.sh"
    check_pass "Made start-builder-api.sh executable"
fi

if [ -x "$SERVICES_DIR/test_builder_api.py" ]; then
    check_pass "test_builder_api.py is executable"
else
    check_warn "test_builder_api.py is not executable"
    chmod +x "$SERVICES_DIR/test_builder_api.py"
    check_pass "Made test_builder_api.py executable"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "  1. Start the API:"
echo "     cd $SERVICES_DIR"
echo "     ./start-builder-api.sh"
echo ""
echo "  2. In another terminal, run tests:"
echo "     cd $SERVICES_DIR"
echo "     ./test_builder_api.py"
echo ""
echo "  3. Check API is running:"
echo "     curl http://localhost:9000/health"
echo ""
echo "  4. View Prometheus metrics:"
echo "     curl http://localhost:9000/api/v1/metrics"
echo ""
