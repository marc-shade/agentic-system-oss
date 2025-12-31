#!/usr/bin/env python3
"""
Cluster Execution MCP Server

Provides cluster-aware command execution and inter-node communication for Claude Code.
Automatically routes commands to optimal nodes based on:
- Current cluster load
- Command characteristics
- Node capabilities

Cluster Execution Tools (4):
- cluster_bash: Execute bash commands across cluster (auto-routing)
- cluster_status: Get current cluster state
- offload_to: Explicitly route to specific node
- parallel_execute: Run commands in parallel across nodes

Node Chat Tools (22 - merged from node-chat-mcp):
- Messaging: send_message_to_node, get_conversation_history, check_for_new_messages, broadcast_to_cluster
- Awareness: get_my_awareness, get_cluster_awareness, get_node_status
- Conversation: watch_cluster_conversations, view_conversations_threaded, prepare_conversation_context
- AGI: decompose_goal, initiate_research_pipeline, start_improvement_cycle
- Memory: search_conversation_memory, get_memory_stats, remember_fact_about_node

Usage in Claude Code sessions:
- "Run tests" → Uses cluster_bash, auto-routes to least loaded node
- "Build on Linux" → Uses offload_to with node="macpro51"
- "Check cluster status" → Uses cluster_status
- "Send message to builder" → Uses send_message_to_node
- "Decompose goal" → Uses AGI goal decomposition
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

# Add cluster-deployment to path
CLUSTER_DIR = Path(__file__).parent.parent.parent / "cluster-deployment"
sys.path.insert(0, str(CLUSTER_DIR))

from distributed_task_router import DistributedTaskRouter, CLUSTER_NODES
from performance_optimizer import PerformanceOptimizer

# Import node chat integration
try:
    from node_chat_integration import get_node_chat_tools, handle_node_chat_tool
    NODE_CHAT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Node chat integration not available: {e}", file=sys.stderr)
    NODE_CHAT_AVAILABLE = False

# Import cluster curriculum sync (Priority 3 AGI Gap Fix)
HOOKS_DIR = Path.home() / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))
try:
    from cluster_curriculum_sync import (
        push_curriculum_to_cluster,
        pull_curriculum_from_cluster,
        get_cluster_curriculum_status
    )
    CURRICULUM_SYNC_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Cluster curriculum sync not available: {e}", file=sys.stderr)
    CURRICULUM_SYNC_AVAILABLE = False

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import mcp.server.stdio
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install anthropic-mcp", file=sys.stderr)
    sys.exit(1)


class ClusterExecutionServer:
    """MCP Server for cluster-aware execution"""

    def __init__(self):
        self.router = DistributedTaskRouter()
        self.optimizer = PerformanceOptimizer()
        self.local_node_id = self.router.local_node_id

    def should_offload(self, command: str) -> bool:
        """
        Determine if command should be offloaded based on characteristics
        """
        # Always offload these patterns
        offload_patterns = [
            'make', 'cargo', 'npm', 'yarn', 'pnpm',
            'pytest', 'jest', 'mocha', 'test',
            'build', 'compile', 'gcc', 'g++', 'clang',
            'docker', 'podman', 'kubectl',
            'rsync', 'scp', 'tar', 'zip', 'unzip',
            'find', 'grep -r', 'rg'
        ]

        cmd_lower = command.lower()
        for pattern in offload_patterns:
            if pattern in cmd_lower:
                return True

        # Don't offload simple commands
        simple_patterns = ['ls', 'pwd', 'cd', 'echo', 'cat']
        if any(cmd_lower.startswith(p) for p in simple_patterns):
            return False

        # Check current load - offload if we're busy
        metrics = self.optimizer.get_current_metrics()
        if metrics.cpu_percent > 40 or metrics.load_average_1m > 4:
            return True

        return False

    def get_cluster_status(self) -> Dict:
        """Get current cluster status"""
        status = {
            "local_node": self.local_node_id,
            "nodes": {}
        }

        # Get local metrics
        local_metrics = self.optimizer.get_current_metrics()
        status["nodes"][self.local_node_id] = {
            "cpu_percent": local_metrics.cpu_percent,
            "memory_percent": local_metrics.memory_percent,
            "load_1m": local_metrics.load_average_1m,
            "active_tasks": local_metrics.active_tasks,
            "status": "healthy" if not self.optimizer.is_overloaded(local_metrics) else "overloaded"
        }

        # Get remote metrics via SSH
        for node_id, node_info in CLUSTER_NODES.items():
            if node_id == self.local_node_id:
                continue

            try:
                import shlex
                # Properly quote the Python script for safe SSH transport
                metrics_script = "import psutil, os; print(psutil.cpu_percent()); print(psutil.virtual_memory().percent); print(os.getloadavg()[0])"
                remote_cmd = f"python3 -c {shlex.quote(metrics_script)}"

                # Use list args for security instead of shell=True
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "ConnectTimeout=3",
                        "-o", "StrictHostKeyChecking=accept-new",
                        "-o", "BatchMode=yes",
                        f"marc@{node_info['ip']}",
                        remote_cmd
                    ],
                    capture_output=True,
                    text=True,
                    timeout=8
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    # Filter to only numeric lines (skip shell startup messages like "Cluster environment loaded...")
                    numeric_lines = [l for l in lines if l.replace('.', '').replace('-', '').isdigit() or
                                     (l.count('.') == 1 and l.replace('.', '').replace('-', '').isdigit())]
                    if len(numeric_lines) >= 3:
                        cpu = float(numeric_lines[0])
                        memory = float(numeric_lines[1])
                        load = float(numeric_lines[2])

                        status["nodes"][node_id] = {
                            "cpu_percent": round(cpu, 1),
                            "memory_percent": round(memory, 1),
                            "load_1m": round(load, 2),
                            "status": "healthy" if cpu < 70 and memory < 80 else "overloaded",
                            "reachable": True
                        }
                    else:
                        status["nodes"][node_id] = {"reachable": False, "error": "Unexpected output"}
                else:
                    status["nodes"][node_id] = {"reachable": False, "error": result.stderr[:100] if result.stderr else "SSH failed"}
            except subprocess.TimeoutExpired:
                status["nodes"][node_id] = {"reachable": False, "error": "Timeout"}
            except Exception as e:
                status["nodes"][node_id] = {"reachable": False, "error": str(e)}

        return status

    def execute_cluster_bash(
        self,
        command: str,
        requires_os: Optional[str] = None,
        requires_arch: Optional[str] = None,
        auto_route: bool = True
    ) -> Dict:
        """
        Execute bash command with cluster-aware routing

        Args:
            command: Bash command to execute
            requires_os: Required OS (linux/darwin)
            requires_arch: Required architecture (x86_64/arm64)
            auto_route: Auto-route based on load (default: True)

        Returns:
            Execution result with node info
        """
        # Determine if should offload
        if auto_route and self.should_offload(command):
            # Submit to cluster
            task_def = {
                "type": "shell",
                "command": command,
                "requires_os": requires_os,
                "requires_arch": requires_arch,
                "priority": 5,
                "metadata": {
                    "source": "cluster-execution-mcp",
                    "auto_routed": True
                }
            }

            task_id = self.router.submit_task(task_def)
            result = self.router.wait_for_result(task_id, timeout=300)

            return {
                "success": result["status"] == "completed",
                "executed_on": result.get("assigned_to", "unknown"),
                "stdout": result.get("result", "") or "",
                "stderr": result.get("error", "") or "",
                "return_code": 0 if result["status"] == "completed" else 1,
                "auto_routed": True,
                "task_id": task_id
            }
        else:
            # Execute locally
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "executed_on": self.local_node_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "auto_routed": False
            }

    def offload_to_node(self, command: str, node_id: str) -> Dict:
        """Explicitly route command to specific node"""
        if node_id not in CLUSTER_NODES:
            return {
                "success": False,
                "error": f"Unknown node: {node_id}. Available: {list(CLUSTER_NODES.keys())}"
            }

        # Submit to specific node
        task_def = {
            "type": "shell",
            "command": command,
            "force_node": node_id,  # Force to specific node
            "priority": 5
        }

        task_id = self.router.submit_task(task_def)
        result = self.router.wait_for_result(task_id, timeout=300)

        return {
            "success": result["status"] == "completed",
            "executed_on": result.get("assigned_to", node_id),
            "stdout": result.get("result", "") or "",
            "stderr": result.get("error", "") or "",
            "return_code": 0 if result["status"] == "completed" else 1,
            "task_id": task_id
        }

    def parallel_execute(self, commands: List[str]) -> List[Dict]:
        """Execute multiple commands in parallel across cluster"""
        task_ids = []

        for cmd in commands:
            task_def = {
                "type": "shell",
                "command": cmd,
                "priority": 5
            }
            task_id = self.router.submit_task(task_def)
            task_ids.append((task_id, cmd))

        # Wait for all to complete
        results = []
        for task_id, cmd in task_ids:
            result = self.router.wait_for_result(task_id, timeout=300)
            results.append({
                "command": cmd,
                "success": result["status"] == "completed",
                "executed_on": result.get("assigned_to", "unknown"),
                "stdout": result.get("result", "") or "",
                "stderr": result.get("error", "") or "",
                "task_id": task_id
            })

        return results


# Create MCP server
app = Server("cluster-execution")
cluster = ClusterExecutionServer()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available cluster execution and node chat tools"""
    tools = [
        Tool(
            name="cluster_bash",
            description="""Execute bash command with automatic cluster routing.

Commands are automatically routed to optimal nodes based on:
- Current cluster load (CPU, memory, load average)
- Command characteristics (build/test/compile patterns)
- Node capabilities (OS, architecture)

Heavy commands (make, cargo, pytest, docker, etc.) are automatically offloaded.
Simple commands (ls, cat, echo) run locally for speed.

Parameters:
- command (required): Bash command to execute
- requires_os (optional): Force specific OS (linux/darwin)
- requires_arch (optional): Force specific architecture (x86_64/arm64)
- auto_route (optional): Enable auto-routing (default: true)

Returns execution result with node info and output.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute"
                    },
                    "requires_os": {
                        "type": "string",
                        "description": "Required OS: linux or darwin",
                        "enum": ["linux", "darwin"]
                    },
                    "requires_arch": {
                        "type": "string",
                        "description": "Required architecture: x86_64 or arm64",
                        "enum": ["x86_64", "arm64"]
                    },
                    "auto_route": {
                        "type": "boolean",
                        "description": "Enable automatic routing based on load",
                        "default": True
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="cluster_status",
            description="""Get current cluster status and load distribution.

Shows real-time metrics for all cluster nodes:
- CPU usage percentage
- Memory usage percentage
- 1-minute load average
- Active task count
- Health status (healthy/overloaded)
- Reachability

Use this to:
- Check cluster health before heavy operations
- Determine optimal node for manual routing
- Debug cluster connectivity issues
- Monitor distributed execution

Returns JSON with status for each node.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="offload_to",
            description="""Explicitly route command to specific cluster node.

Use when you need to:
- Run Linux-specific commands → offload to macpro51
- Test on specific architecture
- Balance load manually
- Debug node-specific issues

Available nodes:
- macpro51: Linux x86_64 builder (docker, podman, compilation)
- mac-studio: macOS ARM64 orchestrator
- macbook-air: macOS ARM64 researcher

Parameters:
- command (required): Bash command to execute
- node_id (required): Target node ID

Returns execution result from specified node.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute"
                    },
                    "node_id": {
                        "type": "string",
                        "description": "Target node ID",
                        "enum": ["macpro51", "mac-studio", "macbook-air"]
                    }
                },
                "required": ["command", "node_id"]
            }
        ),
        Tool(
            name="parallel_execute",
            description="""Execute multiple commands in parallel across cluster.

Distributes commands across available nodes for maximum parallelism.
Use for:
- Running test suites across multiple files
- Parallel builds
- Batch processing
- Load testing

Commands are automatically distributed based on node availability and load.

Parameters:
- commands (required): List of bash commands to execute in parallel

Returns list of results, one per command, with execution details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of bash commands to execute in parallel"
                    }
                },
                "required": ["commands"]
            }
        ),
        Tool(
            name="curriculum_sync_push",
            description="""Push local curriculum learning state to cluster shared memory.

Enables federated learning by sharing your node's curriculum progress with
other cluster nodes. Each node contributes observations and accuracy data
that gets aggregated across the cluster.

What gets synced:
- Current curriculum stage (bootstrap/foundation/refinement/mastery/maintenance)
- Observation count and accuracy
- Per-detector accuracy (security_threat, production_violation, etc.)
- Stage transition history

Returns sync status with current local curriculum state.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="curriculum_sync_pull",
            description="""Pull and merge curriculum learning from cluster nodes.

Performs federated aggregation of curriculum state from all nodes:
- Weighted average of detector accuracy (by observation count)
- Considers stage advancement if cluster is ahead
- Blends local and cluster values (70% local, 30% cluster)

This enables your node to benefit from learning across the entire cluster.

Returns merge status with contributing nodes and merged accuracy.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="curriculum_cluster_status",
            description="""Get cluster-wide curriculum learning status.

Shows aggregated view of curriculum progress across all nodes:
- Per-node stage, observations, and accuracy
- Stage distribution across cluster
- Most advanced node
- Total observations across cluster
- Average accuracy

Use this to monitor federated learning progress and identify
which nodes are contributing most to curriculum advancement.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

    # Add node chat tools if available
    if NODE_CHAT_AVAILABLE:
        tools.extend(get_node_chat_tools())

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        if name == "cluster_bash":
            result = cluster.execute_cluster_bash(
                command=arguments["command"],
                requires_os=arguments.get("requires_os"),
                requires_arch=arguments.get("requires_arch"),
                auto_route=arguments.get("auto_route", True)
            )

            output = f"""Executed on: {result['executed_on']}
Auto-routed: {result.get('auto_routed', False)}
Success: {result['success']}
Return Code: {result['return_code']}

STDOUT:
{result['stdout']}

STDERR:
{result['stderr']}"""

            return [TextContent(type="text", text=output)]

        elif name == "cluster_status":
            status = cluster.get_cluster_status()

            output = f"""Cluster Status - Local Node: {status['local_node']}

"""
            for node_id, metrics in status['nodes'].items():
                if metrics.get('reachable', True):
                    indicator = "🔥" if metrics['status'] == "overloaded" else "✅"
                    output += f"""{indicator} {node_id}:
  CPU: {metrics['cpu_percent']:.1f}%
  Memory: {metrics['memory_percent']:.1f}%
  Load (1m): {metrics['load_1m']:.2f}
  Status: {metrics['status']}

"""
                else:
                    output += f"❌ {node_id}: UNREACHABLE\n\n"

            return [TextContent(type="text", text=output)]

        elif name == "offload_to":
            result = cluster.offload_to_node(
                command=arguments["command"],
                node_id=arguments["node_id"]
            )

            if not result['success'] and 'error' in result:
                return [TextContent(type="text", text=f"Error: {result['error']}")]

            output = f"""Executed on: {result['executed_on']}
Success: {result['success']}
Return Code: {result['return_code']}

STDOUT:
{result['stdout']}

STDERR:
{result['stderr']}"""

            return [TextContent(type="text", text=output)]

        elif name == "parallel_execute":
            results = cluster.parallel_execute(arguments["commands"])

            output = f"Parallel Execution Results ({len(results)} commands):\n\n"
            for i, result in enumerate(results, 1):
                status_icon = "✅" if result['success'] else "❌"
                output += f"""{status_icon} Command {i}: {result['command'][:60]}...
  Executed on: {result['executed_on']}
  STDOUT: {result['stdout'][:200]}...

"""

            return [TextContent(type="text", text=output)]

        # Curriculum sync tools (Priority 3 AGI Gap Fix)
        elif name == "curriculum_sync_push":
            if not CURRICULUM_SYNC_AVAILABLE:
                return [TextContent(type="text", text="Error: Cluster curriculum sync not available")]

            result = push_curriculum_to_cluster()

            if result.get('success'):
                output = f"""Curriculum Pushed to Cluster

Node: {result.get('node_id', 'unknown')}
Stage: {result.get('stage', 'unknown')}
Observations: {result.get('observations', 0)}
Accuracy: {result.get('accuracy', 'N/A')}

Local curriculum state has been synced to cluster shared memory."""
            else:
                output = f"Push failed: {result.get('error', 'Unknown error')}"

            return [TextContent(type="text", text=output)]

        elif name == "curriculum_sync_pull":
            if not CURRICULUM_SYNC_AVAILABLE:
                return [TextContent(type="text", text="Error: Cluster curriculum sync not available")]

            result = pull_curriculum_from_cluster()

            if result.get('success'):
                output = f"""Curriculum Pulled from Cluster

Merged from {result.get('merged_from_nodes', 0)} nodes
Contributing nodes: {', '.join(result.get('contributing_nodes', []))}
Merged accuracy: {result.get('merged_accuracy', 'N/A')}
Total observations: {result.get('total_observations', 0)}
Local stage: {result.get('local_stage', 'unknown')}

Federated learning state has been merged into local curriculum."""
            else:
                output = f"Pull failed: {result.get('error', 'Unknown error')}"

            return [TextContent(type="text", text=output)]

        elif name == "curriculum_cluster_status":
            if not CURRICULUM_SYNC_AVAILABLE:
                return [TextContent(type="text", text="Error: Cluster curriculum sync not available")]

            status = get_cluster_curriculum_status()

            if status.get('cluster_nodes', 0) == 0:
                return [TextContent(type="text", text="No cluster curriculum data found. Push from nodes first.")]

            output = f"""Cluster Curriculum Status

Total nodes: {status.get('cluster_nodes', 0)}
Total observations: {status.get('total_observations', 0)}
Average accuracy: {status.get('average_accuracy', 'N/A')}
Most advanced node: {status.get('most_advanced_node', 'N/A')}
Most advanced stage: {status.get('most_advanced_stage', 'N/A')}

Stage distribution: {json.dumps(status.get('stage_distribution', {}), indent=2)}

Node Details:
"""
            for node in status.get('nodes', []):
                output += f"""  {node['node_id']}: {node['stage']}
    Observations: {node['observations']}
    Accuracy: {node['accuracy']}
    Last sync: {node['last_sync']}

"""

            return [TextContent(type="text", text=output)]

        # Check if it's a node chat tool
        elif NODE_CHAT_AVAILABLE:
            # Get list of node chat tool names
            node_chat_tool_names = [t.name for t in get_node_chat_tools()]
            if name in node_chat_tool_names:
                return await handle_node_chat_tool(name, arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
