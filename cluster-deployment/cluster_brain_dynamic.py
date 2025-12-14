#!/usr/bin/env python3
"""
Dynamic Cluster Brain - Uses mDNS discovery for real-time node awareness.
Provides situational awareness for all agents in the cluster.
"""

import os
import platform
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from node_discovery import (
    discover_all, get_node_ip, get_service_url,
    check_node_reachable, CLUSTER_NODES
)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()
DB_PATH = str(_STORAGE_BASE / "databases" / "cluster" / "cluster_brain.db")


class DynamicClusterBrain:
    """Dynamic cluster brain with real-time node discovery."""
    
    def __init__(self):
        self.db_path = DB_PATH
        
    def get_situational_awareness(self) -> Dict:
        """Get complete situational awareness for agents."""
        nodes = discover_all()
        
        awareness = {
            "timestamp": datetime.now().isoformat(),
            "cluster": {
                "total_nodes": len(nodes),
                "online_nodes": sum(1 for n in nodes.values() if n["reachable"]),
                "nodes": {}
            },
            "services": {},
            "capabilities": {
                "inference": False,
                "orchestration": False,
                "research": False,
                "build": False
            }
        }
        
        for node_id, info in nodes.items():
            awareness["cluster"]["nodes"][node_id] = {
                "ip": info["ip"],
                "role": info["role"],
                "online": info["reachable"],
                "services": self._get_node_services(node_id) if info["reachable"] else []
            }
            
            # Track capabilities
            if info["reachable"]:
                if info["role"] == "inference":
                    awareness["capabilities"]["inference"] = True
                    awareness["services"]["ollama"] = get_service_url(node_id, "ollama")
                elif info["role"] == "orchestrator":
                    awareness["capabilities"]["orchestration"] = True
                elif info["role"] == "researcher":
                    awareness["capabilities"]["research"] = True
                elif info["role"] == "builder":
                    awareness["capabilities"]["build"] = True
        
        return awareness
    
    def _get_node_services(self, node_id: str) -> List[str]:
        """Get available services on a node."""
        node = CLUSTER_NODES.get(node_id, {})
        return list(node.get("services", {}).keys())
    
    def route_task(self, task_type: str) -> Optional[Dict]:
        """Route a task to the best available node."""
        awareness = self.get_situational_awareness()
        
        # Task type to role mapping
        routing = {
            "inference": "inference",
            "llm": "inference",
            "embedding": "inference",
            "orchestration": "orchestrator",
            "coordination": "orchestrator",
            "research": "researcher",
            "analysis": "researcher",
            "build": "builder",
            "test": "builder",
            "compile": "builder"
        }
        
        target_role = routing.get(task_type.lower(), "builder")
        
        for node_id, node_info in awareness["cluster"]["nodes"].items():
            if node_info["role"] == target_role and node_info["online"]:
                return {
                    "node_id": node_id,
                    "ip": node_info["ip"],
                    "role": node_info["role"],
                    "services": node_info["services"]
                }
        
        # Fallback to any online node
        for node_id, node_info in awareness["cluster"]["nodes"].items():
            if node_info["online"]:
                return {
                    "node_id": node_id,
                    "ip": node_info["ip"],
                    "role": node_info["role"],
                    "services": node_info["services"],
                    "fallback": True
                }
        
        return None
    
    def get_inference_endpoint(self) -> Optional[str]:
        """Get the LLM inference endpoint URL."""
        return get_service_url("completeu-server", "ollama")
    
    def broadcast_message(self, message: str, from_node: str = "system") -> Dict:
        """Broadcast a message to all online nodes."""
        import requests
        
        results = {}
        nodes = discover_all()
        
        for node_id, info in nodes.items():
            if info["reachable"] and node_id != from_node:
                chat_url = get_service_url(node_id, "chat")
                if chat_url:
                    try:
                        resp = requests.post(
                            f"{chat_url}/message",
                            json={"from": from_node, "content": message},
                            timeout=5
                        )
                        results[node_id] = "sent" if resp.ok else "failed"
                    except Exception as e:
                        results[node_id] = f"error: {e}"
        
        return results


def print_awareness():
    """Print current situational awareness."""
    brain = DynamicClusterBrain()
    awareness = brain.get_situational_awareness()
    
    print("=" * 50)
    print("🌐 CLUSTER SITUATIONAL AWARENESS")
    print("=" * 50)
    print(f"Time: {awareness['timestamp']}")
    print(f"Nodes: {awareness['cluster']['online_nodes']}/{awareness['cluster']['total_nodes']} online")
    print()
    
    print("📍 NODES:")
    for node_id, info in awareness["cluster"]["nodes"].items():
        status = "✅" if info["online"] else "❌"
        print(f"  {status} {node_id} ({info['role']})")
        if info["online"]:
            print(f"     IP: {info['ip']}")
            print(f"     Services: {', '.join(info['services'])}")
    
    print()
    print("🎯 CAPABILITIES:")
    for cap, available in awareness["capabilities"].items():
        status = "✅" if available else "❌"
        print(f"  {status} {cap}")
    
    if awareness["services"].get("ollama"):
        print()
        print(f"🤖 LLM ENDPOINT: {awareness['services']['ollama']}")


if __name__ == "__main__":
    print_awareness()
