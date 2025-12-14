"""Tests for cluster_execution_mcp.config module."""

import os
import pytest
from unittest.mock import patch


class TestClusterConfig:
    """Tests for ClusterConfig dataclass."""

    def test_default_ssh_user(self):
        """Test default SSH user is set from environment."""
        from cluster_execution_mcp.config import ClusterConfig
        config = ClusterConfig()
        # Should use env var or default
        assert config.ssh_user in ["testuser", "marc"]

    def test_default_timeouts(self):
        """Test default timeout values."""
        from cluster_execution_mcp.config import ClusterConfig
        config = ClusterConfig()
        assert config.ssh_timeout >= 2
        assert config.ssh_connect_timeout >= 2
        assert config.command_timeout >= 10

    def test_default_thresholds(self):
        """Test default threshold values."""
        from cluster_execution_mcp.config import ClusterConfig
        config = ClusterConfig()
        assert 0 < config.cpu_threshold <= 100
        assert config.load_threshold > 0
        assert 0 < config.memory_threshold <= 100


class TestClusterNodes:
    """Tests for cluster node definitions."""

    def test_cluster_nodes_defined(self):
        """Test that cluster nodes are properly defined."""
        from cluster_execution_mcp.config import CLUSTER_NODES
        assert len(CLUSTER_NODES) >= 3
        assert "macpro51" in CLUSTER_NODES
        assert "mac-studio" in CLUSTER_NODES

    def test_node_has_required_fields(self):
        """Test that nodes have all required fields."""
        from cluster_execution_mcp.config import CLUSTER_NODES
        for node_id, node in CLUSTER_NODES.items():
            assert node.node_id == node_id
            assert node.hostname
            assert node.fallback_ip
            assert node.os in ["linux", "macos"]
            assert node.arch in ["x86_64", "arm64"]
            assert isinstance(node.capabilities, list)
            assert isinstance(node.specialties, list)

    def test_get_node_valid(self):
        """Test get_node with valid node ID."""
        from cluster_execution_mcp.config import get_node
        node = get_node("macpro51")
        assert node is not None
        assert node.os == "linux"

    def test_get_node_invalid(self):
        """Test get_node with invalid node ID."""
        from cluster_execution_mcp.config import get_node
        node = get_node("nonexistent")
        assert node is None

    def test_get_available_nodes(self):
        """Test get_available_nodes returns list."""
        from cluster_execution_mcp.config import get_available_nodes
        nodes = get_available_nodes()
        assert isinstance(nodes, list)
        assert "macpro51" in nodes

    def test_get_nodes_by_capability(self):
        """Test filtering nodes by capability."""
        from cluster_execution_mcp.config import get_nodes_by_capability
        docker_nodes = get_nodes_by_capability("docker")
        assert len(docker_nodes) >= 1
        for node in docker_nodes:
            assert "docker" in [c.lower() for c in node.capabilities]

    def test_get_nodes_by_os(self):
        """Test filtering nodes by OS."""
        from cluster_execution_mcp.config import get_nodes_by_os
        linux_nodes = get_nodes_by_os("linux")
        assert len(linux_nodes) >= 1
        for node in linux_nodes:
            assert node.os == "linux"

    def test_get_nodes_by_os_darwin_alias(self):
        """Test that darwin is aliased to macos."""
        from cluster_execution_mcp.config import get_nodes_by_os
        darwin_nodes = get_nodes_by_os("darwin")
        macos_nodes = get_nodes_by_os("macos")
        assert len(darwin_nodes) == len(macos_nodes)


