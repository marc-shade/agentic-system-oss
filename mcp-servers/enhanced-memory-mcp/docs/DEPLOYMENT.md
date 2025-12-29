# Enhanced Memory MCP - Deployment Guide

## Prerequisites

### Required Services
- **Python 3.11+**
- **Qdrant** vector database (port 6333)
- **Redis** (optional, for distributed caching)
- **SQLite** (bundled, for local storage)

### Hardware Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 10 GB SSD | 50+ GB NVMe |
| Network | 100 Mbps | 1 Gbps |

## Installation

### Method 1: pip (Recommended)
```bash
pip install enhanced-memory-mcp
```

### Method 2: From Source
```bash
git clone https://github.com/marc-shade/enhanced-memory-mcp.git
cd enhanced-memory-mcp
pip install -e .
```

### Method 3: Docker
```bash
docker pull marcshade/enhanced-memory-mcp:latest
docker run -p 8765:8765 \
  -v ~/.claude/enhanced_memories:/data \
  marcshade/enhanced-memory-mcp:latest
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_DIR` | `~/.claude/enhanced_memories` | Data storage directory |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL (optional) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding provider |
| `TPU_ENABLED` | `false` | Enable Coral TPU scoring |
| `MAX_MEMORY_SIZE_MB` | `1024` | Maximum memory database size |

### Claude Code Integration

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python",
      "args": ["-m", "enhanced_memory_mcp.server"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Standalone Server

```bash
# Start with defaults
python -m enhanced_memory_mcp.server

# Custom configuration
python -m enhanced_memory_mcp.server \
  --port 8765 \
  --host 0.0.0.0 \
  --memory-dir /data/memories
```

## Qdrant Setup

### Docker Compose
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

volumes:
  qdrant_data:
```

### Collection Initialization
The server automatically creates required collections on first run:
- `enhanced_memory` - Main entity storage
- `nmf_memories` - Neural Memory Fabric
- `reasoning_bank` - ReasoningBank storage

## High Availability Setup

### Multi-Node Deployment
```yaml
# docker-compose-ha.yaml
version: '3.8'
services:
  memory-primary:
    image: marcshade/enhanced-memory-mcp:latest
    environment:
      - NODE_ROLE=primary
      - REDIS_URL=redis://redis:6379
    depends_on:
      - qdrant
      - redis

  memory-replica:
    image: marcshade/enhanced-memory-mcp:latest
    environment:
      - NODE_ROLE=replica
      - PRIMARY_URL=http://memory-primary:8765
    depends_on:
      - memory-primary

  qdrant:
    image: qdrant/qdrant:latest

  redis:
    image: redis:7-alpine
```

### Load Balancer Configuration (nginx)
```nginx
upstream memory_cluster {
    least_conn;
    server memory-1:8765;
    server memory-2:8765;
    server memory-3:8765;
}

server {
    listen 8765;
    location / {
        proxy_pass http://memory_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Performance Tuning

### Embedding Cache
```bash
# Pre-warm embedding cache
python -m enhanced_memory_mcp.tools.cache_warmer \
  --queries "common queries file.txt" \
  --limit 1000
```

### Database Optimization
```sql
-- Run periodically for SQLite optimization
VACUUM;
ANALYZE;
PRAGMA optimize;
```

### Qdrant Optimization
```bash
# Optimize collection indexes
curl -X POST 'http://localhost:6333/collections/enhanced_memory/index' \
  -H 'Content-Type: application/json' \
  -d '{"field_name": "entity_type", "field_schema": "keyword"}'
```

## Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8765/health
# Returns: {"status": "healthy", "version": "1.0.0", ...}
```

### Prometheus Metrics
Enable with `--metrics-port 9090`:
- `memory_entities_total` - Total entity count
- `memory_search_latency_seconds` - Search latency histogram
- `memory_compression_ratio` - Compression efficiency
- `cache_hit_rate` - Semantic cache hit rate

### Logging
Logs are written to `server.log` in the server directory:
```bash
tail -f /path/to/enhanced-memory-mcp/server.log
```

## Backup and Recovery

### Automated Backup
```bash
#!/bin/bash
# backup.sh - Run daily via cron
BACKUP_DIR="/backups/memory/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# SQLite database
sqlite3 ~/.claude/enhanced_memories/memory.db ".backup '$BACKUP_DIR/memory.db'"

# Qdrant snapshots
curl -X POST "http://localhost:6333/collections/enhanced_memory/snapshots"
```

### Recovery
```bash
# Restore SQLite
cp /backups/memory/20250129/memory.db ~/.claude/enhanced_memories/

# Restore Qdrant
curl -X PUT "http://localhost:6333/collections/enhanced_memory/snapshots/recover" \
  -d '{"location": "/backups/qdrant/snapshot.tar"}'
```

## Security

### Authentication (Recommended for Production)
```bash
# Generate API key
python -m enhanced_memory_mcp.tools.generate_key > api_key.txt

# Start with auth enabled
python -m enhanced_memory_mcp.server --require-auth --auth-key-file api_key.txt
```

### Network Security
- Run behind reverse proxy (nginx/traefik)
- Use TLS for all connections
- Restrict access via firewall rules
- Enable rate limiting

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
