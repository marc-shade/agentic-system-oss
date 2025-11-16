# Cluster Execution MCP Server

**Cluster-aware command execution for Claude Code sessions**

## Overview

This MCP server makes Claude Code automatically cluster-aware. Instead of using the regular `Bash` tool, Claude Code can use `cluster_bash` which automatically routes commands to optimal nodes.

## Tools Provided

### `cluster_bash`
Execute bash commands with automatic cluster routing.

**Auto-routing logic**:
- Heavy commands (make, cargo, pytest, docker, etc.) → Offloaded to least loaded node
- Simple commands (ls, cat, echo) → Execute locally for speed
- High local load (>40% CPU) → Offload to remote node
- Low local load → Execute locally

**Example usage in Claude Code**:
```
User: "Run the test suite"

Claude Code: Uses cluster_bash tool
  command: "pytest tests/"

Result: Automatically routes to macbook-air (least loaded)
  Executed on: macbook-air
  Success: true
  [test output]
```

### `cluster_status`
Get real-time cluster health and load distribution.

**Returns**:
- CPU, memory, load for each node
- Health status (healthy/overloaded)
- Active task counts
- Node reachability

**Use before**:
- Heavy operations (check cluster has capacity)
- Manual routing decisions
- Debugging distribution issues

### `offload_to`
Explicitly route command to specific node.

**Use cases**:
- Linux-specific commands → `offload_to(node_id="macpro51")`
- Architecture-specific builds
- Node-specific testing
- Manual load balancing

**Example**:
```
User: "Build the project on Linux"

Claude Code: Uses offload_to tool
  command: "make build"
  node_id: "macpro51"

Result: Executes on macpro51 regardless of load
```

### `parallel_execute`
Run multiple commands in parallel across cluster.

**Automatically distributes across available nodes**:
```
User: "Run all test files in parallel"

Claude Code: Uses parallel_execute tool
  commands: [
    "pytest tests/test_auth.py",
    "pytest tests/test_api.py",
    "pytest tests/test_db.py"
  ]

Result:
  - test_auth.py → macpro51
  - test_api.py → mac-studio
  - test_db.py → macbook-air
  All run simultaneously
```

## Installation

1. **Install in Claude Code config** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "cluster-execution": {
      "command": "python3",
      "args": ["/home/marc/agentic-system/mcp-servers/cluster-execution-mcp/server.py"],
      "env": {},
      "disabled": false
    }
  }
}
```

2. **Restart Claude Code** to load the MCP server

3. **Verify** it's loaded:
```bash
# In Claude Code session, check available tools
# Should see: cluster_bash, cluster_status, offload_to, parallel_execute
```

## Usage in Claude Code Sessions

### Automatic Routing (Recommended)

Just ask Claude Code to run commands normally. Claude Code can choose to use `cluster_bash` instead of regular `Bash`:

```
User: "Run the test suite"
→ Claude Code uses cluster_bash automatically
→ Routes to optimal node
→ Returns results

User: "Build the project"
→ Claude Code uses cluster_bash
→ Detects "build" pattern, offloads to macpro51
→ Returns build output

User: "List files"
→ Claude Code uses regular Bash (simple command)
→ Executes locally
```

### Explicit Cluster Control

For specific requirements:

```
User: "Check cluster status before running tests"
→ Claude Code uses cluster_status
→ Shows all node loads
→ Decides optimal routing

User: "Build on Linux specifically"
→ Claude Code uses offload_to with node_id="macpro51"
→ Forces execution on Linux builder

User: "Run these 5 tests in parallel"
→ Claude Code uses parallel_execute
→ Distributes across all nodes
→ Shows combined results
```

## How It Works

1. **You use Claude Code normally** in a session
2. **Claude Code has access** to cluster execution tools via MCP
3. **Claude Code decides** whether to use cluster_bash or regular Bash
4. **Commands auto-route** based on:
   - Command characteristics (build/test patterns)
   - Current cluster load
   - Node capabilities
5. **Results return** to you transparently

## Advanced Integration Options

Beyond direct tool use, you can leverage Claude Code's native features:

### Skills
Create reusable skills that wrap cluster operations:
```python
# .claude/skills/cluster_build.py
def cluster_build(project_path):
    """Build project using cluster resources"""
    return cluster_bash(f"cd {project_path} && make build")
