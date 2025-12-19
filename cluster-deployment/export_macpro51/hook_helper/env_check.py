#!/usr/bin/env python3
"""
Environmental Awareness System
Real-time system state without MCP dependencies

Phoenix uses this to maintain complete awareness of:
- System resources
- Service health
- Development environment
- Active projects
- Network state
"""

import json
import subprocess
import socket
import psutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class EnvironmentMonitor:
    """Complete environmental awareness for Phoenix"""

    def __init__(self):
        self.home = Path.home()
        self.claude_home = self.home / ".claude"
        self.code_base = Path("/Volumes/FILES/code")
        self.agentic_base = Path("/mnt/agentic-system")

    def check_port(self, port: int, timeout: float = 0.5) -> bool:
        """Check if port is listening"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except:
            return False

    def get_service_status(self) -> Dict[str, bool]:
        """Check all voice and system services"""
        return {
            "whisper_stt": self.check_port(2022),
            "kokoro_tts": self.check_port(8880),
            "kokoro_tts_alt": self.check_port(9091),
            "livekit_server": self.check_port(7880),
            "livekit_frontend": self.check_port(9050),
            "port_manager": self.check_port(4102),
        }

    def get_system_resources(self) -> Dict[str, Any]:
        """Get CPU, memory, disk usage"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        disks = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.mountpoint] = {
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent": usage.percent
                }
            except:
                pass

        return {
            "cpu_percent": cpu_percent,
            "memory_total_gb": memory.total / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "memory_percent": memory.percent,
            "disks": disks
        }

    def get_audio_devices(self) -> Dict[str, List[str]]:
        """Get available audio input/output devices"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()

            inputs = []
            outputs = []
            default_input = None
            default_output = None

            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    inputs.append(info['name'])
                    if i == p.get_default_input_device_info()['index']:
                        default_input = info['name']
                if info['maxOutputChannels'] > 0:
                    outputs.append(info['name'])
                    if i == p.get_default_output_device_info()['index']:
                        default_output = info['name']

            p.terminate()

            return {
                "inputs": inputs,
                "outputs": outputs,
                "default_input": default_input,
                "default_output": default_output
            }
        except Exception as e:
            return {
                "error": str(e),
                "inputs": [],
                "outputs": []
            }

    def get_git_status(self, path: Path) -> Optional[Dict[str, Any]]:
        """Get git status for a directory"""
        if not path.exists():
            return None

        try:
            cwd = os.getcwd()
            os.chdir(path)

            # Check if it's a git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                timeout=2
            )

            if result.returncode != 0:
                os.chdir(cwd)
                return None

            # Get branch
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                stderr=subprocess.DEVNULL,
                timeout=2
            ).decode().strip()

            # Get status
            status_output = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                stderr=subprocess.DEVNULL,
                timeout=2
            ).decode()

            status_lines = [l for l in status_output.split('\n') if l]

            modified = len([l for l in status_lines if l.startswith(' M')])
            added = len([l for l in status_lines if l.startswith('A')])
            deleted = len([l for l in status_lines if l.startswith(' D')])
            untracked = len([l for l in status_lines if l.startswith('??')])

            # Get remote status
            try:
                subprocess.check_output(
                    ['git', 'fetch', '--dry-run'],
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                remote_status = subprocess.check_output(
                    ['git', 'status', '-sb'],
                    stderr=subprocess.DEVNULL,
                    timeout=2
                ).decode().strip().split('\n')[0]
            except:
                remote_status = "unknown"

            os.chdir(cwd)

            return {
                "branch": branch,
                "modified": modified,
                "added": added,
                "deleted": deleted,
                "untracked": untracked,
                "total_uncommitted": len(status_lines),
                "remote_status": remote_status,
                "is_clean": len(status_lines) == 0
            }
        except Exception as e:
            os.chdir(cwd)
            return {"error": str(e)}

    def get_active_projects(self) -> List[Dict[str, Any]]:
        """Find active projects (recently modified)"""
        projects = []

        if self.code_base.exists():
            for project_dir in self.code_base.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith('.'):
                    try:
                        mtime = project_dir.stat().st_mtime
                        git_status = self.get_git_status(project_dir)

                        projects.append({
                            "name": project_dir.name,
                            "path": str(project_dir),
                            "last_modified": datetime.fromtimestamp(mtime).isoformat(),
                            "git": git_status
                        })
                    except:
                        pass

        # Sort by most recently modified
        projects.sort(key=lambda x: x['last_modified'], reverse=True)
        return projects[:10]  # Top 10 most recent

    def get_running_dev_servers(self) -> List[Dict[str, Any]]:
        """Find running development servers (Node, Python, etc.)"""
        servers = []

        try:
            # Common dev server ports
            dev_ports = [3000, 3001, 4000, 5000, 5173, 8000, 8080, 8888, 9000]

            for port in dev_ports:
                if self.check_port(port):
                    # Try to identify what's running
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            try:
                                connections = proc.connections()
                                for conn in connections:
                                    if conn.laddr.port == port:
                                        servers.append({
                                            "port": port,
                                            "pid": proc.info['pid'],
                                            "name": proc.info['name'],
                                            "cmdline": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else None
                                        })
                                        break
                            except:
                                pass
                    except:
                        servers.append({
                            "port": port,
                            "pid": None,
                            "name": "unknown"
                        })
        except:
            pass

        return servers

    def get_docker_status(self) -> Dict[str, Any]:
        """Get Docker container status"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{json .}}'],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.decode().split('\n'):
                    if line:
                        try:
                            containers.append(json.loads(line))
                        except:
                            pass

                return {
                    "docker_available": True,
                    "containers_running": len(containers),
                    "containers": containers
                }
        except:
            pass

        return {
            "docker_available": False,
            "containers_running": 0,
            "containers": []
        }

    def get_mcp_status(self) -> Dict[str, Any]:
        """Check MCP server configuration and status"""
        mcp_config = self.home / ".claude.json"

        if not mcp_config.exists():
            return {"configured": False}

        try:
            with open(mcp_config) as f:
                config = json.load(f)

            servers = config.get('mcpServers', {})

            return {
                "configured": True,
                "total_servers": len(servers),
                "servers": list(servers.keys())
            }
        except:
            return {"configured": True, "error": "Failed to parse config"}

    def get_complete_status(self) -> Dict[str, Any]:
        """Get complete environmental status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_resources(),
            "services": self.get_service_status(),
            "audio": self.get_audio_devices(),
            "cwd": os.getcwd(),
            "git": self.get_git_status(Path.cwd()),
            "active_projects": self.get_active_projects(),
            "dev_servers": self.get_running_dev_servers(),
            "docker": self.get_docker_status(),
            "mcp": self.get_mcp_status()
        }

    def get_summary(self) -> str:
        """Get human-readable summary"""
        status = self.get_complete_status()

        lines = [
            "=== Phoenix Environmental Awareness ===",
            f"Time: {status['timestamp']}",
            "",
            "System Resources:",
            f"  CPU: {status['system']['cpu_percent']:.1f}%",
            f"  Memory: {status['system']['memory_percent']:.1f}% ({status['system']['memory_available_gb']:.1f}GB free)",
            "",
            "Voice Services:",
        ]

        for service, running in status['services'].items():
            status_str = "✅" if running else "❌"
            lines.append(f"  {status_str} {service}")

        lines.append("")
        lines.append("Audio:")
        lines.append(f"  Input: {status['audio'].get('default_input', 'None')}")
        lines.append(f"  Output: {status['audio'].get('default_output', 'None')}")

        if status['git']:
            lines.append("")
            lines.append("Current Git Repository:")
            lines.append(f"  Branch: {status['git'].get('branch', 'N/A')}")
            lines.append(f"  Uncommitted: {status['git'].get('total_uncommitted', 0)}")

        if status['dev_servers']:
            lines.append("")
            lines.append("Running Dev Servers:")
            for server in status['dev_servers']:
                lines.append(f"  Port {server['port']}: {server.get('name', 'unknown')}")

        return '\n'.join(lines)

    def save_snapshot(self, filepath: Optional[Path] = None):
        """Save complete status snapshot to file"""
        if filepath is None:
            filepath = Path("/tmp/phoenix_env_snapshot.json")

        status = self.get_complete_status()

        with open(filepath, 'w') as f:
            json.dump(status, f, indent=2)

        return filepath


def quick_status() -> Dict[str, Any]:
    """Quick function for immediate status"""
    monitor = EnvironmentMonitor()
    return monitor.get_complete_status()


def quick_summary() -> str:
    """Quick function for human-readable summary"""
    monitor = EnvironmentMonitor()
    return monitor.get_summary()


if __name__ == '__main__':
    import sys

    monitor = EnvironmentMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == 'json':
        # Output JSON
        print(json.dumps(monitor.get_complete_status(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == 'save':
        # Save snapshot
        filepath = monitor.save_snapshot()
        print(f"Snapshot saved to: {filepath}")
    else:
        # Output summary
        print(monitor.get_summary())
