# Builder Node System Catalog

**Node ID**: macpro51
**Node Type**: builder
**Node Role**: construction_deployment
**Last Updated**: 2025-11-14 08:56:00

---

## Quick Reference

```bash
# Port awareness
ports              # List all ports
ports-agentic      # Show agentic ports only
ports-check        # Check required ports
ports-suggest      # Firewall suggestions

# Node status
curl http://localhost:9000/api/v1/status | jq .
python3 ~/agentic-system/intelligent-self-healing/intelligent_statusline.py
```

---

## Network Ports (Active Services)

### Agentic Services (Critical)

| Port | Service | Process | Access | Status | Purpose |
|------|---------|---------|--------|--------|---------|
| 5678 | n8n | docker-proxy | Network | Running | Workflow automation |
| 6333 | Qdrant REST | docker-proxy | Network | ⚠️ REQUIRED | Vector database API |
| 6334 | Qdrant gRPC | docker-proxy | Network | ⚠️ REQUIRED | Vector database gRPC |
| 6379 | Redis | docker-proxy | Network | ⚠️ REQUIRED | Key-value store |
| 8888 | Hardware Info | python3 | Network | Running | Hardware monitoring API |
| 9000 | Builder Node API | python3 | Network | ⚠️ REQUIRED | Orchestrator control |
| 11434 | Ollama | ollama | Network | ⚠️ REQUIRED | Local AI models |

### Remote Access

| Port | Service | Process | Access | Status | Purpose |
|------|---------|---------|--------|--------|---------|
| 22 | SSH | sshd | Network | ⚠️ REQUIRED | Secure shell |
| 23 | Telnet | systemd | Network | Running | Legacy access |
| 3389 | RDP | gnome-remote-desktop | Network | Running | Remote desktop |
| 3390 | RDP Alt | gnome-remote-desktop | Network | Running | Alt RDP port |

### File Sharing

| Port | Service | Process | Access | Status | Purpose |
|------|---------|---------|--------|--------|---------|
| 139 | SMB/NetBIOS | smbd | Network | ⚠️ REQUIRED | Samba NetBIOS |
| 445 | SMB/CIFS | smbd | Network | ⚠️ REQUIRED | File sharing |

### Monitoring & Office

| Port | Service | Process | Access | Status | Purpose |
|------|---------|---------|--------|--------|---------|
| 19999 | Netdata | netdata | Network | Running | System monitoring |
| 9980 | Collabora Online | coolwsd | Network | Running | Office suite |
| 9982 | Collabora Admin | coolwsd | Network | Running | Admin console |

---

## Docker Containers

| Container | Image | Ports | Status | Purpose |
|-----------|-------|-------|--------|---------|
| redis | redis:latest | 6379 | Running | Cache, pub/sub, queue |
| qdrant | qdrant/qdrant | 6333, 6334 | Running | Vector similarity search |
| n8n | n8nio/n8n | 5678 | Running | Workflow automation |

**Management**:
```bash
docker ps
docker logs redis
docker logs qdrant
docker logs n8n
```

---

## MCP Servers (7 Active)

| Server | Type | Purpose | Status |
|--------|------|---------|--------|
| enhanced-memory | Memory | Compressed entity storage | ✅ Active |
| agent-runtime | Task Management | Goals, tasks, queue | ✅ Active |
| safla | Embeddings | Fast embedding generation | ✅ Active |
| agi-mcp | AGI Research | Research & learning tools | ✅ Active |
| research-paper | Research | arXiv, Semantic Scholar | ✅ Active |
| video-transcript | Knowledge | YouTube transcript analysis | ✅ Active |
| ember | Conscience | Production-only policy | ✅ Active |

**Configuration**: `~/.claude.json`

---

## Claude Code Hooks (8 Configured)

| Hook | Matcher | Purpose | Script |
|------|---------|---------|--------|
| SessionStart | - | Initialize session | `session-start.sh` |
| SessionEnd | - | Cleanup | `session-end.sh` |
| PreToolUse | `*` | Safety checks, context load | `pre-tool-use.sh` |
| PostToolUse | `*` | Track tool completion | `post-tool-use.sh` |
| Stop | - | Memory consolidation | `stop.sh` |
| SubagentStop | - | Subagent learning | `subagent-stop.sh` |
| UserPromptSubmit | - | Intent classification | `user-prompt-submit.sh` |
| PreCompact | - | Context preservation | `pre-compact.sh` |

**Configuration**: `~/.claude/settings.json`
**Scripts**: `/home/marc/agentic-system/scripts/hooks/`

---

## Storage

### RAID10 Array

**Device**: /dev/md0
**Type**: RAID10 (4x NVMe drives)
**Capacity**: 931GB usable
**Status**: `[UUUU]` (all drives healthy)
**Mount**: `/mnt/agentic-system`
**Auto-assembly**: ✅ Enabled (mdraid initramfs)

```bash
# Check RAID status
cat /proc/mdstat
mdadm --detail /dev/md0

# Monitor
watch -n 1 cat /proc/mdstat
```

### Key Directories