class TestNodeMatching:
    """Tests for ClusterNode.matches_requirements."""

    def test_matches_no_requirements(self):
        """Test node matches when no requirements specified."""
        from cluster_execution_mcp.config import get_node
        node = get_node("macpro51")
        assert node.matches_requirements()

    def test_matches_os_requirement(self):
        """Test OS requirement matching."""
        from cluster_execution_mcp.config import get_node
        linux_node = get_node("macpro51")
        assert linux_node.matches_requirements(requires_os="linux")
        assert not linux_node.matches_requirements(requires_os="macos")

    def test_matches_arch_requirement(self):
        """Test architecture requirement matching."""
        from cluster_execution_mcp.config import get_node
        linux_node = get_node("macpro51")
        assert linux_node.matches_requirements(requires_arch="x86_64")
        assert not linux_node.matches_requirements(requires_arch="arm64")

    def test_matches_capabilities(self):
        """Test capability requirement matching."""
        from cluster_execution_mcp.config import get_node
        node = get_node("macpro51")
        assert node.matches_requirements(requires_capabilities=["docker"])
        assert not node.matches_requirements(requires_capabilities=["nonexistent"])

    def test_matches_darwin_alias(self):
        """Test darwin is handled as macos."""
        from cluster_execution_mcp.config import get_node
        mac_node = get_node("mac-studio")
        assert mac_node.matches_requirements(requires_os="darwin")
        assert mac_node.matches_requirements(requires_os="macos")


class TestValidation:
    """Tests for validation functions."""

    def test_validate_node_id_valid(self):
        """Test validation of valid node ID."""
        from cluster_execution_mcp.config import validate_node_id
        valid, error = validate_node_id("macpro51")
        assert valid is True
        assert error is None

    def test_validate_node_id_invalid(self):
        """Test validation of invalid node ID."""
        from cluster_execution_mcp.config import validate_node_id
        valid, error = validate_node_id("nonexistent")
        assert valid is False
        assert "Unknown node" in error

    def test_validate_command_valid(self):
        """Test validation of valid command."""
        from cluster_execution_mcp.config import validate_command
        valid, error = validate_command("ls -la")
        assert valid is True
        assert error is None

    def test_validate_command_empty(self):
        """Test validation of empty command."""
        from cluster_execution_mcp.config import validate_command
        valid, error = validate_command("")
        assert valid is False
        assert "empty" in error.lower()

    def test_validate_command_dangerous(self):
        """Test validation rejects dangerous patterns."""
        from cluster_execution_mcp.config import validate_command
        valid, error = validate_command("rm -rf /")
        assert valid is False
        assert "dangerous" in error.lower()

    def test_validate_ip_valid(self):
        """Test validation of valid IP."""
        from cluster_execution_mcp.config import validate_ip
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.10.10.10") is True

    def test_validate_ip_invalid_format(self):
        """Test validation of invalid IP format."""
        from cluster_execution_mcp.config import validate_ip
        assert validate_ip("not.an.ip") is False
        assert validate_ip("256.1.1.1") is False

    def test_validate_ip_rejects_loopback(self):
        """Test validation rejects loopback addresses."""
        from cluster_execution_mcp.config import validate_ip
        assert validate_ip("127.0.0.1") is False

    def test_validate_ip_rejects_docker(self):
        """Test validation rejects Docker bridge IPs."""
        from cluster_execution_mcp.config import validate_ip
        assert validate_ip("172.17.0.1") is False

    def test_validate_ip_rejects_link_local(self):
        """Test validation rejects link-local addresses."""
        from cluster_execution_mcp.config import validate_ip
        assert validate_ip("169.254.1.1") is False


class TestOffloadPatterns:
    """Tests for offload pattern detection."""

    def test_should_offload_build_commands(self):
        """Test that build commands are offloaded."""
        from cluster_execution_mcp.config import should_offload_command
        assert should_offload_command("make all")
        assert should_offload_command("cargo build")
        assert should_offload_command("npm install")

    def test_should_not_offload_simple_commands(self):
        """Test that simple commands stay local."""
        from cluster_execution_mcp.config import should_offload_command
        assert not should_offload_command("ls -la")
        assert not should_offload_command("pwd")
        assert not should_offload_command("cat file.txt")

    def test_should_offload_test_commands(self):
        """Test that test commands are offloaded."""
        from cluster_execution_mcp.config import should_offload_command
        assert should_offload_command("pytest tests/")
        assert should_offload_command("npm test")
