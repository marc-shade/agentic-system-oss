#!/usr/bin/env python3
"""
Submit Tasks to GitMQ Cluster
=============================

Easy CLI for submitting work to cluster nodes.

Usage:
    # Submit Python code execution
    python3 submit_task.py --code "print('Hello from cluster')" --language python

    # Submit build task
    python3 submit_task.py --build --repo https://github.com/user/repo.git

    # Submit to specific node
    python3 submit_task.py --code "import platform; print(platform.node())" --node macbook-air

    # List available nodes
    python3 submit_task.py --list-nodes
"""

import argparse
import json
import requests
import time
import sqlite3
from pathlib import Path

CLUSTER_DB = Path("/mnt/agentic-system/databases/cluster/node_registry.db")
DEFAULT_API = "http://localhost:9000"

def get_healthy_nodes():
    """Get list of healthy cluster nodes."""
    nodes = []

    try:
        with sqlite3.connect(CLUSTER_DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM nodes WHERE status = 'active'")

            for row in cursor:
                node = dict(row)
                ip = node.get('ip_address', 'localhost')
                port = node.get('port', 9000)

                # Test health
                try:
                    response = requests.get(f"http://{ip}:{port}/health", timeout=2)
                    if response.status_code == 200:
                        node['healthy'] = True
                        nodes.append(node)
                except:
                    node['healthy'] = False

    except Exception as e:
        print(f"⚠️  Error getting nodes: {e}")

    return nodes

def list_nodes():
    """List all available nodes."""
    nodes = get_healthy_nodes()

    if not nodes:
        print("⚠️  No healthy nodes found")
        print("   Run: python3 add_node.py --init")
        return

    print(f"\n📋 Available Nodes ({len(nodes)}):\n")
    print(f"{'Node ID':<20} {'Role':<15} {'Address':<30} {'Status':<10}")
    print("=" * 75)

    for node in nodes:
        role = node.get('specialty', 'unknown')
        ip = node.get('ip_address')
        port = node.get('port', 9000)
        status = "✅ Online" if node.get('healthy') else "❌ Offline"

        print(f"{node['node_id']:<20} {role:<15} {ip}:{port:<25} {status:<10}")

    print()

def submit_code_task(code: str, language: str = "python", target_node: str = None):
    """Submit code execution task."""
    nodes = get_healthy_nodes()

    if not nodes:
        print("❌ No healthy nodes available")
        return False

    # Select target node
    if target_node:
        node = next((n for n in nodes if n['node_id'] == target_node), None)
        if not node:
            print(f"❌ Node '{target_node}' not found or unhealthy")
            return False
    else:
        # Use first healthy node
        node = nodes[0]

    ip = node.get('ip_address', 'localhost')
    port = node.get('port', 9000)
    node_id = node['node_id']

    print(f"\n🚀 Submitting task to {node_id}...")

    task = {
        "project_id": f"code-exec-{int(time.time())}",
        "build_type": "code_execution",
        "build_command": f"{language} -c '{code}'",
        "priority": 5
    }

    try:
        response = requests.post(
            f"http://{ip}:{port}/api/v1/build",
            json=task,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            build_id = result.get('build_id')

            print(f"✅ Task submitted: Build ID {build_id}")
            print(f"   Node: {node_id}")
            print(f"   Language: {language}")

            # Poll for results
            print(f"\n⏳ Waiting for results...")
            return poll_build_status(ip, port, build_id)

        else:
            print(f"❌ Task submission failed: HTTP {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def poll_build_status(ip: str, port: int, build_id: str, max_wait: int = 30):
    """Poll build status until complete."""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"http://{ip}:{port}/api/v1/build/{build_id}",
                timeout=2
            )

            if response.status_code == 200:
                status = response.json()
                state = status.get('status')

                if state == 'completed':
                    print(f"\n✅ Task completed successfully!")
                    print(f"\n📄 Output:")
                    print("-" * 70)
                    print(status.get('result', {}).get('output', '(no output)'))
                    print("-" * 70)
                    return True

                elif state in ['failed', 'error']:
                    print(f"\n❌ Task failed: {status.get('error', 'Unknown error')}")
                    return False

                elif state in ['pending', 'running']:
                    print(f"  Status: {state}...", end='\r')
                    time.sleep(1)

        except Exception as e:
            print(f"\n⚠️  Polling error: {e}")
            time.sleep(1)

    print(f"\n⏱️  Timeout waiting for results")
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Submit tasks to GitMQ cluster"
    )

    parser.add_argument("--code", help="Code to execute")
    parser.add_argument("--language", default="python", help="Language (python, bash, etc)")
    parser.add_argument("--node", help="Target node ID (optional)")
    parser.add_argument("--list-nodes", action="store_true", help="List available nodes")

    args = parser.parse_args()

    if args.list_nodes:
        list_nodes()

    elif args.code:
        submit_code_task(args.code, args.language, args.node)

    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("   List nodes:")
        print("     python3 submit_task.py --list-nodes")
        print("\n   Execute code:")
        print("     python3 submit_task.py --code \"print('Hello World')\"")
        print("\n   Target specific node:")
        print("     python3 submit_task.py --code \"import os; print(os.uname())\" --node macbook-air")

if __name__ == "__main__":
    main()
