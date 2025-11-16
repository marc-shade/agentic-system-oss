#!/usr/bin/env python3
"""
Agentic System Port Manager
Comprehensive port tracking, management, and documentation tool
"""

import subprocess
import json
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Port Registry - All known agentic system ports
PORT_REGISTRY = {
    # SSH/Remote Access
    22: {"service": "SSH", "category": "remote_access", "protocol": "tcp", "required": True, "description": "Secure Shell access"},
    23: {"service": "Telnet", "category": "remote_access", "protocol": "tcp", "required": False, "description": "Legacy telnet access"},

    # File Sharing
    139: {"service": "SMB/NetBIOS", "category": "file_sharing", "protocol": "tcp", "required": True, "description": "Samba NetBIOS"},
    445: {"service": "SMB/CIFS", "category": "file_sharing", "protocol": "tcp", "required": True, "description": "Samba file sharing"},

    # Agentic Services
    3001: {"service": "KutiraAI Frontend", "category": "agentic", "protocol": "tcp", "required": False, "description": "KutiraAI React dashboard (Vite)"},
    3002: {"service": "KutiraAI API", "category": "agentic", "protocol": "tcp", "required": True, "description": "KutiraAI backend API server"},
    4100: {"service": "Agentic Framework", "category": "agentic", "protocol": "tcp", "required": True, "description": "Agentic framework orchestration server"},
    5678: {"service": "n8n", "category": "agentic", "protocol": "tcp", "required": False, "description": "Workflow automation (Docker)"},
    6333: {"service": "Qdrant REST", "category": "agentic", "protocol": "tcp", "required": True, "description": "Vector database REST API (Docker)"},
    6334: {"service": "Qdrant gRPC", "category": "agentic", "protocol": "tcp", "required": True, "description": "Vector database gRPC (Docker)"},
    6379: {"service": "Redis", "category": "agentic", "protocol": "tcp", "required": True, "description": "Key-value store (Docker)"},
    8888: {"service": "Hardware Info", "category": "agentic", "protocol": "tcp", "required": False, "description": "Hardware monitoring API"},
    9000: {"service": "Builder Node API", "category": "agentic", "protocol": "tcp", "required": True, "description": "Orchestrator control API"},
    11434: {"service": "Ollama", "category": "agentic", "protocol": "tcp", "required": True, "description": "Local AI model server"},

    # Monitoring
    19999: {"service": "Netdata", "category": "monitoring", "protocol": "tcp", "required": False, "description": "System monitoring dashboard"},

    # System Services
    53: {"service": "DNS (systemd)", "category": "system", "protocol": "tcp/udp", "required": True, "description": "Local DNS resolver"},
    631: {"service": "CUPS", "category": "system", "protocol": "tcp", "required": False, "description": "Print service"},
    5355: {"service": "LLMNR", "category": "system", "protocol": "tcp/udp", "required": False, "description": "Link-Local Multicast Name Resolution"},

    # RDP/Remote Desktop (if configured)
    3389: {"service": "RDP", "category": "remote_access", "protocol": "tcp", "required": False, "description": "Remote Desktop Protocol"},
    3390: {"service": "RDP Alt", "category": "remote_access", "protocol": "tcp", "required": False, "description": "Alternative RDP port"},

    # Collaboration Office (if configured)
    9980: {"service": "Collabora Online", "category": "office", "protocol": "tcp", "required": False, "description": "Online office suite"},
    9982: {"service": "Collabora Admin", "category": "office", "protocol": "tcp", "required": False, "description": "Collabora admin console"},
}

