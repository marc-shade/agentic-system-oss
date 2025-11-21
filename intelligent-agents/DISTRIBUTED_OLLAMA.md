# Distributed Ollama for Intelligent Agents

## Overview

The intelligent agent system now supports distributed Ollama inference across your 3-node cluster:
- **mac-studio** (Orchestrator, Priority 1)
- **macbook-air** (Researcher, Priority 2)
- **macbook-pro** (Developer, Priority 2)

This eliminates:
- ❌ External API dependencies (Codex, Gemini)
- ❌ API rate limits
- ❌ Network latency
- ❌ Single-node resource bottlenecks

And provides:
- ✅ 100% local inference
- ✅ Automatic failover
- ✅ Load distribution
- ✅ Fast response times

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Intelligent Agent (Health Guardian)        │
│                  cli_tool="ollama:llama3.2:3b"         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Ollama Load Balancer                       │
│            Strategy: local_first / round_robin          │
└──┬──────────────────┬──────────────────┬────────────────┘
   │                  │                  │
   ▼                  ▼                  ▼
┌──────┐          ┌──────┐          ┌──────┐
│ Mac  │          │ Air  │          │ Pro  │
│Studio│          │      │          │      │
│:11434│          │:11434│          │:11434│
└──────┘          └──────┘          └──────┘
```

## Configuration Formats

### 1. Local Ollama (Current)
```python
cli_tool="ollama:llama3.2:3b"
```
- Uses `localhost:11434`
- Fastest for local inference
- No network overhead

### 2. Remote Ollama (Single Node)
```python
cli_tool="ollama@http://192.168.1.10:11434:llama3.2:3b"
```
- Uses specific remote endpoint
- Good for offloading to dedicated node

### 3. Load Balanced (Multiple Nodes)
```python
from ollama_load_balancer import OllamaLoadBalancer

balancer = OllamaLoadBalancer([
    "http://localhost:11434",              # mac-studio (local)
    "http://macbook-air.local:11434",      # macbook-air
    "http://macbook-pro.local:11434",      # macbook-pro
], strategy="local_first")

# Use with CLI agent
cli_agent.ollama_balancer = balancer
```

## Load Balancing Strategies

### `local_first` (Recommended for mac-studio)
- Prefers localhost when available
- Falls back to remote nodes
- Best for primary orchestrator node

### `round_robin` (Fair distribution)
- Cycles through all healthy nodes
- Even distribution of load
- Good for batch processing

### `least_loaded` (Dynamic optimization)
- Chooses node with lowest current requests
- Adapts to real-time load
- Best for mixed workloads

### `random` (Simple failover)
- Random selection from healthy nodes
- Simpler than round_robin
- Good for testing

## Health Guardian Configuration

### Current (Local Only)
```python
# /Volumes/SSDRAID0/agentic-system/intelligent-agents/specialized/system_health_guardian.py

super().__init__(
    purpose=purpose,
    tools=self._get_tool_definitions(),
    cli_tool="ollama:llama3.2:3b"  # Local only
)
```

### Distributed (Load Balanced)
```python
# Add to __init__ after super().__init__

from sdk_agents.ollama_load_balancer import OllamaLoadBalancer

# Create load balancer with cluster nodes
self.ollama_balancer = OllamaLoadBalancer([
    "http://localhost:11434",              # mac-studio (local)
    "http://macbook-air.local:11434",      # macbook-air
    "http://macbook-pro.local:11434",      # macbook-pro
], strategy="local_first")

# Override CLI agent's generate method to use balancer
self._use_load_balancer()

def _use_load_balancer(self):
    """Replace direct Ollama calls with load balancer"""
    original_reason = self.reason

    def balanced_reason(observations):
        # Use load balancer instead of direct endpoint
        result = self.ollama_balancer.generate(
            model=self.ollama_model,
            prompt=self._format_observations_prompt(observations)
        )
        # Convert to AgentDecision
        return AgentDecision(
            timestamp=datetime.now().isoformat(),
            decision=result['response'],
            reasoning=result['response'],
            confidence=0.7,
            action_taken=f"endpoint:{result['endpoint_used']}",
            tool_used=None
        )

    self.reason = balanced_reason