```

### Hooks
Use hooks to automatically suggest cluster execution:
```json
{
  "PostToolUse": {
    "hook": "detect_heavy_bash.sh",
    "description": "Suggest cluster execution for heavy commands"
  }
}
```

### tmux Sessions
Run distributed workflows across tmux sessions on different nodes for long-running operations.

## Benefits

✅ **Zero configuration** - Works automatically once MCP server installed
✅ **Transparent** - You use Claude Code normally
✅ **Intelligent** - Auto-routes based on load and command type
✅ **Fast** - Simple commands still run locally
✅ **Parallel** - Can distribute multiple operations
✅ **Explicit control** - Can force specific nodes when needed

## Examples

### Before (Regular Bash)
```
User: "Run pytest on the entire test suite"

Claude Code: Bash tool
  pytest tests/

Result: Runs locally, uses 80% CPU, takes 5 minutes
```

### After (Cluster Bash)
```
User: "Run pytest on the entire test suite"

Claude Code: cluster_bash tool
  command: "pytest tests/"

Auto-routing:
  - Detects "pytest" pattern
  - Checks local load: 65% (high)
  - Queries cluster: macbook-air at 15% (available)
  - Routes to macbook-air

Result: Runs on macbook-air, local CPU stays at 10%, takes 5 minutes
```

### Parallel Execution
```
User: "Run all test modules in parallel"

Claude Code: parallel_execute tool
  commands: [
    "pytest tests/test_auth.py",
    "pytest tests/test_api.py",
    "pytest tests/test_db.py",
    "pytest tests/test_models.py",
    "pytest tests/test_views.py"
  ]

Distribution:
  - test_auth.py → macpro51 (Linux)
  - test_api.py → mac-studio (macOS)
  - test_db.py → macbook-air (macOS)
  - test_models.py → macpro51 (Linux)
  - test_views.py → mac-studio (macOS)

Result: All run simultaneously, complete in 1/5 the time
```

## Monitoring

Check what's being executed where:

```
User: "Show me cluster status"

Claude Code: cluster_status tool

Output:
  ✅ macpro51:
    CPU: 45.2%
    Memory: 18.3%
    Load: 3.21
    Status: healthy

  ✅ mac-studio:
    CPU: 22.1%
    Memory: 54.7%
    Load: 2.15
    Status: healthy

  ✅ macbook-air:
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

# Test server directly
python3 /home/marc/agentic-system/mcp-servers/cluster-execution-mcp/server.py
```

**Commands not routing**:
```bash
# Check cluster-deployment is accessible
ls -la ~/agentic-system/cluster-deployment/

# Verify distributed_task_router.py exists
python3 -c "import sys; sys.path.insert(0, '~/agentic-system/cluster-deployment'); from distributed_task_router import DistributedTaskRouter"
```

**Node unreachable**:
```bash
# Test SSH connectivity
ssh marc@192.168.1.176 hostname
ssh marc@192.168.1.76 hostname

# Check if nodes are running self-X daemon
systemctl --user status cluster-self-x.service  # Linux
ssh marc@192.168.1.176 "launchctl list | grep cluster-self-x"  # macOS
```

## Advanced Usage

### Custom Routing Logic

Force specific OS or architecture:

```
Claude Code: cluster_bash
  command: "make build-linux"
  requires_os: "linux"

→ Forces execution on macpro51 (only Linux node)
```

```
Claude Code: cluster_bash
  command: "cargo build --target aarch64"
  requires_arch: "arm64"

→ Routes to mac-studio or macbook-air (ARM64 nodes)
```

### Disable Auto-routing

For debugging, execute locally even if it's a heavy command:

```
Claude Code: cluster_bash
  command: "pytest tests/"
  auto_route: false

→ Executes locally regardless of load
```

## Performance Impact

**Before cluster-execution-mcp**:
- All commands run locally
- Active node gets overloaded
- Long wait times for heavy operations
- Can't parallelize

**After cluster-execution-mcp**:
- Heavy commands auto-offload
- Active node stays responsive
- Parallel execution across cluster
- Optimal resource utilization

**Expected improvement**:
- 60-90% reduction in active node load
- 3-5x faster for parallel operations
- Zero manual intervention required

---

**Part of the Distributed Self-X System**

See also:
- `cluster-deployment/CLUSTER_SELF_X_SYSTEM.md` - Background self-improvement system
- `cluster-deployment/distributed_task_router.py` - Core routing engine
- `cluster-deployment/DISTRIBUTED_EXECUTION.md` - Manual execution guide
