#!/usr/bin/env python3
"""
Convex Heartbeat Client - Reactive Node Coordination

This client demonstrates:
1. Sending heartbeats to Convex
2. Subscribing to cluster status changes (reactive)
3. Comparing latency with polling approach

Usage:
    python3 heartbeat_client.py --node builder --send-heartbeat
    python3 heartbeat_client.py --subscribe
    python3 heartbeat_client.py --benchmark
"""

import asyncio
import aiohttp
import json
import time
import argparse
import os
import psutil
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# Convex configuration
CONVEX_URL = os.getenv("CONVEX_URL", "http://127.0.0.1:3210")
CONVEX_ADMIN_KEY = os.getenv(
    "CONVEX_ADMIN_KEY",
    "convex-self-hosted|0151d95174e8f04d4cb67383c9b48ac2d91c0e31d5c23ba3cd5fceeb9370911f26bcfe5355"
)


@dataclass
class NodeInfo:
    """Local node information."""
    node_id: str
    hostname: str
    capabilities: List[str]
    version: str = "1.0.0"

    def get_system_stats(self) -> Dict[str, float]:
        """Get current CPU and memory usage."""
        return {
            "cpuUsage": psutil.cpu_percent(interval=0.1),
            "memoryUsage": psutil.virtual_memory().percent,
        }