| Path | Purpose | Size |
|------|---------|------|
| `/mnt/agentic-system/` | Main agentic storage | RAID10 |
| `~/agentic-system/` | Symlink to above | - |
| `~/.claude/` | Claude Code config | Local |
| `~/.claude/enhanced_memories/` | Memory database | Local |
| `~/agentic-system/logs/` | All service logs | RAID10 |
| `~/agentic-system/scripts/` | Management scripts | RAID10 |
| `~/agentic-system/services/` | Service implementations | RAID10 |

---

## Systemd Services (Auto-Start)

### Critical Services

| Service | Status | Purpose |
|---------|--------|---------|
| avahi-daemon.service | ✅ Enabled | mDNS discovery |
| sshd.service | ✅ Enabled | SSH access |
| smb.service | ✅ Enabled | Samba file sharing |
| nmb.service | ✅ Enabled | NetBIOS name service |
| firewalld.service | ✅ Enabled | Firewall |
| builder-node-api.service | ✅ Enabled | Orchestrator API |
| agentic-memory-db.service | ✅ Enabled | Memory database |
| docker.service | ✅ Enabled | Container runtime |

```bash
# Check all services
systemctl list-units --type=service --state=running | grep -E "avahi|ssh|smb|builder|memory|docker"

# Service status
~/agentic-system/agentic-system-status.sh
```

---

## Network Configuration

### Interfaces

| Interface | Type | IP Address | Status |
|-----------|------|------------|--------|
| enp20s0 | Ethernet | 192.168.1.183 | Active |
| wls5 | WiFi | 192.168.1.87 | Active |
| docker0 | Bridge | 172.17.0.1 | Active |

### mDNS Names

- `macpro51.local` (primary)
- `Agentic Builder Node - macpro51` (service name)

### Firewall Rules

**Active Zone**: public
**Open Ports**: 1025-65535/tcp, 1025-65535/udp
**Note**: All high ports open (including all agentic services)

```bash
# Check firewall
sudo firewall-cmd --list-all
sudo firewall-cmd --list-ports

# Manage ports
port-open PORT [tcp|udp]
port-close PORT [tcp|udp]
```

---

## API Endpoints

### Builder Node API (Port 9000)

Base URL: `http://macpro51.local:9000`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/status` | GET | Comprehensive status |
| `/api/v1/builder` | GET | Builder info |
| `/api/v1/capabilities` | GET | Node capabilities |
| `/api/v1/control/execute` | POST | Execute commands |
| `/api/v1/control/status` | POST | Control status |

```bash
# Test endpoints
curl http://localhost:9000/api/v1/health | jq .
curl http://localhost:9000/api/v1/status | jq .
```

---

## Logs

### Location: `~/agentic-system/logs/`

| Log File | Purpose | Source |
|----------|---------|--------|
| `claude-sessions.log` | Session lifecycle | Hooks |
| `tool-usage.log` | Tool execution | PreToolUse/PostToolUse |
| `file-operations.log` | File operations | PreToolUse |
| `safety-warnings.log` | Dangerous commands | PreToolUse |
| `intents.log` | User intent classification | UserPromptSubmit |
| `subagent-activity.log` | Subagent executions | SubagentStop |
| `compaction-events.log` | Context compaction | PreCompact |
| `builder-node-api.log` | API requests | Builder API |

```bash
# Tail logs
tail -f ~/agentic-system/logs/claude-sessions.log
tail -f ~/agentic-system/logs/builder-node-api.log

# View all recent activity
journalctl -f
```

---

## Memory Systems

### Enhanced Memory

**Database**: `~/.claude/enhanced_memories/memory.db`
**Type**: SQLite with compression
**Entities**: 7 stored
**Compression**: 61.46% average
**Tiers**: Working, Episodic, Semantic, Procedural

```bash
# Check memory status
sqlite3 ~/.claude/enhanced_memories/memory.db "SELECT COUNT(*) FROM entities;"

# Memory curation (automatic via Stop hook every 5+ minutes)
# Or manual via MCP: mcp__enhanced-memory__autonomous_memory_curation
```

### SAFLA Embeddings

**Type**: Ultra-fast embedding engine
**Performance**: 1.75M+ ops/sec
**Purpose**: Vector similarity, RAG

---

## Hardware

**Platform**: Mac Pro 5,1 (Mid 2010)
**CPU**: Dual Intel Xeon
**RAM**: High capacity
**Storage**:
- RAID10: 4x 512GB NVMe (931GB usable)
- Boot SSD: System drive

**Monitoring**:
```bash
# CPU/Memory
htop
sensors

# RAID status
cat /proc/mdstat

# Disk usage
df -h /mnt/agentic-system

