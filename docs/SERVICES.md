# Agentic System Services

This document describes optional background services that enhance the agentic system.

## Service Overview

The agentic system can run standalone, but these services provide additional capabilities:

| Service | Purpose | Required | Default Port |
|---------|---------|----------|--------------|
| Qdrant | Vector database for semantic search | Optional | 6333/6334 |
| Redis | Caching and pub/sub | Optional | 6379 |

## Qdrant (Vector Database)

Qdrant provides semantic search capabilities for the enhanced-memory MCP server.

### Installation

**Docker (recommended):**
```bash
docker run -d --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant
```

**Podman (Linux):**
```bash
podman run -d --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v ./data/qdrant:/qdrant/storage:Z \
  qdrant/qdrant
```

**Binary installation:**
```bash
# Download from https://github.com/qdrant/qdrant/releases
wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-$(uname -s)-$(uname -m).tar.gz
tar xzf qdrant-*.tar.gz
./qdrant --config-path config/qdrant-config.yaml
```

### Configuration

Create `config/qdrant-config.yaml`:
```yaml
storage:
  storage_path: ./data/qdrant

service:
  http_port: 6333
  grpc_port: 6334

log_level: INFO
```

### Health Check

```bash
curl http://localhost:6333/health
# Expected: {"status":"ok"}
```

### Environment Variables

Set these to enable Qdrant integration:
```bash
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_API_KEY=  # Optional, for cloud deployments
```

## Redis (Caching)

Redis provides optional caching for improved performance.

### Installation

**Docker:**
```bash
docker run -d --name redis \
  -p 6379:6379 \
  -v $(pwd)/data/redis:/data \
  redis:alpine redis-server --appendonly yes
```

**Homebrew (macOS):**
```bash
brew install redis
brew services start redis
```

**Package manager (Linux):**
```bash
# Fedora/RHEL
sudo dnf install redis
sudo systemctl enable --now redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

### Environment Variables

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=  # Optional
```

## Running Without Services

The system works without these services with reduced functionality:

- **Without Qdrant**: Memory search uses local SQLite with basic text matching
- **Without Redis**: No caching, slightly slower repeated operations

## Systemd Service Files (Linux)

### Qdrant Service

Create `/etc/systemd/system/qdrant.service`:
```ini
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=marc
WorkingDirectory=/home/marc/agentic-system
ExecStart=/usr/local/bin/qdrant --config-path config/qdrant-config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qdrant
```

## LaunchAgent (macOS)

### Qdrant Launch Agent

Create `~/Library/LaunchAgents/com.agentic.qdrant.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic.qdrant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/qdrant</string>
        <string>--config-path</string>
        <string>/Volumes/SSDRAID0/agentic-system/config/qdrant-config.yaml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/qdrant.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/qdrant.error.log</string>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.agentic.qdrant.plist
```

## Docker Compose (All Services)

Create `docker-compose.yml` in your installation directory:
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
```

Start all services:
```bash
docker compose up -d
```

## Service Status Check

Run the health check script to verify services:
```bash
python3 scripts/health_check.py
```

Or manually check:
```bash
# Qdrant
curl -s http://localhost:6333/health | jq .

# Redis
redis-cli ping
# Expected: PONG
```

## Troubleshooting

### Qdrant won't start
- Check port 6333/6334 availability: `lsof -i :6333`
- Verify storage directory permissions
- Check logs: `docker logs qdrant` or system logs

### Redis connection refused
- Verify Redis is running: `systemctl status redis` or `brew services list`
- Check if bound to localhost only vs all interfaces
- Test connection: `redis-cli -h localhost ping`

### Memory issues
- Qdrant: Adjust `max_memory_mb` in config
- Redis: Set `maxmemory` directive

## Cloud Alternatives

For production deployments, consider managed services:

- **Qdrant Cloud**: https://cloud.qdrant.io
- **Redis Cloud**: https://redis.com/redis-enterprise-cloud/
- **AWS ElastiCache**: Redis-compatible
- **Upstash**: Serverless Redis

Set the appropriate environment variables for cloud endpoints.
