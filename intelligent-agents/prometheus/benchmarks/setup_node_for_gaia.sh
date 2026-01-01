#!/bin/bash
# Setup script to prepare a cluster node for GAIA benchmark execution
# Run this on each node: mac-studio, macbook-air, macbook-pro, macpro51

set -e

echo "=============================================="
echo "GAIA Benchmark Node Setup"
echo "=============================================="

# Detect node and storage path
source /Volumes/SSDRAID0/agentic-system/scripts/detect-storage.sh 2>/dev/null || \
source /home/marc/agentic-system/scripts/detect-storage.sh 2>/dev/null || \
source ~/agentic-system/scripts/detect-storage.sh 2>/dev/null

if [ -z "$STORAGE_BASE" ]; then
    echo "ERROR: Could not detect storage path"
    exit 1
fi

echo "Node: $(hostname)"
echo "Storage: $STORAGE_BASE"
echo ""

# Step 1: Check Python version
echo "[1/5] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "Python version: $PYTHON_VERSION"

# Step 2: Install core dependencies
echo ""
echo "[2/5] Installing core dependencies..."
pip3 install --upgrade pip --quiet

# GAIA benchmark specific dependencies
pip3 install --quiet \
    anthropic>=0.40.0 \
    datasets>=2.18.0 \
    sentence-transformers>=2.3.0 \
    huggingface_hub>=0.20.0 \
    psutil>=6.1.0 \
    python-dotenv>=1.0.0

echo "Core dependencies installed"

# Step 3: Verify HuggingFace access
echo ""
echo "[3/5] Testing HuggingFace dataset access..."
python3 -c "
from datasets import load_dataset
try:
    ds = load_dataset('gaia-benchmark/GAIA', 'validation', trust_remote_code=True)
    print(f'✓ GAIA dataset accessible: {len(ds)} tasks in validation split')
except Exception as e:
    print(f'✗ Dataset access failed: {e}')
    print('  You may need to: huggingface-cli login')
    exit(1)
"

# Step 4: Check Claude CLI
echo ""
echo "[4/5] Checking Claude CLI..."
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo "✓ Claude CLI installed: $CLAUDE_VERSION"

    # Test headless mode (requires Max account)
    echo "  Testing headless mode..."
    TEST_RESULT=$(claude -p "Say 'ready'" --output-format json 2>/dev/null | head -1 || echo "")
    if echo "$TEST_RESULT" | grep -q "ready"; then
        echo "✓ Claude CLI headless mode working"
    else
        echo "⚠ Claude CLI may not be authenticated for headless mode"
        echo "  Run: claude login"
    fi
else
    echo "✗ Claude CLI not found"
    echo "  Install: npm install -g @anthropic-ai/claude-code"
    echo "  Then: claude login"
fi

# Step 5: Verify benchmark can run
echo ""
echo "[5/5] Verifying benchmark setup..."
cd "$STORAGE_BASE/intelligent-agents/prometheus/benchmarks"

python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '../..')
from gaia_official_benchmark import GAIADatasetLoader, GAIABenchmarkRunner

loader = GAIADatasetLoader()
tasks = loader.load_tasks(split='validation', level=1, limit=1)
print(f'✓ Benchmark loadable: {len(tasks)} test task(s) accessible')
"

echo ""
echo "=============================================="
echo "Setup Complete!"
echo ""
echo "To run the benchmark:"
echo "  cd $STORAGE_BASE/intelligent-agents/prometheus/benchmarks"
echo "  python3 gaia_official_benchmark.py --level 1 --limit 10"
echo ""
echo "Full Level 1 benchmark (53 tasks):"
echo "  python3 gaia_official_benchmark.py --level 1 --limit 53"
echo "=============================================="
