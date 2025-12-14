"""Tests for cluster_execution_mcp.server module."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def get_fn(tool):
    """Extract the underlying function from a FastMCP tool."""
    if hasattr(tool, 'fn'):
        return tool.fn
    if hasattr(tool, '__wrapped__'):
        return tool.__wrapped__
    return tool


class TestClusterExecutionServer:
    """Tests for ClusterExecutionServer class."""

    def test_server_lazy_init(self, mock_subprocess, temp_db):
        """Test server lazy initialization."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        # Router should not be initialized yet
        assert server._router is None

        # Access router property
        _ = server.router
        assert server._router is not None

    def test_server_local_node_id(self, mock_subprocess, temp_db):
        """Test getting local node ID."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        assert server.local_node_id is not None

    def test_is_overloaded_false(self, mock_psutil):
        """Test is_overloaded returns False when not overloaded."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        assert server.is_overloaded() is False

    def test_is_overloaded_true(self):
        """Test is_overloaded returns True when overloaded."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.getloadavg", return_value=(10.0, 8.0, 6.0)):
            mock_mem.return_value = MagicMock(percent=90.0)

            server = ClusterExecutionServer()
            server._router = MagicMock()
            assert server.is_overloaded() is True

    def test_should_offload_heavy_command(self, mock_psutil):
        """Test should_offload returns True for heavy commands."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        assert server.should_offload("make all") is True
        assert server.should_offload("cargo build --release") is True

    def test_should_offload_simple_command(self, mock_psutil):
        """Test should_offload returns False for simple commands."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        assert server.should_offload("ls -la") is False
        assert server.should_offload("pwd") is False


class TestExecuteLocal:
    """Tests for local command execution."""

    def test_execute_local_success(self, mock_subprocess, temp_db):
        """Test successful local execution."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        result = server.execute_local("echo hello")

        assert result["success"] is True
        assert result["stdout"] == "test output"

    def test_execute_local_invalid_command(self, temp_db):
        """Test local execution with invalid command."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        result = server.execute_local("")

        assert result["success"] is False
        assert "error" in result

    def test_execute_local_dangerous_command(self, temp_db):
        """Test local execution rejects dangerous commands."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        result = server.execute_local("rm -rf /")

        assert result["success"] is False
        assert "dangerous" in result.get("error", "").lower()

    def test_execute_local_timeout(self, temp_db):
        """Test local execution timeout handling."""
        from cluster_execution_mcp.server import ClusterExecutionServer
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="test", timeout=10)):
            server = ClusterExecutionServer()
            server._router = MagicMock()
            result = server.execute_local("sleep 1000")

            assert result["success"] is False
            assert "timed out" in result.get("error", "").lower()


class TestGetClusterStatus:
    """Tests for cluster status retrieval."""

    def test_get_cluster_status_local_metrics(self, mock_psutil, mock_subprocess, temp_db):
        """Test getting local metrics in cluster status."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        status = server.get_cluster_status()

        assert "local_node" in status
        assert "nodes" in status
        local_node = status["local_node"]
        assert local_node in status["nodes"]
        assert status["nodes"][local_node]["reachable"] is True

    def test_get_cluster_status_remote_unreachable(self, mock_psutil, temp_db):
        """Test handling unreachable remote nodes."""
        from cluster_execution_mcp.server import ClusterExecutionServer
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=5)):
            with patch("cluster_execution_mcp.router.get_node_ip", return_value="192.168.1.100"):
                server = ClusterExecutionServer()
                status = server.get_cluster_status()

                # Should have error for remote nodes
                for node_id, node_status in status["nodes"].items():
                    if node_id != status["local_node"]:
                        assert node_status.get("reachable") is False or "error" in node_status


class TestOffloadToNode:
    """Tests for explicit node offloading."""

    def test_offload_invalid_node(self, temp_db):
        """Test offloading to invalid node."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        result = server.offload_to_node("ls -la", "nonexistent")

        assert result["success"] is False
        assert "Unknown node" in result.get("error", "")

    def test_offload_invalid_command(self, temp_db):
        """Test offloading invalid command."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        server = ClusterExecutionServer()
        server._router = MagicMock()
        result = server.offload_to_node("rm -rf /", "macpro51")

        assert result["success"] is False

    def test_offload_success(self, mock_subprocess, temp_db):
        """Test successful offload to node."""
        from cluster_execution_mcp.server import ClusterExecutionServer

        with patch("cluster_execution_mcp.router.get_node_ip", return_value="192.168.1.183"):
            server = ClusterExecutionServer()
            result = server.offload_to_node("ls -la", "macpro51")

            assert result["success"] is True
            assert result["executed_on"] == "macpro51"


class TestMCPTools:
    """Tests for MCP tool functions."""

    @pytest.mark.asyncio
    async def test_cluster_bash_tool(self, mock_subprocess, mock_psutil, temp_db):
        """Test cluster_bash MCP tool."""
        from cluster_execution_mcp.server import cluster_bash

        fn = get_fn(cluster_bash)
        result_json = await fn(command="echo hello", auto_route=False)
        result = json.loads(result_json)

        assert "success" in result
        assert "executed_on" in result

    @pytest.mark.asyncio
    async def test_cluster_status_tool(self, mock_subprocess, mock_psutil, temp_db):
        """Test cluster_status MCP tool."""
        from cluster_execution_mcp.server import cluster_status

        fn = get_fn(cluster_status)
        result_json = await fn()
        result = json.loads(result_json)

        assert "local_node" in result
        assert "nodes" in result

    @pytest.mark.asyncio
    async def test_offload_to_tool_invalid(self, temp_db):
        """Test offload_to MCP tool with invalid node."""
        from cluster_execution_mcp.server import offload_to, _server

        # Clear server cache
        import cluster_execution_mcp.server as server_module
        server_module._server = None

        fn = get_fn(offload_to)
        result_json = await fn(command="ls", node_id="invalid")
        result = json.loads(result_json)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parallel_execute_tool(self, mock_subprocess, temp_db):
        """Test parallel_execute MCP tool."""
        from cluster_execution_mcp.server import parallel_execute

        with patch("cluster_execution_mcp.router.get_node_ip", return_value="192.168.1.100"):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_exec.return_value = mock_proc

                fn = get_fn(parallel_execute)
                result_json = await fn(commands=["echo a", "echo b"])
                result = json.loads(result_json)

                assert isinstance(result, list)
                assert len(result) == 2


class TestInputValidation:
    """Tests for input validation in tools."""

    @pytest.mark.asyncio
    async def test_cluster_bash_empty_command(self, temp_db):
        """Test cluster_bash rejects empty command."""
        from cluster_execution_mcp.server import cluster_bash

        import cluster_execution_mcp.server as server_module
        server_module._server = None

        fn = get_fn(cluster_bash)
        result_json = await fn(command="", auto_route=False)
        result = json.loads(result_json)

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_parallel_execute_dangerous_command(self, temp_db):
        """Test parallel_execute rejects dangerous commands."""
        from cluster_execution_mcp.server import parallel_execute

        import cluster_execution_mcp.server as server_module
        server_module._server = None

        fn = get_fn(parallel_execute)
        result_json = await fn(commands=["ls", "rm -rf /"])
        result = json.loads(result_json)

        # Should fail validation
        assert len(result) == 1
        assert result[0]["success"] is False
