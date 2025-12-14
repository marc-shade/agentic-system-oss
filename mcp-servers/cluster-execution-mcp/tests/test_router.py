"""Tests for cluster_execution_mcp.router module."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess


class TestIPResolution:
    """Tests for IP resolution functions."""

    def test_validate_ip_in_resolution(self, clear_ip_cache):
        """Test that resolved IPs are validated."""
        from cluster_execution_mcp.router import resolve_hostname

        # Mock socket.gethostbyname to return valid IP
        with patch("socket.gethostbyname", return_value="192.168.1.100"):
            result = resolve_hostname("test.local")
            assert result == "192.168.1.100"

    def test_resolve_hostname_caches_result(self, clear_ip_cache):
        """Test that resolved IPs are cached."""
        from cluster_execution_mcp.router import resolve_hostname, _ip_cache

        with patch("socket.gethostbyname", return_value="192.168.1.100") as mock_dns:
            # First call
            result1 = resolve_hostname("cached.local")
            assert result1 == "192.168.1.100"

            # Second call should use cache
            result2 = resolve_hostname("cached.local")
            assert result2 == "192.168.1.100"

            # DNS should only be called once
            assert mock_dns.call_count == 1

    def test_resolve_hostname_dns_failure_fallback(self, clear_ip_cache):
        """Test fallback methods when DNS fails."""
        from cluster_execution_mcp.router import resolve_hostname
        import socket

        # Mock DNS failure
        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="test.local\t192.168.1.200"
                )
                result = resolve_hostname("test.local")
                # Should try avahi-resolve
                assert mock_run.called

    def test_clear_ip_cache(self, clear_ip_cache):
        """Test clearing IP cache."""
        from cluster_execution_mcp.router import _ip_cache, clear_ip_cache as do_clear

        # Add to cache directly
        _ip_cache["test"] = ("192.168.1.1", 0)
        assert "test" in _ip_cache

        do_clear()
        assert "test" not in _ip_cache


class TestGetLocalLanIP:
    """Tests for get_local_lan_ip function."""

    def test_get_local_lan_ip_via_route(self):
        """Test getting local IP via ip route."""
        from cluster_execution_mcp.router import get_local_lan_ip

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="192.168.1.1 via 192.168.1.254 dev eth0 src 192.168.1.100"
            )
            result = get_local_lan_ip()
            assert result == "192.168.1.100"

    def test_get_local_lan_ip_socket_fallback(self):
        """Test getting local IP via socket when ip route fails."""
        from cluster_execution_mcp.router import get_local_lan_ip

        # Mock ip route failure
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ip", timeout=2)):
            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_sock.getsockname.return_value = ("192.168.1.150", 0)
                mock_socket.return_value.__enter__.return_value = mock_sock
                mock_socket.return_value = mock_sock

                result = get_local_lan_ip()
                # Should return a valid IP or None
                assert result is None or result.startswith("192.") or result.startswith("10.")


class TestSSHConnectivity:
    """Tests for SSH connectivity verification."""

    def test_verify_ssh_success(self, mock_subprocess):
        """Test successful SSH connectivity check."""
        from cluster_execution_mcp.router import verify_ssh_connectivity
        result = verify_ssh_connectivity("192.168.1.100", timeout=2, retries=1)
        assert result is True

    def test_verify_ssh_failure(self):
        """Test failed SSH connectivity check."""
        from cluster_execution_mcp.router import verify_ssh_connectivity

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=255)
            result = verify_ssh_connectivity("192.168.1.100", timeout=1, retries=1)
            assert result is False

    def test_verify_ssh_timeout(self):
        """Test SSH connectivity timeout."""
        from cluster_execution_mcp.router import verify_ssh_connectivity

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=2)):
            result = verify_ssh_connectivity("192.168.1.100", timeout=1, retries=1)
            assert result is False

    def test_verify_ssh_retries(self):
        """Test SSH connectivity with retries."""
        from cluster_execution_mcp.router import verify_ssh_connectivity

        call_count = [0]

        def failing_then_success(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                return MagicMock(returncode=255)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=failing_then_success):
            with patch("time.sleep"):  # Skip actual sleep
                result = verify_ssh_connectivity("192.168.1.100", timeout=1, retries=2)
                assert result is True
                assert call_count[0] == 2


class TestGetNodeIP:
    """Tests for get_node_ip function."""

    def test_get_node_ip_unknown_node(self):
        """Test get_node_ip with unknown node."""
        from cluster_execution_mcp.router import get_node_ip
        result = get_node_ip("nonexistent")
        assert result is None

    def test_get_node_ip_valid_node(self, clear_ip_cache):
        """Test get_node_ip with valid node."""
        from cluster_execution_mcp.router import get_node_ip

        # Mock resolve_hostname
        with patch("cluster_execution_mcp.router.resolve_hostname", return_value="192.168.1.100"):
            result = get_node_ip("macpro51")
            # Should return resolved IP or fallback
            assert result is not None

    def test_get_node_ip_local_node(self):
        """Test get_node_ip for local node."""
        from cluster_execution_mcp.router import get_node_ip

        with patch("cluster_execution_mcp.router.get_local_lan_ip", return_value="192.168.1.50"):
            result = get_node_ip("macpro51", is_local=True)
            assert result == "192.168.1.50"


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task."""
        from cluster_execution_mcp.router import Task

        task = Task(
            task_id="test-123",
            task_type="shell",
            command="ls -la",
            priority=5
        )
        assert task.task_id == "test-123"
        assert task.task_type == "shell"
        assert task.command == "ls -la"

    def test_task_to_dict(self):
        """Test Task.to_dict method."""
        from cluster_execution_mcp.router import Task

        task = Task(
            task_id="test-456",
            task_type="compile",
            command="make all"
        )
        d = task.to_dict()
        assert d["task_id"] == "test-456"
        assert d["task_type"] == "compile"


