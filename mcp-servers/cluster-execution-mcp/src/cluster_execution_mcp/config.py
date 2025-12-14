#!/usr/bin/env python3
"""
Configuration module for Cluster Execution MCP Server.

Centralizes all configuration, environment variables, and cluster topology.

Cluster Topology (Marc's Agentic System):
- macpro51 (builder): Linux x86_64 - compilation, testing, containers
- mac-studio (orchestrator): macOS ARM64 - coordination, temporal workflows
- macbook-air (researcher): macOS ARM64 - research, documentation
"""
import platform
import socket

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    # Check environment variable first
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()

    # macOS paths
    if system == "Darwin":
        macos_paths = [
            Path("/Volumes/SSDRAID0/agentic-system"),
            Path("/Volumes/FILES/agentic-system"),
            Path.home() / "agentic-system",
        ]
        for path in macos_paths:
            if path.exists():
                return path

    # Linux paths
    elif system == "Linux":
        linux_paths = [
            Path("/mnt/agentic-system"),
            Path("/home/marc/agentic-system"),
            Path.home() / "agentic-system",
        ]
        for path in linux_paths:
            if path.exists():
                return path

    # Fallback to package directory
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# =============================================================================
# Logging Setup
# =============================================================================

LOG_LEVEL = os.getenv("CLUSTER_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger("cluster-execution-mcp")


# =============================================================================
# Environment Configuration
# =============================================================================

@dataclass(frozen=True)
class ClusterConfig:
    """Centralized cluster configuration from environment variables."""

    # SSH Configuration
    ssh_user: str = field(default_factory=lambda: os.getenv("CLUSTER_SSH_USER", "marc"))
    ssh_timeout: int = field(default_factory=lambda: int(os.getenv("CLUSTER_SSH_TIMEOUT", "5")))
    ssh_connect_timeout: int = field(default_factory=lambda: int(os.getenv("CLUSTER_SSH_CONNECT_TIMEOUT", "2")))
    ssh_retries: int = field(default_factory=lambda: int(os.getenv("CLUSTER_SSH_RETRIES", "2")))

    # Load Thresholds
    cpu_threshold: float = field(default_factory=lambda: float(os.getenv("CLUSTER_CPU_THRESHOLD", "40")))
    load_threshold: float = field(default_factory=lambda: float(os.getenv("CLUSTER_LOAD_THRESHOLD", "4")))
    memory_threshold: float = field(default_factory=lambda: float(os.getenv("CLUSTER_MEMORY_THRESHOLD", "80")))

    # Timeouts
    command_timeout: int = field(default_factory=lambda: int(os.getenv("CLUSTER_CMD_TIMEOUT", "300")))
    status_timeout: int = field(default_factory=lambda: int(os.getenv("CLUSTER_STATUS_TIMEOUT", "5")))

    # Cache Settings
    ip_cache_ttl: int = field(default_factory=lambda: int(os.getenv("CLUSTER_IP_CACHE_TTL", "300")))

    # Network (defaults use RFC 5737 TEST-NET for documentation - set CLUSTER_* env vars for real network)
    gateway_ip: str = field(default_factory=lambda: os.getenv("CLUSTER_GATEWAY", "192.0.2.1"))
    dns_server: str = field(default_factory=lambda: os.getenv("CLUSTER_DNS", "8.8.8.8"))

    # Paths
    agentic_system_path: str = field(
        default_factory=lambda: os.getenv("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
    )


# Global config instance
config = ClusterConfig()


# =============================================================================
# Path Configuration
# =============================================================================

def get_data_dir() -> Path:
    """Get data directory for cluster execution."""
    data_dir = Path(config.agentic_system_path) / "databases" / "cluster"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """Get path to task queue database."""
    return get_data_dir() / "task_queue.db"


# =============================================================================
# Cluster Node Definitions
# =============================================================================

class NodeOS(Enum):
    """Operating system types."""
    LINUX = "linux"
    MACOS = "macos"
    DARWIN = "darwin"  # Alias for macos


class NodeArch(Enum):
    """Architecture types."""
    X86_64 = "x86_64"
    ARM64 = "arm64"


@dataclass
class ClusterNode:
    """Definition of a cluster node."""
    node_id: str
    hostname: str
    fallback_ip: str
    os: str
    arch: str
    capabilities: List[str]
    specialties: List[str]
    max_tasks: int
    priority: int  # Lower = higher priority for offloading

    def matches_requirements(
        self,
        requires_os: Optional[str] = None,
        requires_arch: Optional[str] = None,
        requires_capabilities: Optional[List[str]] = None
    ) -> bool:
        """Check if node matches task requirements."""
        # Check OS
        if requires_os:
            # Handle darwin/macos alias
            node_os = self.os.lower()
            required = requires_os.lower()
            if required == "darwin":
                required = "macos"
            if node_os != required:
                return False

        # Check architecture
        if requires_arch and self.arch.lower() != requires_arch.lower():
            return False

        # Check capabilities
        if requires_capabilities:
            node_caps = set(c.lower() for c in self.capabilities)
            required_caps = set(c.lower() for c in requires_capabilities)
            if not required_caps.issubset(node_caps):
                return False

        return True


# =============================================================================
# Cluster Topology - Marc's Agentic System
# =============================================================================
# Uses actual hostnames as primary IDs with real network IPs
# Both hostname and role aliases are supported (e.g., "macpro51" or "builder")

CLUSTER_NODES: Dict[str, ClusterNode] = {
    # Linux Builder Node - macpro51
    "macpro51": ClusterNode(
        node_id="macpro51",
        hostname="macpro51.local",
        fallback_ip=os.getenv("CLUSTER_BUILDER_IP", "192.168.1.27"),
        os="linux",
        arch="x86_64",
        capabilities=["docker", "podman", "raid", "nvme", "compilation", "testing", "tpu", "ollama"],
        specialties=["compilation", "testing", "containerization", "benchmarking", "linux-builds"],
        max_tasks=10,
        priority=3  # Offload target
    ),
    # macOS Orchestrator Node - mac-studio
    "mac-studio": ClusterNode(
        node_id="mac-studio",
        hostname="mac-studio.local",
        fallback_ip=os.getenv("CLUSTER_ORCHESTRATOR_IP", "192.168.1.16"),
        os="macos",
        arch="arm64",
        capabilities=["orchestration", "coordination", "temporal", "mlx-gpu", "arduino", "qdrant"],
        specialties=["orchestration", "coordination", "monitoring", "temporal-workflows"],
        max_tasks=5,
        priority=1  # Keep free - orchestrator
    ),
    # macOS Researcher Node - macbook-air
    "macbook-air": ClusterNode(
        node_id="macbook-air",
        hostname="macbook-air.local",
        fallback_ip=os.getenv("CLUSTER_RESEARCHER_IP", "192.168.1.76"),
        os="macos",
        arch="arm64",
        capabilities=["research", "documentation", "analysis", "mobile"],
        specialties=["research", "documentation", "analysis", "mobile-operations"],
        max_tasks=3,
        priority=2
    ),
}

# =============================================================================
# Node Aliases - Map role names to actual hostnames
# =============================================================================
# Allows using either "builder" or "macpro51" interchangeably

NODE_ALIASES: Dict[str, str] = {
    # Role -> Hostname mappings
    "builder": "macpro51",
    "orchestrator": "mac-studio",
    "researcher": "macbook-air",
    # Self-referential aliases (hostname -> hostname)
    "macpro51": "macpro51",
    "mac-studio": "mac-studio",
    "macbook-air": "macbook-air",
    # Legacy/alternative names
    "linux": "macpro51",
    "studio": "mac-studio",
    "air": "macbook-air",
}


def resolve_node_id(node_id: str) -> str:
    """Resolve node alias to canonical node ID."""
    return NODE_ALIASES.get(node_id.lower(), node_id)


def get_node(node_id: str) -> Optional[ClusterNode]:
    """Get node by ID or alias.

    Supports both actual hostnames (macpro51) and role aliases (builder).
    """
    # Try direct lookup first
    if node_id in CLUSTER_NODES:
        return CLUSTER_NODES[node_id]

    # Try alias resolution
    canonical_id = resolve_node_id(node_id)
    return CLUSTER_NODES.get(canonical_id)


def get_available_nodes() -> List[str]:
    """Get list of available node IDs (actual hostnames)."""
    return list(CLUSTER_NODES.keys())


def get_all_node_aliases() -> Dict[str, str]:
    """Get all node aliases mapping."""
    return NODE_ALIASES.copy()


def get_nodes_by_capability(capability: str) -> List[ClusterNode]:
    """Get nodes that have a specific capability."""
    return [
        node for node in CLUSTER_NODES.values()
        if capability.lower() in [c.lower() for c in node.capabilities]
    ]


def get_nodes_by_os(os_type: str) -> List[ClusterNode]:
    """Get nodes running specific OS."""
    os_type = os_type.lower()
    if os_type == "darwin":
        os_type = "macos"
    return [node for node in CLUSTER_NODES.values() if node.os.lower() == os_type]


# =============================================================================
# Offload Patterns
# =============================================================================

# Commands that should be offloaded
OFFLOAD_PATTERNS = [
    "make", "cargo", "npm", "yarn", "pnpm",
    "pytest", "jest", "mocha", "test",
    "build", "compile", "gcc", "g++", "clang",
    "docker", "podman", "kubectl",
    "rsync", "scp", "tar", "zip", "unzip",
    "find", "grep -r", "rg"
]

# Commands that should run locally (simple/quick)
LOCAL_PATTERNS = ["ls", "pwd", "cd", "echo", "cat", "head", "tail", "which", "type"]


def should_offload_command(command: str) -> bool:
    """Determine if command should be offloaded to another node."""
    cmd_lower = command.lower()

    # Check simple patterns first
    for pattern in LOCAL_PATTERNS:
        if cmd_lower.startswith(pattern):
            return False

    # Check offload patterns
    for pattern in OFFLOAD_PATTERNS:
        if pattern in cmd_lower:
            return True

    return False


# =============================================================================
# Task Status Enum
# =============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# =============================================================================
# Validation Functions
# =============================================================================

def validate_node_id(node_id: str) -> tuple[bool, Optional[str]]:
    """Validate that node_id is known (supports aliases)."""
    # Direct match
    if node_id in CLUSTER_NODES:
        return True, None

    # Try alias resolution
    canonical_id = resolve_node_id(node_id)
    if canonical_id in CLUSTER_NODES:
        return True, None

    available = ", ".join(CLUSTER_NODES.keys())
    aliases = ", ".join(k for k in NODE_ALIASES.keys() if k not in CLUSTER_NODES)
    return False, f"Unknown node: {node_id}. Available: {available} (aliases: {aliases})"


def detect_local_node() -> Optional[str]:
    """Detect which cluster node we're running on."""
    hostname = socket.gethostname().lower()

    # Direct hostname match
    for node_id in CLUSTER_NODES:
        if hostname.startswith(node_id.lower().replace("-", "")):
            return node_id
        if hostname == node_id.lower():
            return node_id

    # Check common hostname patterns
    if "macpro51" in hostname or hostname.startswith("macpro"):
        return "macpro51"
    if "mac-studio" in hostname or "macstudio" in hostname:
        return "mac-studio"
    if "macbook-air" in hostname or "macbookair" in hostname:
        return "macbook-air"

    return None


def get_remote_nodes() -> List[str]:
    """Get list of remote nodes (excluding local node)."""
    local = detect_local_node()
    return [n for n in CLUSTER_NODES.keys() if n != local]


def validate_command(command: str) -> tuple[bool, Optional[str]]:
    """Basic command validation."""
    if not command or not command.strip():
        return False, "Command cannot be empty"

    # Check for dangerous patterns (basic protection)
    dangerous_patterns = [
        "rm -rf /",
        "rm -rf /*",
        "> /dev/sda",
        "dd if=/dev/zero of=/dev/",
        ":(){ :|:& };:",  # Fork bomb
    ]

    cmd_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in cmd_lower:
            return False, f"Command contains dangerous pattern: {pattern}"

    return True, None


def validate_ip(ip: str) -> bool:
    """Validate IP address format."""
    if not ip:
        return False

    # Reject loopback
    if ip.startswith("127."):
        return False

    # Reject Docker/container bridge IPs (172.16-31.x.x)
    if ip.startswith("172."):
        try:
            second_octet = int(ip.split('.')[1])
            if 16 <= second_octet <= 31:
                return False
        except (IndexError, ValueError):
            return False

    # Reject link-local
    if ip.startswith("169.254."):
        return False

    # Reject podman default
    if ip.startswith("10.0."):
        return False

    # Basic format check
    parts = ip.split('.')
    if len(parts) != 4:
        return False

    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
    except ValueError:
        return False

    return True


# =============================================================================
# Export All
# =============================================================================

__all__ = [
    # Configuration
    "config",
    "ClusterConfig",
    "logger",
    # Paths
    "get_data_dir",
    "get_db_path",
    # Nodes
    "CLUSTER_NODES",
    "NODE_ALIASES",
    "ClusterNode",
    "NodeOS",
    "NodeArch",
    "get_node",
    "get_available_nodes",
    "get_all_node_aliases",
    "get_nodes_by_capability",
    "get_nodes_by_os",
    "resolve_node_id",
    "detect_local_node",
    "get_remote_nodes",
    # Patterns
    "OFFLOAD_PATTERNS",
    "LOCAL_PATTERNS",
    "should_offload_command",
    # Status
    "TaskStatus",
    # Validation
    "validate_node_id",
    "validate_command",
    "validate_ip",
]
