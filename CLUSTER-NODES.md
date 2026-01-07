# Cluster Node System Cards

**Last Scan**: 2026-01-07 15:39 EST
**Total Nodes**: 5 discovered (3 fully operational, 1 limited, 1 offline)

---

## Node Summary

| Node | Role | Hardware | Status | IP |
|------|------|----------|--------|-----|
| **mac-studio** | Orchestrator | M2 Max 32GB | **ACTIVE** | 192.168.1.16 |
| **macpro51** | Builder | Dual Xeon 94GB + RTX 3060 | **ACTIVE** | 192.168.1.27 |
| **completeu-server** | Inference | M4 Max 128GB | **ACTIVE** | 192.168.1.186 |
| **macbook-air** | Researcher | Apple Silicon | **OFFLINE** | - |
| **bpi-sentinel** | Sentinel | ARM SBC | **LIMITED** | 192.168.1.234 |

---

## mac-studio (Orchestrator)

**Role**: Primary orchestrator, system coordination, priority 1

### Hardware
| Spec | Value |
|------|-------|
| **Model** | Mac Studio (Mac14,13) |
| **Chip** | Apple M2 Max |
| **CPU Cores** | 12 (8P + 4E) |
| **Memory** | 32 GB |
| **OS** | macOS Tahoe 26.2.0 |

### Storage
| Mount | Type | Capacity | Used | Available |
|-------|------|----------|------|-----------|
| /Volumes/SSDRAID0 | SSD RAID | 1.8 TB | 565 GB (31%) | 1.3 TB |
| /Volumes/FILES | HDD | 3.6 TB | 1.8 TB (50%) | 1.8 TB |

### Current Load
- **CPU**: 57.9%
- **Memory**: 64.3%
- **Load Average**: 13.63 (overloaded)

### Services
| Service | Port | Status |
|---------|------|--------|
| Temporal gRPC | 7233 | Active |
| Temporal UI | 8233 | Active |
| Arduino Surface | 8200 | Active |
| Enhanced Memory | 8101 | Active |
| Agent Runtime | 8102 | Active |
| Qdrant REST | 6333 | Active |
| Qdrant gRPC | 6334 | Active |

### MCP Servers (Primary)
- enhanced-memory-mcp
- agent-runtime-mcp
- sequential-thinking
- voice-mode
- arduino-surface
- cluster-execution-mcp
- safla-mcp

### Capabilities
```
orchestrator_primary
apple_silicon_m2_max
32gb_unified_memory
ssd_raid_1.8tb
temporal_workflows
mcp_server_host
voice_mode_tts_stt
arduino_physical_interface
cluster_coordination
```

---

## macpro51 (Builder)

**Role**: Linux builder, compilation, testing, GPU compute, priority 3

### Hardware
| Spec | Value |
|------|-------|
| **Model** | Mac Pro 5,1 (2010) - Hackintosh |
| **CPU** | Dual Intel Xeon X5680 @ 3.33GHz |
| **CPU Cores** | 24 threads |
| **Memory** | 94 GB DDR3 ECC |
| **GPU** | NVIDIA GeForce RTX 3060 12GB |
| **OS** | Fedora 43 (Kernel 6.17.12) |

### Storage
| Mount | Type | Capacity | Used | Available |
|-------|------|----------|------|-----------|
| /dev/md0 (RAID10) | 4x NVMe | 931 GB | - | - |
| /dev/sda3 | SSD | 231 GB | 136 GB (60%) | 93 GB |

### RAID Status
```
md0 : active raid10 nvme3n1 nvme0n1 nvme2n1 nvme1n1
      976508928 blocks [4/4] [UUUU]
```
**Status**: All 4 drives healthy

### Current Load
- **Uptime**: 2 days, 22:52
- **Load Average**: 5.28, 4.92, 4.91
- **Memory**: 21GB / 94GB used (73GB available)

### GPU Status
| GPU | VRAM | Used | Utilization |
|-----|------|------|-------------|
| RTX 3060 | 12288 MiB | 767 MiB | 0% |

### Docker Containers
| Container | Status | Purpose |
|-----------|--------|---------|
| grafana | Up 2 days | Visualization |
| qdrant | Up 2 days | Vector DB |
| kutiraai-postgres | Up 2 days | PostgreSQL |
| n8n | Up 2 days | Workflows |
| promtail | Up 2 days | Log shipping |
| alertmanager | Up 2 days | Alerts |
| node-exporter | Up 2 days | Metrics |

### Ollama Models
| Model | Size |
|-------|------|
| gpt-oss | 120b (cloud) |
| gemma3 | 12b |
| qwen3-vl | 8b |
| deepseek-r1 | 14b |
| qwen3 | 14b |
| nomic-embed-text | latest |

### Services
| Service | Port | Status |
|---------|------|--------|
| Builder API | 9000 | Not Found |
| Ollama | 11434 | Active |
| SSH | 22 | Active |
| n8n | 5678 | Active |
| Qdrant | 6333/6334 | Active |
| Netdata | 19999 | Active |
| SMB | 139/445 | Active |

