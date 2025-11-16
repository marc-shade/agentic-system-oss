#!/usr/bin/env python3
"""
Arduino Message Broker - Centralized Serial Port Manager
Allows multiple processes to communicate with Arduino through a single broker.

Architecture:
- Owns the serial port exclusively
- Accepts commands via Unix domain socket
- Queues commands from multiple clients
- Routes responses back to requesters
- Prevents port contention and garbled messages
"""

import serial
import json
import socket
import threading
import queue
import time
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any

# Configuration
SOCKET_PATH = "/tmp/arduino_broker.sock"
SERIAL_PORT = "/dev/tty.usbmodem8344401"
BAUD_RATE = 115200
TIMEOUT = 1.0
MAX_RETRIES = 3

class ArduinoBroker:
    def __init__(self, port: str = SERIAL_PORT):
        self.port = port
        self.serial_conn: Optional[serial.Serial] = None
        self.command_queue = queue.Queue()
        self.response_queues: Dict[str, queue.Queue] = {}
        self.running = False
        self.socket_path = SOCKET_PATH

    def connect_serial(self) -> bool:
        """Connect to Arduino serial port"""
        try:
            self.serial_conn = serial.Serial(
                self.port,
                BAUD_RATE,
                timeout=TIMEOUT
            )
            time.sleep(2)  # Wait for Arduino reset
            print(f"✓ Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Arduino: {e}")
            return False

    def setup_socket(self) -> socket.socket:
        """Setup Unix domain socket for IPC"""
        # Remove old socket if exists
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.socket_path)
        sock.listen(5)
        os.chmod(self.socket_path, 0o666)  # Allow all processes to connect
        print(f"✓ Broker listening on {self.socket_path}")
        return sock

    def handle_client(self, conn: socket.socket, addr: str):
        """Handle commands from a client connection"""
        client_id = f"client_{id(conn)}"
        self.response_queues[client_id] = queue.Queue()

        try:
            while self.running:
                # Receive command from client
                data = conn.recv(4096)
                if not data:
                    break

                try:
                    command = json.loads(data.decode('utf-8'))
                    command['_client_id'] = client_id

                    # Queue command for processing
                    self.command_queue.put(command)

                    # Wait for response
                    try:
                        response = self.response_queues[client_id].get(timeout=5.0)
                        conn.sendall(json.dumps(response).encode('utf-8') + b'\n')
                    except queue.Empty:
                        error_response = {"status": "error", "message": "Timeout waiting for Arduino"}
                        conn.sendall(json.dumps(error_response).encode('utf-8') + b'\n')

                except json.JSONDecodeError as e:
                    error_response = {"status": "error", "message": f"Invalid JSON: {e}"}
                    conn.sendall(json.dumps(error_response).encode('utf-8') + b'\n')

        except Exception as e:
            print(f"Client error: {e}")
        finally:
            if client_id in self.response_queues:
                del self.response_queues[client_id]
            conn.close()

    def process_commands(self):
        """Process queued commands and send to Arduino"""
        while self.running:
            try:
                # Get command from queue
                command = self.command_queue.get(timeout=0.1)
                client_id = command.pop('_client_id', None)

                # Send to Arduino
                response = self.send_to_arduino(command)

                # Route response back to client
                if client_id and client_id in self.response_queues:
                    self.response_queues[client_id].put(response)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Command processing error: {e}")

    def send_to_arduino(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to Arduino and get response"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return {"status": "error", "message": "Serial port not connected"}

        try:
            # Convert command to Arduino format
            if command.get('type') == 'lcd':
                cmd_str = f"LCD {command.get('line', 0)} {command.get('text', '')}\n"
            elif command.get('type') == 'led':
                r = command.get('r', 0)
                g = command.get('g', 0)
                b = command.get('b', 0)
                tier = command.get('tier', 0)
                cmd_str = f"LED {tier} {r} {g} {b}\n"
            elif command.get('type') == 'raw':
                cmd_str = command.get('command', '') + '\n'
            else:
                return {"status": "error", "message": "Unknown command type"}

            # Send command
            self.serial_conn.write(cmd_str.encode())
            self.serial_conn.flush()

            # Read response
            response_line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()

            if response_line:
                try:
                    response_data = json.loads(response_line)
                    return {"status": "ok", "data": response_data}
                except json.JSONDecodeError:
                    return {"status": "ok", "raw": response_line}
            else:
                return {"status": "ok", "message": "No response"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def accept_connections(self, sock: socket.socket):
        """Accept and handle client connections"""
        while self.running:
            try:
                conn, addr = sock.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"Connection error: {e}")

    def start(self):
        """Start the broker"""
        print("=" * 50)
        print("🔧 Arduino Message Broker Starting")
        print("=" * 50)

        # Connect to Arduino
        if not self.connect_serial():
            return False

        # Setup socket
        sock = self.setup_socket()

        self.running = True

        # Start command processor thread
        processor_thread = threading.Thread(target=self.process_commands, daemon=True)
        processor_thread.start()

        # Start accepting connections
        print("✓ Broker ready for connections")
        try:
            self.accept_connections(sock)
        except KeyboardInterrupt:
            print("\n⚠ Shutting down...")
        finally:
            self.stop()

    def stop(self):
        """Stop the broker"""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        print("✓ Broker stopped")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = SERIAL_PORT

    broker = ArduinoBroker(port)
    broker.start()

if __name__ == "__main__":
    main()
