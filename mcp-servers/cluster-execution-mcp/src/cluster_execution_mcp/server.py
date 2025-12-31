#!/usr/bin/env python3
"""
Cluster Execution MCP Server

Provides cluster-aware command execution for Claude Code.
Automatically routes commands to optimal nodes based on:
- Current cluster load
- Command characteristics
- Node capabilities

Tools:
- cluster_bash: Execute bash commands across cluster (auto-routing)
- cluster_status: Get current cluster state
- offload_to: Explicitly route to specific node
- parallel_execute: Run commands in parallel across nodes
"""

import asyncio
import json
import shlex
import subprocess
from typing import Optional, List, Dict, Any

import psutil
from mcp.server.fastmcp import FastMCP

from .config import (
    config,
    logger,
    CLUSTER_NODES,
    get_node,
    get_available_nodes,
    validate_node_id,
    validate_command,
    should_offload_command,
)
from .router import (
    DistributedTaskRouter,
    get_node_ip,
    verify_ssh_connectivity,
)


# =============================================================================
# MCP Server Setup
# =============================================================================

mcp = FastMCP("cluster-execution")


# =============================================================================
# Server Class
# =============================================================================

class ClusterExecutionServer:
    """MCP Server for cluster-aware execution."""

    def __init__(self):
        self._router: Optional[DistributedTaskRouter] = None

    @property
    def router(self) -> DistributedTaskRouter:
        """Lazy initialization of router."""
        if self._router is None:
            self._router = DistributedTaskRouter()
        return self._router

    @property
    def local_node_id(self) -> str:
        """Get local node ID."""
        return self.router.local_node_id

    def is_overloaded(self) -> bool:
        """Check if local node is overloaded."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            load = psutil.getloadavg()[0]
            memory = psutil.virtual_memory().percent
            return (
                cpu > config.cpu_threshold or
                load > config.load_threshold or
                memory > config.memory_threshold
            )
        except (OSError, AttributeError):
            return False

    def should_offload(self, command: str) -> bool:
        """Determine if command should be offloaded based on characteristics."""
        # Check command patterns first
        if should_offload_command(command):
            return True

        # Check current load
        return self.is_overloaded()

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status with metrics."""
        status: Dict[str, Any] = {
            "local_node": self.local_node_id,
            "nodes": {}
        }

        # Get local metrics
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            load = psutil.getloadavg()[0]

            status["nodes"][self.local_node_id] = {
                "cpu_percent": round(cpu, 1),
                "memory_percent": round(memory, 1),
                "load_1m": round(load, 2),
                "status": "overloaded" if self.is_overloaded() else "healthy",
                "reachable": True
            }
        except (OSError, AttributeError) as e:
            logger.error(f"Failed to get local metrics: {e}")
            status["nodes"][self.local_node_id] = {
                "error": str(e),
                "reachable": True
            }

        # Get remote metrics via SSH
        for node_id, node in CLUSTER_NODES.items():
            if node_id == self.local_node_id:
                continue

            node_ip = get_node_ip(node_id)
            if not node_ip:
                status["nodes"][node_id] = {"reachable": False, "error": "Cannot resolve IP"}
                continue

            try:
                # SECURITY: Using list arguments with proper shell quoting
                # The remote command must be a single argument to SSH with proper escaping
                # so the remote shell doesn't interpret semicolons as command separators
                metrics_script = (
                    "import psutil, os; "
                    "print(psutil.cpu_percent()); "
                    "print(psutil.virtual_memory().percent); "
                    "print(os.getloadavg()[0])"
                )
                # Quote the script for safe shell transport
                remote_cmd = f"python3 -c {shlex.quote(metrics_script)}"

                result = subprocess.run(
                    [
                        "ssh",
                        "-o", f"ConnectTimeout={config.status_timeout}",
                        "-o", "StrictHostKeyChecking=accept-new",
                        "-o", "BatchMode=yes",
                        f"{config.ssh_user}@{node_ip}",
                        remote_cmd
                    ],
                    capture_output=True,
                    text=True,
                    timeout=config.status_timeout + 2
                )

                if result.returncode == 0:
                    # Get last line to skip shell startup messages (e.g., "Cluster environment loaded...")
                    lines = result.stdout.strip().split('\n')
                    last_line = lines[-1] if lines else ""
                    parts = last_line.split()

                    if len(parts) >= 3:
                        try:
                            cpu = float(parts[0])
                            memory = float(parts[1])
                            load = float(parts[2])

                            is_overloaded = (
                                cpu > config.cpu_threshold or
                                memory > config.memory_threshold or
                                load > config.load_threshold
                            )

                            status["nodes"][node_id] = {
                                "cpu_percent": round(cpu, 1),
                                "memory_percent": round(memory, 1),
                                "load_1m": round(load, 2),
                                "status": "overloaded" if is_overloaded else "healthy",
                                "reachable": True
                            }
                        except ValueError as e:
                            status["nodes"][node_id] = {
                                "reachable": True,
                                "error": f"Parse error: {e}, output: {last_line[:100]}"
                            }
                    else:
                        status["nodes"][node_id] = {
                            "reachable": True,
                            "error": f"Unexpected output format: {last_line[:100]}"
                        }
                else:
                    status["nodes"][node_id] = {
                        "reachable": False,
                        "error": result.stderr[:200] if result.stderr else "SSH failed"
                    }

            except subprocess.TimeoutExpired:
                status["nodes"][node_id] = {"reachable": False, "error": "Timeout"}
            except subprocess.SubprocessError as e:
                status["nodes"][node_id] = {"reachable": False, "error": str(e)}
            except ValueError as e:
                status["nodes"][node_id] = {"reachable": True, "error": f"Parse error: {e}"}
            except OSError as e:
                status["nodes"][node_id] = {"reachable": False, "error": str(e)}

        return status

    def execute_local(self, command: str) -> Dict[str, Any]:
        """Execute command locally."""
        valid, error = validate_command(command)
        if not valid:
            return {
                "success": False,
                "error": error,
                "executed_on": self.local_node_id
            }

        try:
            # For complex shell commands, use shell=True
            if any(c in command for c in ['|', '&&', '||', ';', '`', '$(']):
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=config.command_timeout
                )
            else:
                # Simple command - parse and execute without shell
                cmd_parts = shlex.split(command)
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=config.command_timeout
                )

            return {
                "success": result.returncode == 0,
                "executed_on": self.local_node_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "auto_routed": False
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "executed_on": self.local_node_id,
                "error": f"Command timed out after {config.command_timeout}s",
                "auto_routed": False
            }
        except subprocess.SubprocessError as e:
            return {
                "success": False,
                "executed_on": self.local_node_id,
                "error": str(e),
                "auto_routed": False
            }
        except OSError as e:
            return {
                "success": False,
                "executed_on": self.local_node_id,
                "error": str(e),
                "auto_routed": False
            }

    def execute_cluster_bash(
        self,
        command: str,
        requires_os: Optional[str] = None,
        requires_arch: Optional[str] = None,
        auto_route: bool = True
    ) -> Dict[str, Any]:
        """Execute bash command with cluster-aware routing."""
        # Validate command
        valid, error = validate_command(command)
        if not valid:
            return {"success": False, "error": error}

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

            try:
                task_id = self.router.submit_task(task_def)
                result = self.router.wait_for_result(task_id)

                if result:
                    return {
                        "success": result["status"] == "completed",
                        "executed_on": result.get("assigned_to", "unknown"),
                        "stdout": result.get("result", ""),
                        "stderr": result.get("error", ""),
                        "return_code": 0 if result["status"] == "completed" else 1,
                        "auto_routed": True,
                        "task_id": task_id
                    }
                else:
                    return {
                        "success": False,
                        "error": "Task timed out",
                        "task_id": task_id
                    }
            except ValueError as e:
                return {"success": False, "error": str(e)}
        else:
            # Execute locally
            return self.execute_local(command)

    def offload_to_node(self, command: str, node_id: str) -> Dict[str, Any]:
        """Explicitly route command to specific node."""
        # Validate node
        valid, error = validate_node_id(node_id)
        if not valid:
            return {"success": False, "error": error}

        # Validate command
        valid, error = validate_command(command)
        if not valid:
            return {"success": False, "error": error}

        # Get node IP
        node_ip = get_node_ip(node_id)
        if not node_ip:
            return {
                "success": False,
                "error": f"Cannot resolve IP for node: {node_id}"
            }

        try:
            # SECURITY: Using list arguments
            result = subprocess.run(
                [
                    "ssh",
                    "-o", f"ConnectTimeout={config.ssh_connect_timeout}",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes",
                    f"{config.ssh_user}@{node_ip}",
                    command
                ],
                capture_output=True,
                text=True,
                timeout=config.command_timeout
            )

            return {
                "success": result.returncode == 0,
                "executed_on": node_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "executed_on": node_id,
                "error": f"Command timed out after {config.command_timeout}s"
            }
        except subprocess.SubprocessError as e:
            return {"success": False, "executed_on": node_id, "error": str(e)}
        except OSError as e:
            return {"success": False, "executed_on": node_id, "error": str(e)}

    async def parallel_execute(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple commands in parallel across cluster."""
        # Validate all commands first
        for cmd in commands:
            valid, error = validate_command(cmd)
            if not valid:
                return [{"success": False, "error": f"Invalid command: {error}"}]

        # Distribute across nodes
        nodes = list(CLUSTER_NODES.keys())
        results: List[Dict[str, Any]] = []

        # Use asyncio for parallel execution
        async def execute_one(cmd: str, idx: int) -> Dict[str, Any]:
            # Round-robin node selection
            target_node = nodes[idx % len(nodes)]
            node_ip = get_node_ip(target_node)

            if not node_ip:
                return {
                    "command": cmd,
                    "success": False,
                    "error": f"Cannot resolve IP for {target_node}"
                }

            try:
                proc = await asyncio.create_subprocess_exec(
                    "ssh",
                    "-o", f"ConnectTimeout={config.ssh_connect_timeout}",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes",
                    f"{config.ssh_user}@{node_ip}",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=config.command_timeout
                    )

                    return {
                        "command": cmd,
                        "success": proc.returncode == 0,
                        "executed_on": target_node,
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "return_code": proc.returncode
                    }
                except asyncio.TimeoutError:
                    proc.kill()
                    return {
                        "command": cmd,
                        "success": False,
                        "executed_on": target_node,
                        "error": "Timeout"
                    }

            except OSError as e:
                return {
                    "command": cmd,
                    "success": False,
                    "executed_on": target_node,
                    "error": str(e)
                }

        # Execute all in parallel
        tasks = [execute_one(cmd, i) for i, cmd in enumerate(commands)]
        results = await asyncio.gather(*tasks)

        return list(results)


# Global server instance
_server: Optional[ClusterExecutionServer] = None


def get_server() -> ClusterExecutionServer:
    """Get or create server instance."""
    global _server
    if _server is None:
        _server = ClusterExecutionServer()
    return _server


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
async def cluster_bash(
    command: str,
    requires_os: Optional[str] = None,
    requires_arch: Optional[str] = None,
    auto_route: bool = True
) -> str:
    """
    Execute bash command with automatic cluster routing.

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

    Returns execution result with node info and output.
    """
    server = get_server()
    result = server.execute_cluster_bash(
        command=command,
        requires_os=requires_os,
        requires_arch=requires_arch,
        auto_route=auto_route
    )

    return json.dumps(result, indent=2)


@mcp.tool()
async def cluster_status() -> str:
    """
    Get current cluster status and load distribution.

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

    Returns JSON with status for each node.
    """
    server = get_server()
    status = server.get_cluster_status()
    return json.dumps(status, indent=2)


@mcp.tool()
async def offload_to(command: str, node_id: str) -> str:
    """
    Explicitly route command to specific cluster node.

    Use when you need to:
    - Run Linux-specific commands -> offload to macpro51
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

    Returns execution result from specified node.
    """
    server = get_server()
    result = server.offload_to_node(command=command, node_id=node_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def parallel_execute(commands: List[str]) -> str:
    """
    Execute multiple commands in parallel across cluster.

    Distributes commands across available nodes for maximum parallelism.
    Use for:
    - Running test suites across multiple files
    - Parallel builds
    - Batch processing
    - Load testing

    Commands are automatically distributed based on node availability and load.

    Parameters:
    - commands (required): List of bash commands to execute in parallel

    Returns list of results, one per command, with execution details.
    """
    server = get_server()
    results = await server.parallel_execute(commands)
    return json.dumps(results, indent=2)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the MCP server."""
    logger.info("Starting Cluster Execution MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
