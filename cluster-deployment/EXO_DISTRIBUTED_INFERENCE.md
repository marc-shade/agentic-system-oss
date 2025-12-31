# Exo Distributed LLM Inference Integration

## Overview

This document describes the integration of **Exo** distributed LLM inference with the agentic system cluster. While **RDMA over Thunderbolt** is available in macOS 26.2 Tahoe (released December 12, 2025), it **requires Thunderbolt 5 (M4+ chips)**.

## Hardware Inventory

| Node | Model | Chip | Memory | Thunderbolt | RDMA Support | Role |
|------|-------|------|--------|-------------|--------------|------|
| mac-studio-1 | Mac Studio | M2 Ultra | 192GB | TB4 | No | Orchestrator / Primary |
| mac-studio-2 | Mac Studio | M2 Ultra | 192GB | TB4 | No | Inference Head |
| mac-mini | Mac Mini | M4 Pro | 64GB | **TB5** | **Yes** | Inference Worker |
| macbook-air | MacBook Air | M3 | 24GB | TB3 | No | Researcher / Worker |

**Total Unified Memory Pool**: ~472GB (enough for 400B+ parameter models)

## RDMA Capability Matrix

**CRITICAL**: RDMA over Thunderbolt requires Thunderbolt 5, only available on M4 chips or newer.

| Chip Generation | Thunderbolt Version | RDMA Support |
|-----------------|---------------------|--------------|
| M1 / M1 Pro/Max/Ultra | TB4 | No |
| M2 / M2 Pro/Max/Ultra | TB4 | No |
| M3 / M3 Pro/Max | TB3/TB4 | No |
| **M4 / M4 Pro/Max** | **TB5** | **Yes** |

### Current Cluster RDMA Status
- **mac-mini (M4 Pro)**: Only node with RDMA capability
- **Mac Studios (M2 Ultra)**: No RDMA - will use Ethernet/WiFi
- **MacBook Air (M3)**: No RDMA - will use Ethernet/WiFi

### Future Upgrade Path
To enable full RDMA cluster, would need:
- M4 Ultra Mac Studios (when released)
- M4 MacBook Air (when released)

## Network Topology

### Hybrid Approach: Ethernet + RDMA (Future)

Since most nodes lack TB5, the cluster will primarily use **Ethernet/WiFi** for P2P communication. This still provides significant value by pooling memory across nodes.

```
                    ┌────────────────────┐
                    │   Network Switch   │
                    │  (10GbE / WiFi 6E) │
                    └─────────┬──────────┘
                              │ Exo P2P Discovery
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐     ┌───────┴───────┐     ┌───────┴───────┐
│  mac-studio-1 │     │  mac-studio-2 │     │   mac-mini    │
│  (Orchestrator)│     │ (Inference)   │     │   (Worker)    │
│   192GB M2U   │     │   192GB M2U   │     │   64GB M4P    │
│     TB4       │     │     TB4       │     │   **TB5**     │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │    macbook-air    │
                    │   (Researcher)    │
                    │     24GB M3       │
                    │       TB3         │
                    └───────────────────┘

Legend: Network = Ethernet/WiFi (all nodes)
        RDMA    = Not available (TB5 required on both ends)
```

### Performance Expectations (Without RDMA)

| Transport | Bandwidth | Latency | Notes |
|-----------|-----------|---------|-------|
| 10GbE | ~10 Gbps | ~100-500μs | Good for inference |
| WiFi 6E | ~2-4 Gbps | ~1-5ms | Usable but slower |
| TB5 RDMA | ~80 Gbps | ~1-10μs | Future (M4+ only) |

Even without RDMA, Exo over Ethernet can achieve **useful distributed inference** by pooling memory. The bottleneck shifts from memory to network bandwidth, but this is acceptable for:
- Large batch inference
- Longer context windows
- Models that don't fit in single-node memory

### RDMA Benefits (When Available)
- **Zero-copy transfers**: Data moves directly between device memories
- **80 Gb/s bandwidth**: Thunderbolt 5 with kernel optimizations
- **Shared memory pool**: Unified address space across cluster
- **Low latency**: Eliminates TCP/IP overhead