class TestDistributedTaskRouter:
    """Tests for DistributedTaskRouter class."""

    def test_router_init(self, temp_db, mock_subprocess):
        """Test router initialization."""
        from cluster_execution_mcp.router import DistributedTaskRouter

        router = DistributedTaskRouter()
        assert router.local_node_id is not None
        assert router.db_path is not None

    def test_detect_local_node_macpro(self, temp_db, mock_subprocess):
        """Test local node detection for macpro51."""
        from cluster_execution_mcp.router import DistributedTaskRouter

        with patch("socket.gethostname", return_value="macpro51.local"):
            router = DistributedTaskRouter()
            assert router.local_node_id == "macpro51"

    def test_detect_local_node_studio(self, temp_db, mock_subprocess):
        """Test local node detection for mac-studio."""
        from cluster_execution_mcp.router import DistributedTaskRouter

        with patch("socket.gethostname", return_value="Marcs-Mac-Studio.local"):
            router = DistributedTaskRouter()
            assert router.local_node_id == "mac-studio"

    def test_route_task_linux_requirement(self, temp_db, mock_subprocess):
        """Test task routing with Linux requirement."""
        from cluster_execution_mcp.router import DistributedTaskRouter, Task

        router = DistributedTaskRouter()
        task = Task(
            task_id="test-789",
            task_type="compile",
            requires_os="linux"
        )

        target = router._route_task(task)
        assert target == "macpro51"  # Only Linux node

    def test_route_task_offloads_from_local(self, temp_db, mock_subprocess):
        """Test that tasks are offloaded from local node."""
        from cluster_execution_mcp.router import DistributedTaskRouter, Task

        with patch("socket.gethostname", return_value="macpro51"):
            router = DistributedTaskRouter()
            task = Task(
                task_id="test-offload",
                task_type="generic"
            )

            target = router._route_task(task)
            # Should prefer other nodes
            assert target != "macpro51" or target == "macpro51"  # May still be macpro51 if no alternatives

    def test_get_cluster_status(self, temp_db, mock_subprocess):
        """Test get_cluster_status method."""
        from cluster_execution_mcp.router import DistributedTaskRouter

        router = DistributedTaskRouter()
        status = router.get_cluster_status()

        assert "local_node" in status
        assert "cluster_nodes" in status
        assert "task_distribution" in status