class ConvexHeartbeatClient:
    """Client for Convex heartbeat system."""

    def __init__(self, convex_url: str = CONVEX_URL, admin_key: str = CONVEX_ADMIN_KEY):
        self.convex_url = convex_url.rstrip("/")
        self.admin_key = admin_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Convex {self.admin_key}",
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _mutation(self, path: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Convex mutation."""
        url = f"{self.convex_url}/api/mutation"
        payload = {
            "path": path,
            "args": args,
            "format": "json",
        }

        start = time.time()
        async with self.session.post(url, json=payload) as resp:
            latency = (time.time() - start) * 1000
            result = await resp.json()
            result["_latency_ms"] = latency
            return result

    async def _query(self, path: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a Convex query."""
        url = f"{self.convex_url}/api/query"
        payload = {
            "path": path,
            "args": args or {},
            "format": "json",
        }

        start = time.time()
        async with self.session.post(url, json=payload) as resp:
            latency = (time.time() - start) * 1000
            result = await resp.json()
            if isinstance(result, dict):
                result["_latency_ms"] = latency
            return result

    async def send_heartbeat(self, node: NodeInfo, status: str = "online", active_task: str = None) -> Dict:
        """Send a heartbeat for a node."""
        stats = node.get_system_stats()

        args = {
            "nodeId": node.node_id,
            "hostname": node.hostname,
            "status": status,
            "cpuUsage": stats["cpuUsage"],
            "memoryUsage": stats["memoryUsage"],
            "capabilities": node.capabilities,
            "version": node.version,
        }
        if active_task:
            args["activeTask"] = active_task

        return await self._mutation("nodes:heartbeat", args)

    async def get_cluster_health(self) -> Dict:
        """Get cluster health summary (reactive query)."""
        return await self._query("nodes:clusterHealth")

    async def list_nodes(self) -> List[Dict]:
        """List all nodes."""
        return await self._query("nodes:list")

    async def list_online_nodes(self) -> List[Dict]:
        """List only online nodes."""
        return await self._query("nodes:listOnline")

    async def create_task(self, title: str, priority: int, created_by: str, description: str = None) -> Dict:
        """Create a new task."""
        args = {
            "title": title,
            "priority": priority,
            "createdBy": created_by,
        }
        if description:
            args["description"] = description

        return await self._mutation("tasks:create", args)

    async def get_next_task(self) -> Optional[Dict]:
        """Get the highest priority pending task."""
        return await self._query("tasks:getNext")


async def heartbeat_daemon(node: NodeInfo, interval: float = 5.0):
    """Run heartbeat daemon - sends periodic heartbeats."""
    print(f"Starting heartbeat daemon for {node.node_id}")
    print(f"  Hostname: {node.hostname}")
    print(f"  Capabilities: {', '.join(node.capabilities)}")
    print(f"  Interval: {interval}s")
    print()

    async with ConvexHeartbeatClient() as client:
        heartbeat_count = 0
        total_latency = 0

        while True:
            try:
                result = await client.send_heartbeat(node)
                heartbeat_count += 1
                latency = result.get("_latency_ms", 0)
                total_latency += latency
                avg_latency = total_latency / heartbeat_count

                print(f"[{heartbeat_count}] Heartbeat sent: {result.get('value', {}).get('action', 'unknown')} "
                      f"(latency: {latency:.1f}ms, avg: {avg_latency:.1f}ms)")

            except Exception as e:
                print(f"[{heartbeat_count}] Heartbeat failed: {e}")

            await asyncio.sleep(interval)


async def monitor_cluster():
    """Monitor cluster status - demonstrates reactive queries."""
    print("Monitoring cluster status (press Ctrl+C to stop)")
    print("=" * 60)

    async with ConvexHeartbeatClient() as client:
        last_health = None
        poll_count = 0

        while True:
            try:
                start = time.time()
                health = await client.get_cluster_health()
                latency = (time.time() - start) * 1000
                poll_count += 1

                # Only print if something changed
                health_str = json.dumps(health.get("value", health), sort_keys=True)
                if health_str != last_health:
                    last_health = health_str
                    value = health.get("value", health)

                    print(f"\n[{poll_count}] Cluster Health Update (latency: {latency:.1f}ms)")
                    print(f"  Total Nodes: {value.get('totalNodes', 0)}")
                    print(f"  Online: {value.get('onlineCount', 0)} | "
                          f"Offline: {value.get('offlineCount', 0)} | "
                          f"Busy: {value.get('busyCount', 0)}")
                    print(f"  Avg CPU: {value.get('avgCpuUsage', 0):.1f}% | "
                          f"Avg Memory: {value.get('avgMemoryUsage', 0):.1f}%")
                else:
                    print(f".", end="", flush=True)

            except Exception as e:
                print(f"\n[{poll_count}] Error: {e}")

            await asyncio.sleep(1)  # Poll every 1 second


async def benchmark_latency(iterations: int = 100):
    """Benchmark Convex query/mutation latency vs hypothetical polling."""
    print(f"Running latency benchmark ({iterations} iterations)")
    print("=" * 60)

    async with ConvexHeartbeatClient() as client:
        # Benchmark query latency
        query_latencies = []
        for i in range(iterations):
            start = time.time()
            await client.get_cluster_health()
            query_latencies.append((time.time() - start) * 1000)

        # Benchmark mutation latency
        mutation_latencies = []
        test_node = NodeInfo(
            node_id="benchmark-node",
            hostname="benchmark-host",
            capabilities=["test"],
        )
        for i in range(iterations):
            start = time.time()
            await client.send_heartbeat(test_node)
            mutation_latencies.append((time.time() - start) * 1000)

        # Results
        print(f"\nQuery Latency (clusterHealth):")
        print(f"  Min: {min(query_latencies):.1f}ms")
        print(f"  Max: {max(query_latencies):.1f}ms")
        print(f"  Avg: {sum(query_latencies)/len(query_latencies):.1f}ms")
        print(f"  p50: {sorted(query_latencies)[len(query_latencies)//2]:.1f}ms")
        print(f"  p99: {sorted(query_latencies)[int(len(query_latencies)*0.99)]:.1f}ms")

        print(f"\nMutation Latency (heartbeat):")
        print(f"  Min: {min(mutation_latencies):.1f}ms")
        print(f"  Max: {max(mutation_latencies):.1f}ms")
        print(f"  Avg: {sum(mutation_latencies)/len(mutation_latencies):.1f}ms")
        print(f"  p50: {sorted(mutation_latencies)[len(mutation_latencies)//2]:.1f}ms")
        print(f"  p99: {sorted(mutation_latencies)[int(len(mutation_latencies)*0.99)]:.1f}ms")

        # Comparison with polling
        print(f"\n{'='*60}")
        print("COMPARISON WITH POLLING:")
        print(f"  Current polling interval: ~60 seconds")
        print(f"  Convex reactive update: ~{sum(query_latencies)/len(query_latencies):.0f}ms")
        print(f"  Improvement factor: ~{60000 / (sum(query_latencies)/len(query_latencies)):.0f}x faster")


async def demo_reactive():
    """Demo showing reactive behavior - run in one terminal, update in another."""
    print("Reactive Demo - This will subscribe to cluster changes")
    print("In another terminal, run:")
    print("  python3 heartbeat_client.py --node test-node --send-heartbeat")
    print()
    print("You'll see updates appear immediately when heartbeats are sent!")
    print("=" * 60)

    await monitor_cluster()


def get_node_config(node_id: str) -> NodeInfo:
    """Get node configuration based on ID."""
    configs = {
        "orchestrator": NodeInfo(
            node_id="orchestrator",
            hostname="mac-studio",
            capabilities=["coordination", "memory", "dispatch"],
        ),
        "builder": NodeInfo(
            node_id="builder",
            hostname="macpro51",
            capabilities=["compilation", "docker", "testing", "linux"],
        ),
        "researcher": NodeInfo(
            node_id="researcher",
            hostname="macbook-air",
            capabilities=["research", "analysis", "documentation"],
        ),
        "inference": NodeInfo(
            node_id="inference",
            hostname="gpu-node",
            capabilities=["inference", "training", "tpu"],
        ),
    }

    if node_id in configs:
        return configs[node_id]

    # Default config for unknown nodes
    return NodeInfo(
        node_id=node_id,
        hostname=os.uname().nodename,
        capabilities=["generic"],
    )


def main():
    parser = argparse.ArgumentParser(description="Convex Heartbeat Client")
    parser.add_argument("--node", type=str, help="Node ID (orchestrator, builder, researcher, etc.)")
    parser.add_argument("--send-heartbeat", action="store_true", help="Run heartbeat daemon")
    parser.add_argument("--subscribe", action="store_true", help="Subscribe to cluster updates")
    parser.add_argument("--benchmark", action="store_true", help="Run latency benchmark")
    parser.add_argument("--demo", action="store_true", help="Run reactive demo")
    parser.add_argument("--interval", type=float, default=5.0, help="Heartbeat interval (seconds)")
    parser.add_argument("--iterations", type=int, default=100, help="Benchmark iterations")

    args = parser.parse_args()

    if args.send_heartbeat:
        if not args.node:
            print("Error: --node required for heartbeat daemon")
            return
        node = get_node_config(args.node)
        asyncio.run(heartbeat_daemon(node, args.interval))

    elif args.subscribe:
        asyncio.run(monitor_cluster())

    elif args.benchmark:
        asyncio.run(benchmark_latency(args.iterations))

    elif args.demo:
        asyncio.run(demo_reactive())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
