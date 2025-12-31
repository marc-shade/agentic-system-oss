"""
Arduino Cluster Module
======================

Provides cluster-aware Arduino discovery and access.

When Arduino is moved between nodes, the system automatically
discovers its new location and routes commands appropriately.

Usage:
    from arduino_surface.cluster import ClusterArduinoClient

    # Automatically finds Arduino across cluster
    client = ClusterArduinoClient()
    client.lcd(0, "Hello from any node!")
"""

from .arduino_cluster_discovery import (
    ArduinoClusterDiscovery,
    ArduinoLocation,
    ClusterNode,
    CLUSTER_NODES,
    get_discovery_service,
    discover_arduino,
    get_status,
)

from .arduino_cluster_client import (
    ClusterArduinoClient,
    LocalArduinoClient,
    RemoteArduinoClient,
    get_client,
    lcd,
    led,
    alert,
)

__all__ = [
    # Discovery
    'ArduinoClusterDiscovery',
    'ArduinoLocation',
    'ClusterNode',
    'CLUSTER_NODES',
    'get_discovery_service',
    'discover_arduino',
    'get_status',
    # Client
    'ClusterArduinoClient',
    'LocalArduinoClient',
    'RemoteArduinoClient',
    'get_client',
    'lcd',
    'led',
    'alert',
]
