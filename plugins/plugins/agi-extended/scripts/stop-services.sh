#!/bin/bash
# Stop Docker services for agi-extended

set -e

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Determine compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

cd "$PLUGIN_DIR/docker"

echo "Stopping AGI-Extended services..."
$COMPOSE_CMD down

echo "Services stopped."
