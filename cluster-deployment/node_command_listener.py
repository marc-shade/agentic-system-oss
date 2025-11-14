#!/usr/bin/env python3
"""
Node Command Listener - Telnet-style Control Daemon
Enables orchestrator-to-node remote command execution

Listen on port 9999 for commands from orchestrator
Execute commands and return results
Simple text-based protocol for easy debugging

Usage:
    python3 node_command_listener.py [node_id] [port]

Example:
    python3 node_command_listener.py macpro51 9999
"""

import socket
import subprocess
import json
import sys
import os
import threading
import time
from datetime import datetime
from pathlib import Path

class NodeCommandListener:
    def __init__(self, node_id, port=9999):
        self.node_id = node_id
        self.port = port
        self.running = False
        self.log_file = Path(f"/tmp/node_command_listener_{node_id}.log")

    def log(self, message):
        """Log to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")

    def execute_command(self, command):
        """Execute a shell command and return result"""
        try:
            self.log(f"Executing: {command}")

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            response = {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
                "node": self.node_id,
                "timestamp": datetime.now().isoformat()
            }

            self.log(f"Result: returncode={result.returncode}")
            return response

        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {command}")
            return {
                "status": "timeout",
                "error": "Command execution timed out after 300 seconds",
                "command": command,
                "node": self.node_id
            }
        except Exception as e:
            self.log(f"Error executing command: {e}")
            return {
                "status": "error",
                "error": str(e),
                "command": command,
                "node": self.node_id
            }

    def handle_client(self, client_socket, address):
        """Handle a client connection"""
        self.log(f"Connection from {address}")

        try:
            # Send welcome message
            welcome = f"Node Command Listener - {self.node_id}\n"
            welcome += f"Connected. Send commands (one per line).\n"
            welcome += f"Type 'quit' to disconnect, 'status' for node status.\n"
            welcome += f"> "
            client_socket.send(welcome.encode())

            buffer = ""
            while True:
                # Receive data
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Process complete commands (lines)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    command = line.strip()

                    if not command:
                        client_socket.send(b"> ")
                        continue

                    self.log(f"Received command: {command}")

                    # Handle special commands
                    if command.lower() == 'quit':
                        client_socket.send(b"Goodbye!\n")
                        return

                    elif command.lower() == 'status':
                        status = {
                            "node": self.node_id,
                            "status": "online",
                            "uptime": time.time(),
                            "timestamp": datetime.now().isoformat()
                        }
                        response = json.dumps(status, indent=2) + "\n> "
                        client_socket.send(response.encode())

                    elif command.lower().startswith('exec '):
                        # Execute command
                        cmd = command[5:].strip()
                        result = self.execute_command(cmd)
                        response = json.dumps(result, indent=2) + "\n> "
                        client_socket.send(response.encode())

                    else:
                        # Unknown command
                        error = f"Unknown command: {command}\n"
                        error += "Available commands:\n"
                        error += "  exec <command>  - Execute shell command\n"
                        error += "  status         - Get node status\n"
                        error += "  quit           - Disconnect\n> "
                        client_socket.send(error.encode())

        except Exception as e:
            self.log(f"Error handling client: {e}")

        finally:
            client_socket.close()
            self.log(f"Connection closed from {address}")

    def start(self):
        """Start the command listener"""
        self.log(f"Starting Node Command Listener on port {self.port}")
        self.log(f"Node ID: {self.node_id}")

        # Create socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            self.running = True

            self.log(f"Listening on 0.0.0.0:{self.port}")
            self.log(f"Orchestrator can connect with: telnet {self.node_id} {self.port}")
            self.log(f"Or: nc {self.node_id} {self.port}")

            while self.running:
                try:
                    client_socket, address = server_socket.accept()

                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except KeyboardInterrupt:
                    self.log("Shutting down...")
                    self.running = False
                    break

        finally:
            server_socket.close()
            self.log("Server stopped")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 node_command_listener.py <node_id> [port]")
        print("Example: python3 node_command_listener.py macpro51 9999")
        sys.exit(1)

    node_id = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

    listener = NodeCommandListener(node_id, port)
    listener.start()

if __name__ == "__main__":
    main()
