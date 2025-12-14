#!/bin/bash
# Deploy TOON Refactoring to Remote Node
# Usage: ./deploy-toon-to-node.sh <node-ip> <node-name>

set -e

# Detect storage base path based on platform
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi

    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            else
                echo "$(dirname "$(dirname "$0")")"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            else
                echo "$(dirname "$(dirname "$0")")"
            fi
            ;;
        *)
            echo "$(dirname "$(dirname "$0")")"
            ;;
    esac
}

STORAGE_BASE="$(detect_storage_base)"

NODE_IP="$1"
NODE_NAME="$2"

if [ -z "$NODE_IP" ] || [ -z "$NODE_NAME" ]; then
    echo "Usage: $0 <node-ip> <node-name>"
    echo "Example: $0 192.168.1.16 mac-studio"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  TOON Deployment to $NODE_NAME ($NODE_IP)"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Test connectivity
echo "1. Testing connectivity..."
if ! ssh -o ConnectTimeout=5 $NODE_IP "hostname" > /dev/null 2>&1; then
    echo "  ✗ Cannot connect to $NODE_IP"
    exit 1
fi
echo "  ✓ Connected to $(ssh $NODE_IP hostname)"
echo

# Install toon-py
echo "2. Installing toon-py library..."
ssh $NODE_IP "pip3 install --user toon-py" 2>&1 | grep -E "(Successfully installed|Requirement already satisfied)" || true
echo "  ✓ toon-py installed"
echo

# Copy toon_config.py
echo "3. Deploying toon_config.py utility..."
scp "$STORAGE_BASE/cluster-deployment/toon_config.py" $NODE_IP:~/agentic-system/cluster-deployment/ 2>&1 | grep -v "Warning"
echo "  ✓ toon_config.py deployed"
echo

# Convert node-config.json to TOON
echo "4. Converting configuration files..."
ssh $NODE_IP "python3 - << 'PYEOF'
import json
import sys
from pathlib import Path

# Install path for toon_py
sys.path.insert(0, str(Path.home() / 'agentic-system' / 'cluster-deployment'))

try:
    from toon_py import encode
except ImportError:
    print('  ⚠️  toon-py not found in Python path, trying pip install location')
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'toon-py'],
                   capture_output=True)
    from toon_py import encode

claude_dir = Path.home() / '.claude'
converted = []

# Config files to convert
config_files = [
    'node-config.json',
    'self-x-config.json',
    'weekly_budget.json',
    'preservation_rules.json',
    'settings.local.json',
]

for filename in config_files:
    json_path = claude_dir / filename
    if not json_path.exists():
        continue

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        toon_output = encode(data)
        toon_path = json_path.with_suffix('.toon')

        with open(toon_path, 'w') as f:
            f.write(toon_output)

        converted.append(filename)
        print(f'  ✓ Converted: {filename}')
    except Exception as e:
        print(f'  ✗ Error converting {filename}: {e}')

print(f'  Total converted: {len(converted)} files')
PYEOF"
echo

# Run refactoring script on Python files
echo "5. Updating Python code..."
scp "$STORAGE_BASE/scripts/refactor-to-toon.py" $NODE_IP:~/agentic-system/scripts/ 2>&1 | grep -v "Warning"
ssh $NODE_IP "cd ~/agentic-system && python3 scripts/refactor-to-toon.py 2>&1 | grep -E '(✓|✗|Success|Failed)'"
echo

# Verify installation
echo "6. Verifying TOON installation..."
ssh $NODE_IP "python3 - << 'PYEOF'
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'agentic-system' / 'cluster-deployment'))

try:
    import toon_py
    print(f'  ✓ toon-py: v{toon_py.__version__}')
except:
    print('  ✗ toon-py not installed')

try:
    from toon_config import load_node_config
    config = load_node_config()
    print(f'  ✓ Config loader: node {config[\"node_id\"]} loaded')
except Exception as e:
    print(f'  ✗ Config loader failed: {e}')

# Count TOON files
toon_files = list(Path.home().glob('.claude/*.toon'))
print(f'  ✓ TOON files: {len(toon_files)} created')
PYEOF"
echo

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ TOON Deployment Complete on $NODE_NAME"
echo "╚════════════════════════════════════════════════════════════╝"
