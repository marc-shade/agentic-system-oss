#!/usr/bin/env python3
"""
Orchestrator Remote Execution Client
Send commands to cluster nodes via telnet-style protocol

Usage:
    python3 orchestrator_remote_exec.py <node_ip> <command> [port]

Examples:
    # Get node status
    python3 orchestrator_remote_exec.py 192.168.1.183 status

    # Execute command
    python3 orchestrator_remote_exec.py 192.168.1.183 "exec hostname"

    # Execute TOON build
    python3 orchestrator_remote_exec.py 192.168.1.183 "exec cd /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51 && ./build_toon.sh"
"""

import socket
import sys
import json
import time

def send_command(node_ip, command, port=9999, timeout=10):
    """Send command to node and return response"""
    try:
        # Connect to node
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((node_ip, port))

        # Read welcome message
        welcome = sock.recv(4096).decode('utf-8')
        print(f"Connected to {node_ip}:{port}")
        print(welcome)

        # Send command
        sock.send(f"{command}\n".encode())

        # Read response
        response = ""
        while True:
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    break
                response += data

                # Check if we got a complete response (ends with "> ")
                if response.endswith("> "):
                    break

            except socket.timeout:
                break

        # Clean up prompt
        if response.endswith("> "):
            response = response[:-2]

        return response.strip()

    except ConnectionRefused:
        return f"ERROR: Connection refused. Is the command listener running on {node_ip}:{port}?"
    except socket.timeout:
        return f"ERROR: Connection timeout. Node might be unreachable."
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    node_ip = sys.argv[1]
    command = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999

    print(f"Sending to {node_ip}:{port}: {command}")
    print("-" * 60)

    response = send_command(node_ip, command, port)
    print(response)

    # Try to parse as JSON for pretty printing
    try:
        if response.startswith('{'):
            data = json.loads(response)
            print("\n" + "=" * 60)
            print("Parsed Response:")
            print("=" * 60)
            print(json.dumps(data, indent=2))

            # Special handling for exec results
            if data.get('status') == 'success':
                print("\n✅ Command executed successfully")
                if data.get('stdout'):
                    print("\nOutput:")
                    print(data['stdout'])
            elif data.get('status') == 'error':
                print("\n❌ Command failed")
                if data.get('stderr'):
                    print("\nError:")
                    print(data['stderr'])

    except:
        pass

if __name__ == "__main__":
    main()