```

## Network Configuration

### Verify Ollama is accessible on cluster nodes

**On each node (macbook-air, macbook-pro):**

```bash
# Check Ollama is running
ollama list

# Verify port 11434 is listening
lsof -ti:11434

# Test from mac-studio
curl http://macbook-air.local:11434/api/tags
curl http://macbook-pro.local:11434/api/tags
```

### Firewall Configuration

Ensure port 11434 is open on all nodes:

```bash
# macOS firewall (if enabled)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/ollama
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock /usr/local/bin/ollama
```

## Testing Distributed Setup

### Test Remote Endpoint
```bash
curl -X POST http://macbook-air.local:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"test","stream":false}'
```

### Test Load Balancer
```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents/sdk_agents
python3 ollama_load_balancer.py
```

Expected output:
```
Response: 4
Endpoint: http://localhost:11434
Time: 156ms

Status:
{
  "strategy": "local_first",
  "total_nodes": 3,
  "healthy_nodes": 1,  # Others offline or unreachable
  "nodes": [...]
}
```

## Performance Characteristics

### Local (localhost:11434)
- **First request**: ~18 seconds (model loading)
- **Subsequent**: ~0.5-2 seconds
- **Best for**: Real-time monitoring, quick decisions

### Remote (macbook-air.local:11434)
- **Network latency**: +5-20ms
- **Same inference speed**: ~0.5-2 seconds after loading
- **Best for**: Background processing, batch jobs

### Load Balanced (3 nodes)
- **Throughput**: 3x single node
- **Failover**: Automatic to healthy nodes
- **Best for**: High-volume agent swarms

## Migration Path

1. ✅ **Phase 1 (Current)**: Local Ollama on mac-studio
   - Health Guardian using `ollama:llama3.2:3b`
   - All inference on orchestrator node

2. **Phase 2 (Optional)**: Add remote nodes
   - Update Health Guardian to use load balancer
   - Distribute load across cluster
   - Test failover scenarios

3. **Phase 3 (Future)**: Multi-agent swarms
   - Multiple intelligent agents running concurrently
   - Each using load-balanced Ollama
   - Cluster-wide resource optimization

## Benefits

### Resource Distribution
- Mac Studio handles orchestration + local inference
- MacBook Air/Pro handle offloaded inference
- No single point of resource exhaustion

### Fault Tolerance
- Automatic failover to healthy nodes
- Continues operation if node goes down
- Health checking every 60 seconds

### Scalability
- Add more nodes by updating endpoint list
- Linear scaling of inference capacity
- No code changes required

## Monitoring

### Check Load Balancer Status
```python
status = balancer.get_status()
print(f"Healthy nodes: {status['healthy_nodes']}/{status['total_nodes']}")
```

### Check Node Response Times
```python
for node in status['nodes']:
    print(f"{node['endpoint']}: {node['response_time_ms']:.0f}ms")
```

### Integration with Enhanced Memory
All load balancer decisions and performance metrics can be stored:

```python
from enhanced_memory import create_entities

create_entities([{
    "name": f"ollama-lb-decision-{timestamp}",
    "entityType": "inference_routing",
    "observations": [
        f"model={model}",
        f"endpoint={result['endpoint_used']}",
        f"response_time_ms={result['response_time_ms']}",
        f"strategy={balancer.strategy}"
    ]
}])
```

## Troubleshooting

### Node shows as unhealthy
```bash
# Check Ollama is running on remote node
ssh macbook-air.local "ollama list"

# Check network connectivity
ping macbook-air.local

# Check port accessibility
curl http://macbook-air.local:11434/api/tags
```

### Slow responses
- First request loads model (~18s)
- Keep models loaded: `ollama run llama3.2:3b` on each node
- Consider using persistent Ollama sessions

### Load balancer not distributing evenly
- Check strategy setting (`round_robin` for even distribution)
- Verify all nodes are healthy
- Check network latency between nodes

## Future Enhancements

1. **Model-specific routing**: Route different models to different nodes
2. **GPU detection**: Prefer nodes with available GPU
3. **Cost optimization**: Track token usage per node
4. **Adaptive strategies**: Learn optimal routing from performance data
5. **Multi-model support**: Load different models on different nodes
