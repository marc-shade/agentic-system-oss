#!/bin/bash
# Exo Cluster Node Setup Script
# Run this on each Mac to join the distributed inference cluster

set -e

echo "=== Exo Cluster Node Setup ==="
echo ""

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is for macOS only"
    exit 1
fi

# Check architecture
ARCH=$(uname -m)
echo "Architecture: $ARCH"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    echo "Install with: brew install python3"
    exit 1
fi

echo "Python: $(python3 --version)"

# Install exo
echo ""
echo "=== Installing Exo ==="
pip3 install --upgrade exo-ai

# Verify installation
if ! command -v exo &> /dev/null; then
    # Try finding it in common locations
    EXO_PATH=$(python3 -c "import site; print(site.USER_BASE + '/bin/exo')" 2>/dev/null)
    if [[ -f "$EXO_PATH" ]]; then
        echo "Exo installed at: $EXO_PATH"
        echo "Add to PATH: export PATH=\"\$PATH:$(dirname $EXO_PATH)\""
    else
        echo "Warning: exo not in PATH, but may be installed"
    fi
fi

# Create model cache directory on external drive if available
echo ""
echo "=== Configuring Model Storage ==="
if [[ -d "/Volumes/SSDRAID0" ]]; then
    mkdir -p /Volumes/SSDRAID0/.exo/models
    mkdir -p /Volumes/SSDRAID0/.cache/exo

    # Create symlinks
    mkdir -p ~/.exo
    if [[ ! -L ~/.exo/models ]]; then
        rm -rf ~/.exo/models 2>/dev/null
        ln -s /Volumes/SSDRAID0/.exo/models ~/.exo/models
        echo "Linked ~/.exo/models -> /Volumes/SSDRAID0/.exo/models"
    fi

    mkdir -p ~/.cache
    if [[ ! -L ~/.cache/exo ]]; then
        rm -rf ~/.cache/exo 2>/dev/null
        ln -s /Volumes/SSDRAID0/.cache/exo ~/.cache/exo
        echo "Linked ~/.cache/exo -> /Volumes/SSDRAID0/.cache/exo"
    fi
else
    echo "No SSDRAID0 found - models will be stored in ~/.exo/models"
fi

# Get system info
echo ""
echo "=== System Info ==="
echo "Hostname: $(hostname)"
echo "Model: $(sysctl -n hw.model 2>/dev/null || echo 'unknown')"
MEM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}')
echo "Memory: ${MEM_GB}GB unified"

# Estimate max model size (roughly 80% of RAM for safety)
MAX_MODEL_GB=$((MEM_GB * 80 / 100))
echo "Max model size (estimate): ~${MAX_MODEL_GB}GB"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start Exo and join the cluster:"
echo "  exo"
echo ""
echo "Web UI will be available at: http://localhost:52415"
echo ""
echo "Nodes auto-discover each other on the same network."
echo "No manual configuration needed!"
echo ""
echo "Recommended models for ${MEM_GB}GB RAM:"
if [[ $MEM_GB -ge 128 ]]; then
    echo "  - llama-3.3-70b (4-bit) - Full 70B model"
    echo "  - deepseek-v3 - With multi-node clustering"
elif [[ $MEM_GB -ge 64 ]]; then
    echo "  - llama-3.3-70b (4-bit) - May fit"
    echo "  - llama-3.1-70b (4-bit)"
elif [[ $MEM_GB -ge 32 ]]; then
    echo "  - llama-3.1-8b"
    echo "  - deepseek-r1-distill-qwen-7b"
    echo "  - deepseek-r1-distill-llama-8b"
else
    echo "  - llama-3.2-1b"
    echo "  - llama-3.2-3b"
    echo "  - deepseek-r1-distill-qwen-1.5b"
fi
