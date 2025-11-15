#!/bin/bash
# Install Monitoring Stack - Prometheus, Loki, Grafana

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "📊 Installing Monitoring Stack..."
echo "=================================="
echo ""

# Detect OS
OS=$(uname -s)

# Track what gets installed
INSTALLED=()

# === Prometheus ===
echo -e "${BLUE}1. Installing Prometheus...${NC}"
if command -v prometheus &> /dev/null; then
    echo -e "${YELLOW}⚠ Prometheus already installed${NC}"
    prometheus --version
else
    case "$OS" in
        Darwin)
            if command -v brew &> /dev/null; then
                brew install prometheus
                INSTALLED+=("prometheus")
            else
                echo -e "${RED}✗ Homebrew required for macOS${NC}"
            fi
            ;;
        Linux)
            # Download and install Prometheus
            PROM_VERSION="2.47.0"
            wget https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz
            tar xvfz prometheus-*.tar.gz
            sudo mv prometheus-${PROM_VERSION}.linux-amd64/prometheus /usr/local/bin/
            sudo mv prometheus-${PROM_VERSION}.linux-amd64/promtool /usr/local/bin/
            rm -rf prometheus-*
            INSTALLED+=("prometheus")
            ;;
    esac
fi

echo ""

# === Loki ===
echo -e "${BLUE}2. Installing Loki...${NC}"
if command -v loki &> /dev/null; then
    echo -e "${YELLOW}⚠ Loki already installed${NC}"
    loki --version
else
    if command -v docker &> /dev/null; then
        echo "Installing Loki via Docker..."
        docker run -d \
            --name loki \
            -p 9900:9900 \
            -p 9901:9901 \
            grafana/loki:latest
        INSTALLED+=("loki (docker)")
    elif [ "$OS" = "Darwin" ] && command -v brew &> /dev/null; then
        brew install loki
        INSTALLED+=("loki")
    else
        echo -e "${YELLOW}⚠ Skipping Loki - Docker or Homebrew required${NC}"
    fi
fi

echo ""

# === Grafana ===
echo -e "${BLUE}3. Installing Grafana...${NC}"
if command -v grafana-server &> /dev/null; then
    echo -e "${YELLOW}⚠ Grafana already installed${NC}"
    grafana-server --version
else
    case "$OS" in
        Darwin)
            if command -v brew &> /dev/null; then
                brew install grafana
                INSTALLED+=("grafana")
            fi
            ;;
        Linux)
            # Add Grafana APT repository
            sudo apt-get install -y apt-transport-https software-properties-common
            wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
            echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
            sudo apt-get update
            sudo apt-get install -y grafana
            INSTALLED+=("grafana")
            ;;
    esac
fi

echo ""
echo "=================================="
echo -e "${GREEN}✓ Monitoring Stack Installation Summary${NC}"
echo "=================================="

if [ ${#INSTALLED[@]} -gt 0 ]; then
    echo "Installed components:"
    for component in "${INSTALLED[@]}"; do
        echo "  ✓ $component"
    done
else
    echo "No new components installed (all already present)"
fi

echo ""
echo "Service Ports:"
echo "  Prometheus: 9700"
echo "  Loki:       9900 (HTTP), 9901 (gRPC)"
echo "  Grafana:    9500"
echo ""
echo "Note: Services are not started automatically."
echo "      Use the start scripts in monitoring/ directory"