# Network monitoring
http://macpro51.local:19999  # Netdata dashboard
```

---

## Key Scripts & Tools

| Script | Purpose | Location |
|--------|---------|----------|
| `port-manager.py` | Port tracking & firewall | `~/agentic-system/scripts/` |
| `intelligent_statusline.py` | Statusline display | `~/agentic-system/intelligent-self-healing/` |
| `agentic-system-status.sh` | System health check | `~/` |
| `test-boot-sequence.sh` | Boot verification | `~/` |
| `builder-node-api.py` | Orchestrator API server | `~/agentic-system/services/` |
| `memory-status-check.sh` | Memory status | `~/agentic-system/scripts/statusline/` |

---

## Environment Variables

**Session File**: `/tmp/claude_session_start.json`
**Memory Status**: `/tmp/memory-status-check.sh` (symlink)
**Last Curation**: `/tmp/last_memory_curation`

---

## Orchestrator Integration

### Discovery

The Builder node announces itself via Avahi/mDNS:

```
Service: _agentic-builder._tcp
Port: 9000
TXT Records:
  - node_id=macpro51
  - node_type=builder
  - node_role=construction_deployment
  - orchestrator_ready=true
  - capabilities=claude_code,hooks,mcp_servers,enhanced_memory,docker,raid10
```

### Control Protocol

**Health Check**:
```bash
GET http://macpro51.local:9000/api/v1/health
```

**Task Assignment**:
```bash
POST http://macpro51.local:9000/api/v1/control/execute
Content-Type: application/json

{
  "command": "status",
  "task_type": "monitoring"
}
```

**Status Query**:
```bash
GET http://macpro51.local:9000/api/v1/status
```

---

## Security

### Command Blocking

PreToolUse hook blocks extremely dangerous commands:
- `rm -rf /` (root deletion)
- `dd of=/dev/sd*` (raw disk writes)
- `mkfs`, `fdisk`, `parted` on physical disks

**Logs**: `~/agentic-system/logs/safety-warnings.log`

### API Security

- Network: Internal network only (192.168.1.x)
- Commands: Restricted to safe patterns
- No external internet exposure

### Access Control

- SSH: Port 22 (key-based recommended)
- SMB: User authentication required
- API: Currently unauthenticated (local network only)

---

## Troubleshooting

### Node Not Responding

```bash
# Check Builder API
systemctl status builder-node-api.service
curl http://localhost:9000/api/v1/health

# Check Avahi
systemctl status avahi-daemon
avahi-browse -a -t | grep macpro51

# Check network
ip addr show
ping -c 3 192.168.1.1
```

### Port Conflicts

```bash
# List all listening ports
ports

# Check specific port
sudo lsof -i :9000
ss -tuln | grep 9000

# Kill process on port
sudo kill $(sudo lsof -t -i:9000)
```

### RAID Issues

```bash
# Check RAID status
cat /proc/mdstat
mdadm --detail /dev/md0

# Rebuild if needed
sudo mdadm --re-add /dev/md0 /dev/nvmeXnY
```

### Memory Database Issues

```bash
# Check service
systemctl status agentic-memory-db.service

# Check database
ls -lh ~/.claude/enhanced_memories/memory.db
sqlite3 ~/.claude/enhanced_memories/memory.db ".tables"
```

---

## Quick Commands Reference

```bash
# System status
~/agentic-system-status.sh

# Port awareness
ports-agentic
ports-check

# Service management
systemctl status builder-node-api.service
sudo systemctl restart builder-node-api.service

# Docker management
docker ps
docker stats
docker logs -f redis

# RAID monitoring
watch cat /proc/mdstat

# Network discovery
avahi-browse -a -t

# Claude status
python3 ~/agentic-system/intelligent-self-healing/intelligent_statusline.py

# Memory stats
curl http://localhost:9000/api/v1/status | jq '.mcp_servers, .hooks'
```

---

## External Access URLs

**From any node on network**:

- Builder API: `http://macpro51.local:9000/api/v1/`
- Netdata: `http://macpro51.local:19999/`
- n8n: `http://macpro51.local:5678/`
- Ollama: `http://macpro51.local:11434/`
- Collabora: `http://macpro51.local:9980/`

**SSH**: `ssh marc@macpro51.local`
**SMB**: `smb://macpro51.local/marc`

---

## Node Capabilities (Advertised)

```
claude_code                  # Claude Code installation with hooks
hooks_8_configured           # 8/10 hooks active
mcp_servers                  # 7 MCP servers integrated
enhanced_memory              # Compressed entity storage
docker_containers            # Redis, Qdrant, n8n
raid10_storage               # 931GB high-performance storage
ollama_ai                    # Local AI model serving
ssh_access                   # Remote shell access
smb_file_sharing             # Network file sharing
avahi_discovery              # mDNS service discovery
hardware_monitoring          # Netdata + sensors
autonomous_memory_curation   # Self-improving memory
dangerous_command_blocking   # Safety checks
intent_classification        # User intent analysis
session_tracking             # Session continuity
```

---

**This catalog is automatically exportable for other nodes:**

```bash
# Export to JSON for orchestrator
python3 ~/agentic-system/scripts/port-manager.py export

# Serve catalog via API
curl http://macpro51.local:9000/api/v1/status > system-catalog.json
```

---

*Last Updated: 2025-11-14 08:56:00*
*Node: macpro51 (Builder)*
*Status: Fully Operational*
