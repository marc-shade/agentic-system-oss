"""
Cluster Execution MCP Server

Provides cluster-aware command execution for distributed task routing.
"""

from .config import (
    config,
    ClusterConfig,
    ClusterNode,
    CLUSTER_NODES,
    TaskStatus,
    get_node,
    get_available_nodes,
    get_nodes_by_capability,
    get_nodes_by_os,
    validate_node_id,
    validate_command,
    validate_ip,
    should_offload_command,
)
from .router import (
    DistributedTaskRouter,
    Task,
    get_node_ip,
    get_local_lan_ip,
    resolve_hostname,
    verify_ssh_connectivity,
    clear_ip_cache,
)
from .server import (
    ClusterExecutionServer,
    cluster_bash,
    cluster_status,
    offload_to,
    parallel_execute,
    main,
)

__version__ = "0.2.0"
__all__ = [
    # Config
    "config",
    "ClusterConfig",
    "ClusterNode",
    "CLUSTER_NODES",
    "TaskStatus",
    "get_node",
    "get_available_nodes",
    "get_nodes_by_capability",
    "get_nodes_by_os",
    "validate_node_id",
    "validate_command",
    "validate_ip",
    "should_offload_command",
    # Router
    "DistributedTaskRouter",
    "Task",
    "get_node_ip",
    "get_local_lan_ip",
    "resolve_hostname",
    "verify_ssh_connectivity",
    "clear_ip_cache",
    # Server
    "ClusterExecutionServer",
    "cluster_bash",
    "cluster_status",
    "offload_to",
    "parallel_execute",
    "main",
]
