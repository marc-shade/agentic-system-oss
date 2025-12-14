#!/bin/bash
# Enable all agentic system services for auto-start on boot
# Run this script after creating/updating systemd units

set -e

echo "🚀 Enabling all agentic system services for auto-start..."
echo ""

# Enable user lingering so services persist after logout
echo "👤 Enabling user lingering (services persist after logout)..."
sudo loginctl enable-linger $USER

# Reload systemd user daemon
echo "📋 Reloading systemd user daemon..."
systemctl --user daemon-reload

# Core infrastructure containers
echo ""
echo "🐳 Enabling container services..."
systemctl --user enable redis.service
systemctl --user enable qdrant.service
systemctl --user enable n8n.service

# Monitoring stack (already in containers, just enable systemd management)
echo ""
echo "📊 Monitoring stack services (managed by existing containers)..."
systemctl --user enable prometheus.service
systemctl --user enable loki.service
systemctl --user enable grafana.service

# MCP servers
echo ""
echo "🔌 Enabling MCP servers..."
systemctl --user enable mcp-enhanced-memory.service
systemctl --user enable mcp-agent-runtime.service
systemctl --user enable mcp-ember.service
systemctl --user enable mcp-safla.service
systemctl --user enable mcp-cluster-execution.service
systemctl --user enable mcp-video-transcript.service
systemctl --user enable mcp-research-paper.service
systemctl --user enable mcp-agi.service

# Builder node services
echo ""
echo "🔨 Enabling builder node services..."
systemctl --user enable builder-api.service
systemctl --user enable builder-heartbeat.service
systemctl --user enable builder-task-queue.service

# Cluster services
echo ""
echo "🌐 Enabling cluster services..."
systemctl --user enable cluster-heartbeat.service

# Maintenance services
echo ""
echo "🧹 Enabling maintenance services..."
systemctl --user enable artifact-cleanup.service

# Kutira AI services (optional, only if needed)
echo ""
echo "🤖 Kutira AI services (will enable but may not start if not configured)..."
systemctl --user enable kutiraai-api.service || true
systemctl --user enable kutiraai-framework.service || true
systemctl --user enable kutiraai-frontend.service || true

echo ""
echo "✅ All services enabled for auto-start!"
echo ""
echo "To start all services now, run:"
echo "  $0 --start"
echo ""
echo "To check status:"
echo "  systemctl --user list-units --type=service --state=running | grep -E 'agentic|builder|mcp|redis|qdrant'"
echo ""

# If --start flag is provided, start all services
if [ "$1" == "--start" ]; then
    echo "🚀 Starting all services..."
    echo ""

    # Start in dependency order
    echo "Starting containers..."
    systemctl --user start redis.service
    systemctl --user start qdrant.service
    sleep 2

    echo "Starting MCP servers..."
    systemctl --user start mcp-enhanced-memory.service
    systemctl --user start mcp-agent-runtime.service
    systemctl --user start mcp-ember.service
    systemctl --user start mcp-safla.service
    systemctl --user start mcp-cluster-execution.service
    systemctl --user start mcp-video-transcript.service
    systemctl --user start mcp-research-paper.service
    systemctl --user start mcp-agi.service
    sleep 2

    echo "Starting builder services..."
    systemctl --user start builder-api.service
    systemctl --user start builder-heartbeat.service
    systemctl --user start builder-task-queue.service

    echo "Starting cluster services..."
    systemctl --user start cluster-heartbeat.service

    echo "Starting workflow automation..."
    systemctl --user start n8n.service

    echo ""
    echo "✅ All services started!"
    echo ""
    echo "Check status with:"
    echo "  systemctl --user status builder-api.service"
    echo "  systemctl --user status mcp-enhanced-memory.service"
fi
