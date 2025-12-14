# Cluster Execution MCP Server

Cluster-aware command execution for distributed task routing across the AGI agentic cluster.

**Version**: 0.2.0

## Features

- **Automatic task routing**: Commands routed to optimal nodes based on load, capabilities, and requirements
- **Multi-node support**: macpro51 (Linux x86_64), mac-studio (macOS ARM64), macbook-air (macOS ARM64), inference node
- **Dynamic IP resolution**: mDNS, DNS, and fallback methods with caching
- **Security hardened**: No shell injection, environment-based configuration, command validation
- **SSH connectivity verification**: Retry logic with configurable timeouts
- **Parallel execution**: Distribute commands across cluster for maximum throughput

## Installation

```bash
cd /mnt/agentic-system/mcp-servers/cluster-execution-mcp
pip install -e .

# For development:
pip install -e ".[dev]"
```

## Configuration

### Claude Code Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "cluster-execution": {
      "command": "/mnt/agentic-system/.venv/bin/python3",
      "args": ["-m", "cluster_execution_mcp.server"]
    }
  }
}
```

### Environment Variables

All configuration is externalized via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_SSH_USER` | `marc` | SSH username for remote execution |
| `CLUSTER_SSH_TIMEOUT` | `5` | SSH connection timeout (seconds) |
| `CLUSTER_SSH_CONNECT_TIMEOUT` | `2` | Initial SSH connect timeout (seconds) |
| `CLUSTER_SSH_RETRIES` | `2` | Number of SSH retry attempts |
| `CLUSTER_CPU_THRESHOLD` | `40` | CPU usage % threshold for offloading |
| `CLUSTER_LOAD_THRESHOLD` | `4` | Load average threshold for offloading |
| `CLUSTER_MEMORY_THRESHOLD` | `80` | Memory usage % threshold for offloading |
| `CLUSTER_CMD_TIMEOUT` | `300` | Command execution timeout (seconds) |
| `CLUSTER_STATUS_TIMEOUT` | `5` | Status check timeout (seconds) |
| `CLUSTER_IP_CACHE_TTL` | `300` | IP resolution cache TTL (seconds) |
| `CLUSTER_GATEWAY` | `192.168.1.1` | Gateway IP for route detection |
| `CLUSTER_DNS` | `8.8.8.8` | DNS server for IP detection |
| `AGENTIC_SYSTEM_PATH` | `/mnt/agentic-system` | Base path for databases |

### Node Configuration

Node hostnames and IPs can be customized:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_MACPRO51_HOST` | `macpro51.local` | Mac Pro hostname |
| `CLUSTER_MACPRO51_IP` | `192.168.1.183` | Mac Pro fallback IP |
| `CLUSTER_MACSTUDIO_HOST` | `Marcs-Mac-Studio.local` | Mac Studio hostname |
| `CLUSTER_MACSTUDIO_IP` | `192.168.1.16` | Mac Studio fallback IP |
| `CLUSTER_MACBOOKAIR_HOST` | `Marcs-MacBook-Air.local` | MacBook Air hostname |
| `CLUSTER_MACBOOKAIR_IP` | `192.168.1.172` | MacBook Air fallback IP |
| `CLUSTER_INFERENCE_HOST` | `completeu-server.local` | Inference node hostname |
| `CLUSTER_INFERENCE_IP` | `192.168.1.186` | Inference node fallback IP |

## MCP Tools

| Tool | Description |
|------|-------------|
| `cluster_bash` | Execute bash commands with automatic cluster routing |
| `cluster_status` | Get current cluster state and load distribution |
| `offload_to` | Explicitly route command to specific node |
| `parallel_execute` | Run multiple commands in parallel across nodes |

## Usage Examples

### Automatic Routing

```python
# Heavy commands auto-route to least loaded node
result = await cluster_bash("make -j8 all")

# Simple commands run locally
result = await cluster_bash("ls -la")
```

### Force Specific Requirements

```python
# Force Linux execution
result = await cluster_bash("docker build .", requires_os="linux")

# Force x86_64 architecture
result = await cluster_bash("cargo build", requires_arch="x86_64")
```

### Explicit Node Routing

```python
# Run on Linux builder
result = await offload_to("podman run -it ubuntu:22.04", node_id="macpro51")