class PortManager:
    """Manage and track network ports for agentic system"""

    def __init__(self):
        self.listening_ports = {}
        self.firewall_ports = []
        self.load_state()

    def load_state(self):
        """Load current port state"""
        self.scan_listening_ports()
        self.scan_firewall_rules()

    def scan_listening_ports(self):
        """Scan all currently listening ports"""
        try:
            # Use ss for modern port scanning
            result = subprocess.run(
                ["ss", "-tuln"],
                capture_output=True,
                text=True
            )

            self.listening_ports = {}
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        # Extract port from address:port
                        addr_port = parts[4]
                        if ':' in addr_port:
                            port_str = addr_port.split(':')[-1]
                            try:
                                port = int(port_str)
                                protocol = parts[0].lower()

                                # Get process info
                                process_info = self._get_process_for_port(port, protocol)

                                self.listening_ports[port] = {
                                    'protocol': protocol,
                                    'address': addr_port,
                                    'process': process_info,
                                    'registry': PORT_REGISTRY.get(port, {})
                                }
                            except ValueError:
                                pass
        except Exception as e:
            print(f"Error scanning ports: {e}")

    def _get_process_for_port(self, port: int, protocol: str) -> Optional[str]:
        """Get process name using a port"""
        try:
            # Use lsof to find process
            result = subprocess.run(
                ["sudo", "lsof", "-i", f"{protocol}:{port}", "-t"],
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                pid = result.stdout.strip().split('\n')[0]
                # Get process name
                proc_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "comm="],
                    capture_output=True,
                    text=True
                )
                return proc_result.stdout.strip()
        except:
            pass
        return None

    def scan_firewall_rules(self):
        """Get firewall port rules"""
        try:
            result = subprocess.run(
                ["sudo", "firewall-cmd", "--list-ports"],
                capture_output=True,
                text=True
            )

            self.firewall_ports = []
            for port_proto in result.stdout.strip().split():
                if '/' in port_proto:
                    port_str, proto = port_proto.split('/')
                    try:
                        port = int(port_str)
                        self.firewall_ports.append({'port': port, 'protocol': proto})
                    except ValueError:
                        pass
        except Exception as e:
            print(f"Error scanning firewall: {e}")

    def list_all_ports(self, category: Optional[str] = None):
        """List all ports with details"""
        print(f"\n{'='*100}")
        print(f"Port Manager - {socket.gethostname()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}\n")

        # Group ports by category
        categories = {}
        for port, info in sorted(self.listening_ports.items()):
            registry = info.get('registry', {})
            cat = registry.get('category', 'unknown')

            if category and cat != category:
                continue

            if cat not in categories:
                categories[cat] = []
            categories[cat].append((port, info))

        # Display by category
        for cat in sorted(categories.keys()):
            print(f"\n{cat.upper().replace('_', ' ')} ({len(categories[cat])} ports)")
            print(f"{'-'*100}")

            for port, info in categories[cat]:
                registry = info.get('registry', {})
                service_name = registry.get('service', 'Unknown')
                description = registry.get('description', 'No description')
                protocol = info.get('protocol', 'unknown')
                process = info.get('process', 'unknown')
                required = registry.get('required', False)

                # Check firewall status
                fw_open = any(p['port'] == port for p in self.firewall_ports)
                fw_status = "✅ OPEN" if fw_open else "🔒 LOCAL"
                req_status = "⚠️  REQUIRED" if required else "   OPTIONAL"

                print(f"  {port:5d}/{protocol:4s}  {fw_status:10s}  {req_status:13s}  {service_name:20s}  {process:20s}")
                print(f"             {description}")

    def check_required_ports(self):
        """Check if all required ports are listening"""
        print(f"\n{'='*100}")
        print("REQUIRED PORTS CHECK")
        print(f"{'='*100}\n")

        missing_ports = []
        for port, registry in PORT_REGISTRY.items():
            if registry.get('required', False):
                if port not in self.listening_ports:
                    missing_ports.append((port, registry['service']))
                    print(f"  ❌ Port {port} ({registry['service']}) - NOT LISTENING")
                else:
                    print(f"  ✅ Port {port} ({registry['service']}) - Active")

        if missing_ports:
            print(f"\n⚠️  WARNING: {len(missing_ports)} required port(s) not listening!")
            return False
        else:
            print(f"\n✅ All required ports are active")
            return True

    def show_agentic_ports(self):
        """Show only agentic system ports"""
        print(f"\n{'='*100}")
        print("AGENTIC SYSTEM PORTS")
        print(f"{'='*100}\n")

        agentic_ports = [
            (port, info) for port, info in sorted(self.listening_ports.items())
            if info.get('registry', {}).get('category') == 'agentic'
        ]

        for port, info in agentic_ports:
            registry = info['registry']
            service = registry['service']
            desc = registry['description']
            process = info.get('process', 'unknown')
            fw_open = any(p['port'] == port for p in self.firewall_ports)
            fw_status = "Public" if fw_open else "Local Only"

            print(f"  🔌 {port:5d}  {service:25s}  [{fw_status:12s}]  {process:20s}")
            print(f"             {desc}")
            print()

    def open_firewall_port(self, port: int, protocol: str = 'tcp'):
        """Open a port in firewall"""
        try:
            result = subprocess.run(
                ["sudo", "firewall-cmd", f"--add-port={port}/{protocol}", "--permanent"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                subprocess.run(["sudo", "firewall-cmd", "--reload"], capture_output=True)
                print(f"✅ Opened port {port}/{protocol} in firewall")
                self.scan_firewall_rules()
                return True
            else:
                print(f"❌ Failed to open port {port}/{protocol}: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def close_firewall_port(self, port: int, protocol: str = 'tcp'):
        """Close a port in firewall"""
        try:
            result = subprocess.run(
                ["sudo", "firewall-cmd", f"--remove-port={port}/{protocol}", "--permanent"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                subprocess.run(["sudo", "firewall-cmd", "--reload"], capture_output=True)
                print(f"✅ Closed port {port}/{protocol} in firewall")
                self.scan_firewall_rules()
                return True
            else:
                print(f"❌ Failed to close port {port}/{protocol}: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def export_json(self, filename: Optional[str] = None):
        """Export port configuration to JSON"""
        if not filename:
            filename = f"/home/marc/agentic-system/logs/ports-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        data = {
            'timestamp': datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'listening_ports': {
                str(port): {
                    'protocol': info['protocol'],
                    'process': info.get('process'),
                    'service': info.get('registry', {}).get('service', 'Unknown'),
                    'category': info.get('registry', {}).get('category', 'unknown'),
                    'required': info.get('registry', {}).get('required', False),
                    'firewall_open': any(p['port'] == port for p in self.firewall_ports)
                }
                for port, info in self.listening_ports.items()
            },
            'firewall_rules': self.firewall_ports
        }

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Exported port configuration to: {filename}")
        return filename

    def suggest_firewall_rules(self):
        """Suggest firewall rules for agentic ports"""
        print(f"\n{'='*100}")
        print("FIREWALL RULE SUGGESTIONS")
        print(f"{'='*100}\n")

        suggestions = []

        for port, info in sorted(self.listening_ports.items()):
            registry = info.get('registry', {})
            if registry.get('category') == 'agentic' and registry.get('required'):
                fw_open = any(p['port'] == port for p in self.firewall_ports)
                if not fw_open:
                    suggestions.append({
                        'port': port,
                        'service': registry['service'],
                        'protocol': registry.get('protocol', 'tcp').split('/')[0]
                    })

        if suggestions:
            print("The following required agentic ports should be opened in firewall:\n")
            for s in suggestions:
                print(f"  🔓 Port {s['port']:5d}/{s['protocol']:3s}  {s['service']:30s}")
                print(f"     Command: sudo firewall-cmd --add-port={s['port']}/{s['protocol']} --permanent")
                print()

            print(f"\nTo open all suggested ports:")
            print(f"  sudo firewall-cmd --permanent \\")
            for s in suggestions:
                print(f"    --add-port={s['port']}/{s['protocol']} \\")
            print(f"    && sudo firewall-cmd --reload")
        else:
            print("✅ All required agentic ports are already configured in firewall")


def main():
    """Main entry point"""
    import sys

    pm = PortManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            pm.list_all_ports()
        elif command == "agentic":
            pm.show_agentic_ports()
        elif command == "check":
            pm.check_required_ports()
        elif command == "suggest":
            pm.suggest_firewall_rules()
        elif command == "export":
            pm.export_json()
        elif command == "open" and len(sys.argv) > 2:
            port = int(sys.argv[2])
            protocol = sys.argv[3] if len(sys.argv) > 3 else 'tcp'
            pm.open_firewall_port(port, protocol)
        elif command == "close" and len(sys.argv) > 2:
            port = int(sys.argv[2])
            protocol = sys.argv[3] if len(sys.argv) > 3 else 'tcp'
            pm.close_firewall_port(port, protocol)
        else:
            print("Unknown command or missing arguments")
            print("\nUsage:")
            print("  port-manager.py list           - List all ports")
            print("  port-manager.py agentic        - Show agentic ports only")
            print("  port-manager.py check          - Check required ports")
            print("  port-manager.py suggest        - Suggest firewall rules")
            print("  port-manager.py export         - Export to JSON")
            print("  port-manager.py open PORT      - Open port in firewall")
            print("  port-manager.py close PORT     - Close port in firewall")
    else:
        # Default: show agentic ports and check required
        pm.show_agentic_ports()
        pm.check_required_ports()
        print()


if __name__ == '__main__':
    main()
