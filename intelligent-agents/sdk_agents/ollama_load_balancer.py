#!/usr/bin/env python3
"""
Ollama Load Balancer - Distribute inference across cluster nodes

Supports multiple strategies:
- round_robin: Cycle through healthy nodes
- random: Random selection from healthy nodes
- least_loaded: Use node with lowest current load
- local_first: Prefer localhost, fallback to remote

Usage:
    balancer = OllamaLoadBalancer([
        "http://localhost:11434",
        "http://192.168.1.10:11434",  # macbook-air
        "http://192.168.1.11:11434",  # macbook-pro
    ])

    result = balancer.generate(model="llama3.2:3b", prompt="Hello")
"""

import requests
import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class OllamaNode:
    """Represents an Ollama endpoint"""
    endpoint: str
    healthy: bool = True
    last_check: Optional[datetime] = None
    response_time_ms: float = 0
    current_load: int = 0
    consecutive_failures: int = 0


class OllamaLoadBalancer:
    """
    Load balancer for distributed Ollama inference

    Features:
    - Health checking with automatic failover
    - Multiple load balancing strategies
    - Response time tracking
    - Automatic node recovery
    """

    def __init__(
        self,
        endpoints: List[str],
        strategy: str = "round_robin",  # round_robin, random, least_loaded, local_first
        health_check_interval: int = 60,  # seconds
        max_consecutive_failures: int = 3
    ):
        self.nodes = [OllamaNode(endpoint=ep) for ep in endpoints]
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.current_index = 0

    def generate(
        self,
        model: str,
        prompt: str,
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using load balancing

        Args:
            model: Ollama model name
            prompt: Prompt text
            timeout: Request timeout in seconds
            **kwargs: Additional parameters for Ollama API

        Returns:
            Response dict with 'response', 'endpoint_used', 'response_time_ms'
        """
        # Check node health periodically
        self._check_node_health()

        # Get healthy nodes
        healthy_nodes = [n for n in self.nodes if n.healthy]

        if not healthy_nodes:
            raise Exception("No healthy Ollama nodes available")

        # Select node based on strategy
        node = self._select_node(healthy_nodes)

        # Make request
        start_time = time.time()
        try:
            response = requests.post(
                f"{node.endpoint}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=timeout
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # Success - reset failure counter
                node.consecutive_failures = 0
                node.response_time_ms = elapsed_ms
                node.current_load = max(0, node.current_load - 1)

                result = response.json()
                result["endpoint_used"] = node.endpoint
                result["response_time_ms"] = elapsed_ms
                return result
            else:
                # HTTP error
                self._handle_node_failure(node, f"HTTP {response.status_code}")
                raise Exception(f"Ollama HTTP error: {response.status_code}")

        except Exception as e:
            self._handle_node_failure(node, str(e))
            # Try fallback to another node
            if len(healthy_nodes) > 1:
                return self.generate(model, prompt, timeout, **kwargs)
            raise

    def _select_node(self, healthy_nodes: List[OllamaNode]) -> OllamaNode:
        """Select node based on configured strategy"""

        if self.strategy == "round_robin":
            # Cycle through nodes
            node = healthy_nodes[self.current_index % len(healthy_nodes)]
            self.current_index += 1
            node.current_load += 1
            return node

        elif self.strategy == "random":
            # Random selection
            node = random.choice(healthy_nodes)
            node.current_load += 1
            return node

        elif self.strategy == "least_loaded":
            # Choose node with lowest current load
            node = min(healthy_nodes, key=lambda n: n.current_load)
            node.current_load += 1
            return node

        elif self.strategy == "local_first":
            # Prefer localhost, fallback to remote
            localhost_nodes = [n for n in healthy_nodes if "localhost" in n.endpoint or "127.0.0.1" in n.endpoint]
            if localhost_nodes:
                node = localhost_nodes[0]
            else:
                node = healthy_nodes[0]
            node.current_load += 1
            return node

        else:
            # Default to round robin
            return self._select_node(healthy_nodes)

    def _check_node_health(self):
        """Check health of all nodes periodically"""
        now = datetime.now()

        for node in self.nodes:
            # Skip if checked recently
            if node.last_check and (now - node.last_check) < timedelta(seconds=self.health_check_interval):
                continue

            # Health check
            try:
                response = requests.get(f"{node.endpoint}/api/tags", timeout=5)
                if response.status_code == 200:
                    # Node is healthy
                    if not node.healthy:
                        print(f"Node {node.endpoint} recovered")
                    node.healthy = True
                    node.consecutive_failures = 0
                else:
                    node.healthy = False
            except Exception:
                node.healthy = False

            node.last_check = now

    def _handle_node_failure(self, node: OllamaNode, error: str):
        """Handle node failure"""
        node.consecutive_failures += 1

        if node.consecutive_failures >= self.max_consecutive_failures:
            node.healthy = False
            print(f"Node {node.endpoint} marked unhealthy after {node.consecutive_failures} failures: {error}")

    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        return {
            "strategy": self.strategy,
            "total_nodes": len(self.nodes),
            "healthy_nodes": len([n for n in self.nodes if n.healthy]),
            "nodes": [
                {
                    "endpoint": n.endpoint,
                    "healthy": n.healthy,
                    "response_time_ms": n.response_time_ms,
                    "current_load": n.current_load,
                    "consecutive_failures": n.consecutive_failures
                }
                for n in self.nodes
            ]
        }


if __name__ == "__main__":
    # Example usage - matches Health Guardian configuration
    balancer = OllamaLoadBalancer([
        "http://192.168.1.186:11434",      # Powerful node FIRST (many large models)
        "http://192.168.1.76:11434",       # Remote node 2 (llama3.2, mistral)
        "http://localhost:11434",          # mac-studio (fallback, avoid over-taxing)
    ], strategy="least_loaded")

    try:
        result = balancer.generate(
            model="llama3.2:3b",
            prompt="What is 2+2?"
        )
        print(f"Response: {result['response']}")
        print(f"Endpoint: {result['endpoint_used']}")
        print(f"Time: {result['response_time_ms']:.0f}ms")
    except Exception as e:
        print(f"Error: {e}")

    print("\nStatus:")
    import json
    print(json.dumps(balancer.get_status(), indent=2))