# Run on Mac Studio
result = await offload_to("swift build", node_id="mac-studio")
```

### Parallel Execution

```python
# Run tests across cluster
results = await parallel_execute([
    "pytest tests/unit/",
    "pytest tests/integration/",
    "pytest tests/e2e/"
])
```

### Cluster Status

```python
# Get cluster health before heavy operations
status = await cluster_status()
# Returns:
# {
#   "local_node": "macpro51",
#   "nodes": {
#     "macpro51": {"cpu_percent": 15.2, "memory_percent": 45.3, ...},
#     "mac-studio": {"cpu_percent": 8.1, "memory_percent": 32.1, ...},
#     ...
#   }
# }
```

## Cluster Nodes

| Node | OS | Arch | Capabilities | Specialties |
|------|-----|------|--------------|-------------|
| `macpro51` | Linux | x86_64 | docker, podman, raid, nvme, compilation, testing, tpu | compilation, testing, containerization, benchmarking |
| `mac-studio` | macOS | ARM64 | orchestration, coordination, temporal, mlx-gpu, arduino | orchestration, coordination, monitoring |
| `macbook-air` | macOS | ARM64 | research, documentation, analysis | research, documentation, mobile |
| `inference` | macOS | ARM64 | ollama, inference, model-serving, llm-api | ollama-inference, model-serving |

## Offload Patterns

Commands matching these patterns are automatically offloaded:

- Build: `make`, `cargo`, `npm`, `yarn`, `pnpm`
- Test: `pytest`, `jest`, `mocha`, `test`
- Compile: `gcc`, `g++`, `clang`
- Container: `docker`, `podman`, `kubectl`
- File ops: `rsync`, `scp`, `tar`, `zip`, `find`, `grep -r`

Commands that stay local:
- Simple: `ls`, `pwd`, `cd`, `echo`, `cat`, `head`, `tail`, `which`, `type`

## Security

### Shell Injection Prevention

All commands use `subprocess.run()` with list arguments where possible:

```python
# SAFE: List arguments
subprocess.run(["ssh", "-o", "ConnectTimeout=5", f"{user}@{ip}", command])

# Complex shell commands are validated before execution
```

### Command Validation

Commands are validated for dangerous patterns:
- `rm -rf /`
- `rm -rf /*`
- `> /dev/sda`
- Fork bombs
- And more...

### SSH Configuration

- `StrictHostKeyChecking=accept-new` - Accept new hosts but verify returning hosts
- `BatchMode=yes` - Non-interactive mode for scripting
- Configurable timeouts and retries

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=cluster_execution_mcp --cov-report=html
```

### Project Structure

```
cluster-execution-mcp/
├── src/cluster_execution_mcp/
│   ├── __init__.py      # Package exports
│   ├── config.py        # Configuration, validation, node definitions
│   ├── router.py        # Task routing and IP resolution
│   └── server.py        # FastMCP server and tools
├── tests/
│   ├── conftest.py      # Pytest fixtures
│   ├── test_config.py   # Config module tests (29 tests)
│   ├── test_router.py   # Router module tests (21 tests)
│   └── test_server.py   # Server and tool tests (21 tests)
└── pyproject.toml       # Package configuration
```

## CLI Interface

```bash
# Submit a command
cluster-router submit "make -j8 all"

# Check task status
cluster-router status <task_id>

# Show cluster status
cluster-router cluster-status
```

## Monitoring

Check cluster health before operations:

```
User: "Show me cluster status"

Claude Code: cluster_status tool

Output:
  macpro51:
    CPU: 45.2%
    Memory: 18.3%
    Load: 3.21
    Status: healthy

  mac-studio:
    CPU: 22.1%
    Memory: 54.7%
    Load: 2.15
    Status: healthy

  macbook-air:
    CPU: 12.8%
    Memory: 38.2%
    Load: 1.03
    Status: healthy
```

## Troubleshooting

**MCP server not loading**:
```bash
# Check config
cat ~/.claude.json | jq '.mcpServers["cluster-execution"]'

# Test server import
python3 -c "from cluster_execution_mcp.server import main; print('OK')"
```

**Node unreachable**:
```bash
# Test SSH connectivity
ssh marc@macpro51.local hostname
ssh marc@Marcs-Mac-Studio.local hostname

# Check with fallback IP
ssh marc@192.168.1.183 hostname
```

**Commands timing out**:
```bash
# Increase timeout via environment
export CLUSTER_CMD_TIMEOUT=600  # 10 minutes
export CLUSTER_SSH_TIMEOUT=10   # 10 seconds
```

## Changelog

### v0.2.0

- **New Features**:
  - Proper package structure with pyproject.toml
  - Environment-based configuration (no hardcoded credentials)
  - Shared config module with validation functions
  - Retry logic for SSH connectivity
  - IP resolution caching with TTL
  - Inference node support

- **Security Improvements**:
  - Eliminated shell injection vulnerabilities
  - Command validation for dangerous patterns
  - IP validation rejecting loopback/Docker/link-local
  - SSH host key handling (accept-new)

- **Code Quality**:
  - Full type hints throughout codebase
  - Replaced bare except clauses with specific exceptions
  - Added comprehensive logging
  - 71 unit tests with mocking

- **Bug Fixes**:
  - Fixed darwin/macos OS alias handling
  - Proper timeout handling in SSH operations
  - Better error messages for failed operations

### v0.1.0

- Initial release with basic cluster execution

## License

MIT

---

**Part of the AGI Agentic System**

See also:
- Node Chat MCP - Inter-node communication
- Enhanced Memory MCP - Persistent memory with RAG
- Agent Runtime MCP - Goals and task queue