## Exo Architecture Integration

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENTIC SYSTEM CLUSTER                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    EXO INFERENCE LAYER                    │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │ mac-studio-1│  │ mac-studio-2│  │  mac-mini   │       │   │
│  │  │  MLX Worker │  │  MLX Worker │  │  MLX Worker │       │   │
│  │  │   192GB     │──│   192GB     │──│    64GB     │       │   │
│  │  │  Layers 0-30│  │ Layers 31-60│  │ Layers 61-80│       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  │         │                │                │               │   │
│  │         └────────────────┼────────────────┘               │   │
│  │                          │                                │   │
│  │              ┌───────────┴───────────┐                    │   │
│  │              │   Exo P2P Discovery   │                    │   │
│  │              │   Ring Partitioning   │                    │   │
│  │              └───────────────────────┘                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              │ OpenAI-Compatible API             │
│                              │ http://localhost:8000             │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 UNIFIED INFERENCE PROXY                   │   │
│  │                  (exo-inference-mcp)                      │   │
│  │                                                           │   │
│  │  • Cluster-aware routing                                  │   │
│  │  • Model selection (size → cluster fit)                   │   │
│  │  • Fallback to single-node for small models               │   │
│  │  • Token streaming support                                │   │
│  │  • Usage metrics & cost tracking                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                   │
│              ▼               ▼               ▼                   │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       │
│  │ enhanced-memory│ │ agent-runtime  │ │  node-chat     │       │
│  │     -mcp       │ │     -mcp       │ │     -mcp       │       │
│  └────────────────┘ └────────────────┘ └────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Ring Memory Weighted Partitioning

Exo automatically partitions models based on available memory:

```
Model: Llama 3.3 70B (140GB at FP16, 70GB at Q8)

Node Distribution (by memory ratio):
┌─────────────────────────────────────────────────────────────┐
│ mac-studio-1 │ mac-studio-2 │ mac-mini │ macbook-air       │
│    192GB     │    192GB     │   64GB   │    24GB           │
│    40.7%     │    40.7%     │  13.6%   │    5.1%           │
│  Layers 0-28 │ Layers 29-56 │  57-66   │   67-70           │
└─────────────────────────────────────────────────────────────┘

Inference Flow (Ring Pattern):
mac-studio-1 → mac-studio-2 → mac-mini → macbook-air → mac-studio-1
     ↓              ↓             ↓            ↓
  Process       Process       Process      Process
  Layers        Layers        Layers       Layers
   0-28         29-56         57-66        67-70
```

## Unified Inference API

### Access from Any Node

The key requirement is that **any active node can leverage the full cluster's compute**. This is achieved through:

1. **Exo P2P Discovery**: All nodes automatically find each other
2. **Unified API Endpoint**: Same API available on each node
3. **MCP Proxy Layer**: `exo-inference-mcp` provides consistent interface

### API Endpoints

```yaml
# OpenAI-Compatible API (on each Exo node)
Base URL: http://localhost:8000

Endpoints:
  - POST /v1/chat/completions     # Chat completion
  - POST /v1/completions          # Text completion
  - GET  /v1/models               # List available models
  - GET  /cluster/status          # Cluster health
  - GET  /cluster/nodes           # Node inventory
```

### Example Usage from Agentic System

```python
# From any node in the cluster
from exo_inference import ExoClusterClient

client = ExoClusterClient()

# Automatically uses full cluster memory pool
response = await client.chat_completion(
    model="llama-3.3-70b",  # Requires ~140GB - distributed across cluster
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing."}
    ],
    stream=True
)

async for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

## MCP Integration: exo-inference-mcp

### Server Design

```python
# mcp-servers/exo-inference-mcp/server.py

from mcp import Server
from exo_client import ExoDistributedClient

server = Server("exo-inference-mcp")
client = ExoDistributedClient()

@server.tool("exo_chat")
async def exo_chat(
    messages: list[dict],
    model: str = "auto",  # Auto-select based on cluster capacity
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = True
) -> str:
    """
    Run chat completion on distributed Exo cluster.
    Automatically leverages all available cluster memory.
    """
    return await client.chat(messages, model, temperature, max_tokens, stream)

