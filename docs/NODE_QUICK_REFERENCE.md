# Node Quick Reference Card

**Generated**: 2025-12-13 | **Cluster Version**: 1.0.0

---

## At-a-Glance

| Node | Role | IP | OS | Chip | RAM | Status |
|------|------|----|----|------|-----|--------|
| mac-studio | Orchestrator | 192.168.1.16 | macOS | M2 Ultra | 192GB | Primary |
| macpro51 | Builder | 192.168.1.183 | Fedora 43 | 2x Xeon X5680 | 126GB | Active |
| macbook-air | Researcher | 192.168.1.76 | macOS | M3 | 24GB | Active |
| completeu-server | AI Inference | 192.168.1.186 | macOS | Apple Silicon | - | Active |
| macmini | Small Inference | 192.168.1.36 | macOS | M1 | 16GB | Active |
| bpi-sentinel | Sentinel | 192.168.1.234 | Linux | Allwinner H618 | 2GB | Active |

---

## Storage Paths by Node

```
mac-studio:       /Volumes/SSDRAID0/agentic-system/
macpro51:         /mnt/agentic-system/
macbook-air:      /Users/marc/agentic-system/
completeu-server: /Volumes/FILES/agentic-system/
macmini:          /Users/marc/agentic-system/
bpi-sentinel:     /home/marc/agentic-system/
```

---

## Quick Commands

### SSH to Any Node
```bash
ssh mac-studio      # Orchestrator
ssh macpro51        # Builder (this node)
ssh macbook-air     # Researcher
ssh completeu-server # AI Inference
ssh macmini         # Small Inference
ssh bpi-sentinel    # Sentinel
```

### Sync Files
```bash
# Push docs to mac-studio
rsync -avz /mnt/agentic-system/docs/ mac-studio:/Volumes/SSDRAID0/agentic-system/docs/

# Push docs to macbook-air
rsync -avz /mnt/agentic-system/docs/ macbook-air:/Users/marc/agentic-system/docs/

# Sync cluster config everywhere
for node in mac-studio macbook-air; do
  rsync -avz /mnt/agentic-system/cluster-deployment/ $node:~/agentic-system/cluster-deployment/
done
```

### Health Check All Nodes
```bash
for n in mac-studio macmini macbook-air completeu-server bpi-sentinel; do
  ping -c1 -W1 $n >/dev/null && echo "✓ $n" || echo "✗ $n"
done
```

---

## Service Ports

| Port | Service | Where |
|------|---------|-------|
| 445 | Samba | macpro51 |
| 6333 | Qdrant | all |
| 7233 | Temporal | mac-studio |
| 8233 | Temporal UI | mac-studio |
| 9000 | Builder API | macpro51 |
| 9500 | Grafana | all |
| 9700 | Prometheus | all |
| 11434 | Ollama | completeu-server |

---

## LLM Routing Policy

| Task Type | Route To | Why |
|-----------|----------|-----|
| Large LLM (>13B) | completeu-server | Dedicated inference |
| Small LLM (<13B) | macmini | M1 GPU |
| Embeddings | macpro51 (local) | CPU OK for embeddings |
| Fast inference | mac-studio | M2 Ultra MLX |
| Edge ML | macpro51 | Coral TPU |

**NEVER run LLM inference on macpro51 CPU** - use cluster nodes with GPUs.

---

## Node Capabilities Matrix

| Capability | mac-studio | macpro51 | macbook-air | completeu | macmini | bpi |
|------------|:----------:|:--------:|:-----------:|:---------:|:-------:|:---:|
| Orchestration | **Primary** | Failover | - | - | - | - |
| LLM Inference | M2 Ultra | TPU only | M3 | **Primary** | M1 | - |
| Compilation | - | **Primary** | - | - | - | - |
| Docker/Podman | - | **Primary** | - | - | - | - |
| Research | - | - | **Primary** | - | - | - |
| Monitoring | **Primary** | - | - | - | - | Sentinel |
| Arduino | **Primary** | - | - | - | - | - |

---

## Emergency Contacts

### If Node Unreachable
1. Check `/etc/hosts` has correct IP
2. Verify network: `ping <ip-address>`
3. Try mDNS: `ping <node>.local`
4. Check SSH: `ssh -v <node>`

### If Service Down
```bash
# Linux (macpro51)
systemctl status <service>
journalctl -u <service> -f

# macOS
launchctl list | grep <service>
```

### If Memory Full
```bash
# Check disk
df -h

# Check memory
free -h  # Linux
vm_stat  # macOS
```

---

## File Locations

### Configuration
- Node config: `~/.claude/node-config.json`
- Cluster nodes: `cluster-deployment/cluster-nodes.json`
- MCP config: `~/.claude.json`

### Databases
- Shared memories: `databases/cluster/shared_memories.db`
- Node chat: `databases/cluster/node_chat.db`
- Qdrant: `databases/qdrant/`

### Logs
- System: `logs/`
- Cluster sync: `logs/cluster-memory-sync.log`
- MCP: Check systemd journal

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Node not resolving | Check `/etc/hosts` |
| SSH fails | Check `~/.ssh/authorized_keys` |
| High CPU | Run `top`, check for Ollama |
| Samba auth fails | Use rsync over SSH instead |
| MCP error | Restart Claude Code |
| RAID degraded | `cat /proc/mdstat` |

---

*Keep this reference handy for quick cluster operations.*