### Capabilities
```
linux_builder
dual_xeon_24_threads
94gb_ram_ecc
nvidia_rtx_3060_12gb
nvme_raid10_931gb
docker_podman_native
ollama_local_models
compilation_heavy_workloads
test_execution
gpu_compute_cuda
```

---

## completeu-server (Inference)

**Role**: High-memory inference, large model hosting, cloud model gateway

### Hardware
| Spec | Value |
|------|-------|
| **Model** | Mac Studio (Mac16,9) |
| **Chip** | Apple M4 Max |
| **CPU Cores** | 16 (12P + 4E) |
| **Memory** | 128 GB |
| **OS** | macOS Tahoe 25.2.0 |

### Storage
| Mount | Type | Capacity | Used | Available |
|-------|------|----------|------|-----------|
| / | SSD | 460 GB | 11 GB (8%) | 137 GB |

### Current Load
- **Uptime**: 18 days, 5:14
- **Load Average**: 3.85, 4.04, 3.77

### Ollama Models (Cloud Gateway)
| Model | Type |
|-------|------|
| gpt-oss | 120b (cloud) |
| gemini-3-flash-preview | cloud |
| minimax-m2.1 | cloud |
| glm-4.7 | cloud |
| gemma3 | 12b local |
| qwen3-vl | 8b local |
| minicpm-v | local |
| deepseek-r1 | 14b local |
| qwen2-math | 7b local |
| qwen2.5-coder | 7b local |

### Services
| Service | Port | Status |
|---------|------|--------|
| Ollama | 11434 | Active |
| SSH | 22 | Active |

### Capabilities
```
apple_silicon_m4_max
128gb_unified_memory
ollama_cloud_gateway
large_model_inference
vision_models
math_models
coding_models
high_memory_workloads
```

---

## macbook-air (Researcher)

**Role**: Research, analysis, documentation, priority 2

### Status
**OFFLINE** - mDNS service advertised but host unreachable

### Discovery Info
- **mDNS Name**: Marc's MacBook Air
- **Service**: _ssh._tcp
- **Last Seen**: 2026-01-07 (service announcement only)

### Expected Capabilities
```
apple_silicon
research_analysis
documentation
mobile_development
```

---

## bpi-sentinel (Sentinel)

**Role**: Environmental monitoring, security sentinel

### Status
**LIMITED** - Pingable but SSH access failed

### Network
| Spec | Value |
|------|-------|
| **IP** | 192.168.1.234 |
| **Hostname** | bpi-sentinel.local |
| **Type** | ARM Single Board Computer |

### Expected Capabilities
```
environmental_monitoring
security_sentinel
low_power_always_on
sensor_integration
```

---

## Network Topology

```
                    ┌─────────────────┐
                    │   FIOS Router   │
                    │  192.168.1.1    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│  mac-studio   │   │   macpro51    │   │ completeu-srv │
│  Orchestrator │   │    Builder    │   │   Inference   │
│ 192.168.1.16  │   │ 192.168.1.27  │   │ 192.168.1.186 │
│    M2 Max     │   │  Dual Xeon    │   │    M4 Max     │
│     32GB      │   │   94GB+GPU    │   │    128GB      │
└───────────────┘   └───────────────┘   └───────────────┘
        │
        │ USB Serial
        ▼
┌───────────────┐
│ Arduino UNO   │
│ Physical I/O  │
└───────────────┘
```

---

## Cluster Commands

### Check All Nodes
```bash
# Quick ping check
for host in mac-studio macpro51 completeu-server macbook-air bpi-sentinel; do
  ping -c 1 -t 2 ${host}.local 2>/dev/null && echo "$host: UP" || echo "$host: DOWN"
done

# Full cluster status (via MCP)
mcp__cluster-execution-mcp__cluster_status

# Avahi service discovery
dns-sd -B _ssh._tcp local.
dns-sd -B _agentic-builder._tcp local.
```

### Distributed Execution
```bash
# Auto-route to optimal node
mcp__cluster-execution-mcp__cluster_bash(command="make build")

# Force to specific node
mcp__cluster-execution-mcp__offload_to(node_id="macpro51", command="docker build .")

# Parallel across cluster
mcp__cluster-execution-mcp__parallel_execute(commands=["test1", "test2", "test3"])
```

### Node-to-Node Communication
```bash
# Send message to node
mcp__cluster-execution-mcp__send_message_to_node(to_node="builder", message="Start task")

# Check for messages
mcp__cluster-execution-mcp__check_for_new_messages()

# View cluster awareness
mcp__cluster-execution-mcp__get_cluster_awareness()
```

---

## Aggregate Cluster Resources

| Resource | Total |
|----------|-------|
| **CPU Cores** | 52 (12 + 24 + 16) |
| **Memory** | 254 GB (32 + 94 + 128) |
| **GPU VRAM** | 12 GB (RTX 3060) |
| **Fast Storage** | 3.7 TB |
| **Cold Storage** | 3.6 TB |
| **Ollama Models** | 16 unique |

---

*Generated by Phoenix AGI System*
*Scan Time: 2026-01-07 15:39 EST*
