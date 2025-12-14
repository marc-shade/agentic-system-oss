#!/bin/bash
# Install and configure the Autonomous Cognitive Daemon
# Run as: sudo ./scripts/install.sh

set -e


# Platform-aware storage detection
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
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$PROJECT_DIR/systemd/acd.service"
SYSTEMD_DIR="/etc/systemd/system"
VENV_DIR="$STORAGE_BASE/.venv"

echo "=========================================="
echo "  Autonomous Cognitive Daemon Installer"
echo "=========================================="
echo ""

# Check if running as root for systemd operations
if [ "$EUID" -ne 0 ]; then
    echo "Note: Run with sudo to install systemd service"
    INSTALL_SERVICE=false
else
    INSTALL_SERVICE=true
fi

# Install Python package
echo "[1/4] Installing Python package..."
cd "$PROJECT_DIR"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    pip install -e . --quiet
    echo "      Package installed in $VENV_DIR"
else
    echo "      Warning: Virtual environment not found at $VENV_DIR"
    echo "      Installing in current environment..."
    pip install -e . --quiet
fi

# Create required directories
echo "[2/4] Creating directories..."
mkdir -p $STORAGE_BASE/session-briefings
mkdir -p /var/log/acd
echo "      Created session-briefings and log directories"

# Install systemd service
if [ "$INSTALL_SERVICE" = true ]; then
    echo "[3/4] Installing systemd service..."
    cp "$SERVICE_FILE" "$SYSTEMD_DIR/acd.service"
    systemctl daemon-reload
    echo "      Service installed"
else
    echo "[3/4] Skipping systemd installation (requires sudo)"
fi

# Verify installation
echo "[4/4] Verifying installation..."
if python -c "import acd; print(f'      ACD version: {acd.__version__}')" 2>/dev/null; then
    echo "      Installation verified!"
else
    echo "      Warning: Could not verify installation"
fi

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "To start the daemon:"
echo "  sudo systemctl start acd"
echo ""
echo "To enable on boot:"
echo "  sudo systemctl enable acd"
echo ""
echo "To check status:"
echo "  sudo systemctl status acd"
echo "  journalctl -u acd -f"
echo ""
echo "To run manually:"
echo "  source $STORAGE_BASE/.venv/bin/activate"
echo "  acd"
echo ""
