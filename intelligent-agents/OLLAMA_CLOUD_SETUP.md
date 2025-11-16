# Ollama Cloud + Distributed Setup

## Architecture Overview

**Primary Strategy: Ollama Cloud (Unlimited Parallelism)**
- Cloud models don't use local GPU
- Unlimited parallel agents without resource conflicts
- Falls back to distributed local inference if cloud unavailable

**Fallback Strategy: Distributed Local Ollama**
- 3-node cluster for local inference when needed
- Automatic health checking and failover
- Load balancing across nodes

## Configuration

### Ollama Cloud
- **API Key**: Stored in `~/.zshrc`, `~/.bashrc`, and `/Volumes/SSDRAID0/agentic-system/.env`
- **Cloud Model**: `gpt-oss:20b-cloud` (pulled and ready)
- **Endpoint**: `http://localhost:11434` (local Ollama API routes to cloud)

### Distributed Cluster Nodes
1. **192.168.1.186** (Powerful node)
   - Models: mixtral:8x7b, qwen3:32b, deepseek-r1:32b, gpt-oss:120b
   - Use for: Heavy inference when cloud unavailable

2. **192.168.1.76** (Medium node)
   - Models: llama3.2:latest, mistral:instruct
   - Use for: Standard inference

3. **localhost** (Mac Studio orchestrator)
   - Models: llama3.2:3b, qwen2.5-coder, etc.
   - Use for: Last resort, avoid over-taxing orchestrator

### Load Balancing Strategy
- **Strategy**: `round_robin`
- **Order**: Cloud → 192.168.1.186 → 192.168.1.76 → localhost
- **Health Checks**: Every 60 seconds
- **Failover**: Automatic to healthy nodes

## Benefits

### Unlimited Parallelism (Cloud)
```
✅ Health Guardian        → gpt-oss:20b-cloud (parallel)
✅ Code Evolution Protector → gpt-oss:20b-cloud (parallel)
✅ System Remediation     → gpt-oss:20b-cloud (parallel)
✅ Display Intelligence   → gpt-oss:20b-cloud (parallel)
✅ Any other agents       → gpt-oss:20b-cloud (parallel)
```
All run simultaneously without blocking!

### Fault Tolerance (Fallback)
```
Cloud unavailable? → Use 192.168.1.186 (powerful local)
192.168.1.186 down? → Use 192.168.1.76 (medium local)
192.168.1.76 down? → Use localhost (orchestrator)
```

### Resource Distribution
- **Cloud**: No local GPU usage, unlimited capacity
- **192.168.1.186**: 8x7b+ models, heavy workloads
- **192.168.1.76**: 3b-7b models, standard workloads
- **localhost**: Orchestration only, minimal inference

## Testing

### Test Cloud Model
```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "gpt-oss:20b-cloud",
  "prompt": "System health check",
  "stream": false
}' | jq -r '.response'
```

### Test Load Balancer
```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents/sdk_agents
python3 ollama_load_balancer.py
```

### Test Health Guardian
```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents
python3 specialized/system_health_guardian.py /dev/tty.usbmodem8344401
```

## Performance Characteristics

### Cloud Model (gpt-oss:20b-cloud)
- **Latency**: ~1-3 seconds (network + cloud inference)
- **Throughput**: Unlimited parallel requests
- **Cost**: Uses Ollama Cloud credits
- **Resource Usage**: Zero local GPU/CPU

### Local Models
- **Latency**: ~0.5-2 seconds (local inference)
- **Throughput**: Limited by node count (3 nodes = 3 parallel max)
- **Cost**: Free (self-hosted)
- **Resource Usage**: High local GPU/CPU

## Migration Summary

**Before**:
- Single node (localhost) with API dependencies (Codex, Gemini)
- Limited to 1 agent at a time
- API rate limits and costs
- Over-taxing orchestrator node

**After**:
- Cloud-first (unlimited parallelism) + 3-node fallback
- Unlimited parallel agents
- No API dependencies or rate limits
- Orchestrator node protected from inference load

## Environment Variables

```bash
# Ollama Cloud
export OLLAMA_API_KEY="***REMOVED***"
export OLLAMA_CLOUD_ENDPOINT="http://localhost:11434"
export OLLAMA_CLOUD_MODEL="gpt-oss:20b-cloud"
```

## Files Modified

1. `/Volumes/SSDRAID0/agentic-system/intelligent-agents/specialized/system_health_guardian.py`
   - Changed to `ollama:gpt-oss:20b-cloud`
   - Added distributed load balancer initialization
   - Implemented `_enable_distributed_reasoning()` method

2. `/Volumes/SSDRAID0/agentic-system/intelligent-agents/sdk_agents/cli_agent.py`
   - Added Ollama support (local and remote)
   - Format: `ollama:model` or `ollama@http://ip:port:model`

3. `/Volumes/SSDRAID0/agentic-system/intelligent-agents/sdk_agents/ollama_load_balancer.py`
   - Created load balancer with 4 strategies
   - Health checking and automatic failover
   - Response time tracking

4. `/Volumes/SSDRAID0/agentic-system/.env`
   - Stored Ollama Cloud API key and configuration

## Next Steps

1. Update other intelligent agents to use cloud models
2. Monitor cloud usage and costs
3. Optimize fallback strategy based on actual usage patterns
4. Consider pulling additional cloud models for specific use cases
   - `gpt-oss:120b-cloud` - Larger, more capable
   - `deepseek-v3.1:671b-cloud` - Massive reasoning model
   - `qwen3-coder:480b-cloud` - Specialized coding model

## Status

✅ **Cloud model configured**: gpt-oss:20b-cloud pulled and ready
✅ **API key stored**: Available in .zshrc, .bashrc, and .env
✅ **Load balancer implemented**: 3-node cluster with health checks
✅ **Health Guardian updated**: Using cloud-first strategy
✅ **Distributed reasoning enabled**: Automatic failover to local nodes
✅ **Unlimited parallelism**: Multiple agents can run simultaneously

## Documentation

- Distributed Ollama: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/DISTRIBUTED_OLLAMA.md`
- Ollama Cloud docs: https://docs.ollama.com/cloud
- Load balancer: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/sdk_agents/ollama_load_balancer.py`