@server.tool("exo_cluster_status")
async def cluster_status() -> dict:
    """Get Exo cluster status including node health and memory usage."""
    return await client.get_cluster_status()

@server.tool("exo_models")
async def list_models() -> list[dict]:
    """List models that can run on the current cluster configuration."""
    cluster_memory = await client.get_total_memory()
    return await client.get_compatible_models(cluster_memory)
```

### MCP Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "exo-inference": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/exo-inference-mcp/server.py"],
      "env": {
        "EXO_API_URL": "http://localhost:8000",
        "EXO_DISCOVERY": "auto"
      }
    }
  }
}
```

## Supported Models by Cluster Size

| Model | Parameters | Memory (FP16) | Memory (Q8) | Min Cluster |
|-------|------------|---------------|-------------|-------------|
| Llama 3.2 | 3B | 6GB | 3GB | Single node |
| Llama 3.1 | 8B | 16GB | 8GB | Single node |
| Llama 3.1 | 70B | 140GB | 70GB | 2x Mac Studio |
| Llama 3.1 | 405B | 810GB | 405GB | Full cluster |
| DeepSeek V3 | 671B | 1.3TB | 670GB | Full cluster + more |
| Qwen 2.5 | 72B | 144GB | 72GB | 2x Mac Studio |
| Mixtral | 8x22B | ~280GB | ~140GB | Full cluster |

With 472GB unified memory, the cluster can run:
- All 70B-class models at FP16
- Most 400B-class models at Q8 quantization
- Mixtral 8x22B MoE at Q8

## Implementation Roadmap

### Phase 1: Prerequisites
- [x] macOS 26.2 Tahoe released (Dec 12, 2025)
- [ ] Update all nodes to macOS 26.2+
- [ ] Verify Ethernet/WiFi network connectivity between all nodes
- [ ] Ensure 10GbE or WiFi 6E for optimal bandwidth

### Phase 2: Exo Installation ✅ COMPLETED on mac-studio
- [x] Install Exo on mac-studio via DMG (`/Applications/EXO.app`)
- [x] Verify Exo API running at localhost:8000
- [x] Test single-node inference (Llama 3.2 1B 4-bit)
- [ ] Install Exo on mac-mini (M4 Pro - TB5 RDMA capable)
- [ ] Install Exo on macbook-air (M3)
- [ ] Verify P2P auto-discovery working over Ethernet
- [ ] Test distributed inference across 2 nodes

**Installation Notes (December 18, 2025):**
```bash
# DMG Install (recommended)
# Download from: https://assets.exolabs.net/EXO-latest.dmg
# CLI location: /Applications/EXO.app/Contents/Resources/exo/exo

# Start Exo with force-master flag (single node)
/Applications/EXO.app/Contents/Resources/exo/exo --verbose --force-master

# Create instance before inference
curl -s "http://localhost:8000/instance/placement?model_id=llama-3.2-1b" | \
  curl -s -X POST "http://localhost:8000/instance" \
    -H "Content-Type: application/json" \
    -d "{\"instance\":$(cat -)}"

# Test inference
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.2-1b","messages":[{"role":"user","content":"Hello"}]}'
```

**Known Issues:**
- MacMon not found error (non-critical) - resource monitoring tool missing
- Models must be explicitly instantiated before inference (auto-download doesn't create instance)

### Phase 3: Cluster Validation (Ethernet-based)
- [ ] Test full 4-node cluster over Ethernet/WiFi
- [ ] Benchmark token throughput
- [ ] Verify memory pooling works correctly
- [ ] Test failover when nodes disconnect

### Phase 4: MCP Integration ✅ COMPLETED
- [x] Create exo-inference-mcp server skeleton
- [x] Complete MCP server implementation
- [x] Integrate with existing agentic system
- [x] Add to Claude Code MCP configuration (~/.claude.json)

**MCP Server Tools (December 18, 2025):**
- `exo_chat` - Chat completion (requires model loaded first)
- `exo_load_model` - Create instance and wait for runner ready
- `exo_unload_model` - Delete instance to free memory
- `exo_status` - Get cluster status (nodes, instances, runners, memory)
- `exo_models` - List all 22 available models

**Verified Working:**
- Status check returns node/instance/runner details
- Model list returns 22 models including DeepSeek V3.1, Llama 3.x series
- Chat completion working with Llama 3.2 1B (4-bit, ~700MB)
- [ ] Test from all cluster nodes

### Phase 5: Optimization & Monitoring
- [ ] Tune ring partitioning for workload
- [ ] Implement model caching strategy
- [ ] Add monitoring to Grafana dashboard
- [ ] Document operational procedures

### Phase 6: Future RDMA (When Hardware Available)
- [ ] Acquire M4 Ultra Mac Studios (when released)
- [ ] Acquire Thunderbolt 5 cables
- [ ] Configure RDMA between TB5-capable nodes
- [ ] Benchmark RDMA vs Ethernet performance

## Monitoring Integration

Add Exo metrics to existing Prometheus/Grafana stack:

```yaml
# monitoring/prometheus/prometheus.yml (addition)
scrape_configs:
  - job_name: 'exo-cluster'
    static_configs:
      - targets:
        - 'mac-studio-1.local:8000'
        - 'mac-studio-2.local:8000'
        - 'mac-mini.local:8000'
        - 'macbook-air.local:8000'
    metrics_path: '/metrics'
```

### Key Metrics to Track
- `exo_tokens_per_second` - Inference throughput
- `exo_memory_used_bytes` - Per-node memory usage
- `exo_cluster_nodes_active` - Node availability
- `exo_rdma_bandwidth_bytes` - RDMA transfer rates
- `exo_model_load_time_seconds` - Model loading latency

## Security Considerations

1. **Network Isolation**: Exo cluster should be on isolated VLAN
2. **API Authentication**: Add authentication to OpenAI-compatible API
3. **Data Privacy**: All inference runs locally, no external API calls
4. **Access Control**: Limit MCP tool access to authorized agents

## Performance Comparison

### Current Setup (Ethernet/WiFi - No RDMA)

| Metric | 10GbE Ethernet | WiFi 6E |
|--------|----------------|---------|
| Bandwidth | ~10 Gbps | ~2-4 Gbps |
| Latency | ~100-500μs | ~1-5ms |
| CPU Overhead | Moderate | Moderate |
| Memory Efficiency | Buffer copies | Buffer copies |
| Best For | Distributed inference | Mobile/portable nodes |

### Future (RDMA/TB5 - M4+ Hardware Required)

| Metric | RDMA over TB5 |
|--------|---------------|
| Bandwidth | ~80 Gbps |
| Latency | ~1-10μs |
| CPU Overhead | Near zero |
| Memory Efficiency | Zero-copy |
| Expected Speedup | 3-4x vs Ethernet |

### Practical Implications for Current Cluster

Without RDMA, the cluster still provides value:
- **Memory pooling**: Run 400B+ models that don't fit in single node
- **Batch throughput**: Good for non-real-time inference
- **Token generation**: ~10-30 tok/s depending on model and network
- **Context windows**: Enable longer contexts by distributing KV cache

The network becomes the bottleneck instead of memory, but for many agentic workloads this is acceptable since:
1. Agent tasks often involve thinking time between API calls
2. Batch processing of multiple prompts can hide latency
3. Large context retrieval (RAG) benefits more from memory than speed

## References

- [Exo GitHub Repository](https://github.com/exo-explore/exo)
- [Apple RDMA over Thunderbolt Announcement](https://www.webpronews.com/apples-macos-tahoe-26-2-enables-rdma-over-thunderbolt-for-ai-mac-clusters/)
- [macOS Tahoe 26.2 Release Notes](https://www.macrumors.com/roundup/macos-26/)
- [MLX Framework Documentation](https://github.com/ml-explore/mlx)
- [Linus Tech Tips Mac AI Cluster Video](https://youtu.be/4l4UWZGxvoc)

---

*Document created: December 18, 2025*
*Status: Planning Phase*
