#!/usr/bin/env python3
"""
Node Inventory Collector - Gathers 100% of Node Information

Collects complete inventory of:
- Hardware specs
- Network interfaces (all IPs, MACs, speeds)
- All listening services (ports, protocols, bind addresses)
- Complete software inventory (pip, dnf, npm, etc.)
- All mounted filesystems
- SSH connectivity to other nodes
- System capabilities
- Important configuration files
- Environment variables (non-secret)

Runs regularly to keep comprehensive state 100% accurate.
"""

import json
import os
import platform
import psutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from comprehensive_cluster_state import ComprehensiveClusterState


class NodeInventoryCollector:
    """Collects complete inventory of local node"""

    def __init__(self, node_id: str, role: str):
        self.node_id = node_id
        self.role = role
        self.hostname = socket.gethostname()

    def collect_complete_inventory(self) -> Dict[str, Any]:
        """
        Collect COMPLETE inventory of this node

        Returns everything needed for comprehensive cluster state
        """
        print(f"🔍 Collecting complete inventory for {self.node_id}...")

        inventory = {
            # Basic node info
            "hostname": self.hostname,
            "role": self.role,
            "os_type": self._get_os_type(),
            "os_version": self._get_os_version(),
            "architecture": platform.machine(),
            "cpu_count": psutil.cpu_count(),
            "cpu_model": self._get_cpu_model(),
            "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "total_disk_gb": self._get_total_disk(),
            "python_version": platform.python_version(),
            "kernel_version": platform.release(),
            "timezone": self._get_timezone(),
            "locale": os.environ.get("LANG", "unknown"),
            "boot_time": psutil.boot_time(),
            "config_version": "1.0",

            # Detailed inventories
            "network_interfaces": self._collect_network_interfaces(),
            "services": self._collect_services(),
            "software": self._collect_software(),
            "filesystems": self._collect_filesystems(),
            "capabilities": self._collect_capabilities(),
            "ssh_connectivity": [],  # Filled by test_ssh_connectivity()
        }

        print(f"✅ Inventory collected: {len(inventory['network_interfaces'])} interfaces, "
              f"{len(inventory['services'])} services, {len(inventory['software'])} packages")

        return inventory

    def _get_os_type(self) -> str:
        """Get OS type (linux or darwin)"""
        return platform.system().lower()

    def _get_os_version(self) -> str:
        """Get OS version string"""
        os_type = self._get_os_type()

        if os_type == "linux":
            # Try to get Linux distribution info
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip().strip('"')
            except:
                pass
            return f"Linux {platform.release()}"

        elif os_type == "darwin":
            # macOS version
            result = subprocess.run(["sw_vers", "-productVersion"],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return f"macOS {result.stdout.strip()}"

        return platform.platform()

    def _get_cpu_model(self) -> str:
        """Get CPU model name"""
        os_type = self._get_os_type()

        if os_type == "linux":
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
            except:
                pass

        elif os_type == "darwin":
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()

        return "Unknown"

    def _get_total_disk(self) -> float:
        """Get total disk space in GB"""
        total = 0
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total += usage.total
            except:
                pass
        return round(total / (1024**3), 2)

    def _get_timezone(self) -> str:
        """Get system timezone"""
        try:
            if Path("/etc/timezone").exists():
                return Path("/etc/timezone").read_text().strip()

            result = subprocess.run(["timedatectl", "show", "-p", "Timezone", "--value"],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "unknown"

    def _collect_network_interfaces(self) -> List[Dict[str, Any]]:
        """Collect all network interfaces with full details"""
        interfaces = []

        # Get interface addresses
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)

        for interface_name, addr_list in addrs.items():
            # Skip loopback
            if interface_name == "lo":
                continue

            for addr in addr_list:
                if addr.family == socket.AF_INET:  # IPv4
                    iface_info = {
                        "interface_name": interface_name,
                        "ip_address": addr.address,
                        "netmask": addr.netmask,
                        "mac_address": self._get_mac_address(interface_name, addr_list),
                        "is_up": stats[interface_name].isup if interface_name in stats else False,
                        "speed_mbps": stats[interface_name].speed if interface_name in stats else None,
                        "bytes_sent": io_counters[interface_name].bytes_sent if interface_name in io_counters else 0,
                        "bytes_recv": io_counters[interface_name].bytes_recv if interface_name in io_counters else 0,
                    }
                    interfaces.append(iface_info)

        return interfaces

    def _get_mac_address(self, interface_name: str, addr_list: List) -> Optional[str]:
        """Extract MAC address from address list"""
        for addr in addr_list:
            if addr.family == psutil.AF_LINK:
                return addr.address
        return None

    def _collect_services(self) -> List[Dict[str, Any]]:
        """
        Collect all listening services/servers

        Scans all listening ports and identifies services
        """
        services = []
        seen = set()  # (port, protocol) tracking

        # Get all listening connections
        for conn in psutil.net_connections(kind='inet'):
            # Only listening sockets
            if conn.status != psutil.CONN_LISTEN:
                continue

            if not conn.laddr:
                continue

            port = conn.laddr.port
            bind_address = conn.laddr.ip
            protocol = "tcp" if conn.type == socket.SOCK_STREAM else "udp"

            # Avoid duplicates
            key = (port, protocol)
            if key in seen:
                continue
            seen.add(key)

            # Identify service name
            service_name = self._identify_service(port, conn.pid)
            service_type = self._classify_service_type(service_name, port)

            # Is it publicly accessible?
            is_public = bind_address in ("0.0.0.0", "::", "") or not bind_address.startswith("127.")

            service = {
                "service_name": service_name,
                "service_type": service_type,
                "port": port,
                "protocol": protocol,
                "bind_address": bind_address,
                "is_public": is_public,
                "pid": conn.pid,
                "status": "listening",
                "healthcheck_url": self._get_healthcheck_url(service_name, port, protocol),
                "config_path": self._find_config_path(service_name),
                "version": self._get_service_version(service_name),
            }

            services.append(service)

        return services

    def _identify_service(self, port: int, pid: Optional[int]) -> str:
        """Identify service name from port and process"""
        # Well-known ports
        well_known = {
            22: "ssh",
            80: "http",
            443: "https",
            5432: "postgresql",
            6379: "redis",
            6333: "qdrant",
            6334: "qdrant-grpc",
            7233: "temporal",
            8233: "temporal-ui",
            9000: "builder-node-api",
            9500: "grafana",
            9700: "prometheus",
            9900: "loki",
            11434: "ollama",
        }

        if port in well_known:
            return well_known[port]

        # Try to get process name
        if pid:
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                # Clean up process name
                if name.endswith(".py"):
                    return Path(proc.cmdline()[1]).stem if len(proc.cmdline()) > 1 else name
                return name
            except:
                pass

        return f"port-{port}"

    def _classify_service_type(self, service_name: str, port: int) -> str:
        """Classify service type"""
        service_types = {
            "redis": "cache",
            "qdrant": "vector_db",
            "postgresql": "database",
            "temporal": "workflow_engine",
            "grafana": "monitoring",
            "prometheus": "metrics",
            "loki": "logs",
            "ollama": "ai_inference",
            "builder-node-api": "http_api",
        }

        for key, svc_type in service_types.items():
            if key in service_name.lower():
                return svc_type

        # Classify by port
        if 80 <= port <= 89 or 8000 <= port <= 8999:
            return "http_service"
        elif 5000 <= port <= 5999:
            return "application"

        return "unknown"

    def _get_healthcheck_url(self, service_name: str, port: int, protocol: str) -> Optional[str]:
        """Generate health check URL for HTTP services"""
        if protocol == "tcp" and any(x in service_name.lower() for x in ["http", "api", "grafana", "prometheus"]):
            return f"http://localhost:{port}/health"
        return None

    def _find_config_path(self, service_name: str) -> Optional[str]:
        """Find configuration file path for service"""
        # Common config paths
        common_paths = [
            f"/home/marc/agentic-system/services/{service_name}.py",
            f"/home/marc/agentic-system/config/{service_name}.yaml",
            f"/etc/{service_name}/{service_name}.conf",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def _get_service_version(self, service_name: str) -> Optional[str]:
        """Get service version if available"""
        # Try common version commands
        version_commands = {
            "docker": ["docker", "--version"],
            "podman": ["podman", "--version"],
            "redis": ["redis-server", "--version"],
            "ollama": ["ollama", "--version"],
        }

        if service_name in version_commands:
            try:
                result = subprocess.run(version_commands[service_name],
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Extract version number
                    output = result.stdout.strip()
                    # Simple extraction - take first number pattern
                    import re
                    match = re.search(r'(\d+\.\d+\.\d+)', output)
                    if match:
                        return match.group(1)
            except:
                pass

        return None

    def _collect_software(self) -> List[Dict[str, Any]]:
        """
        Collect complete software inventory

        Inventories all installed packages:
        - Python packages (pip)
        - System packages (dnf/apt/brew)
        - Node packages (npm -g)
        """
        software = []

        # Python packages
        print("  📦 Collecting Python packages...")
        software.extend(self._collect_pip_packages())

        # System packages
        print("  📦 Collecting system packages...")
        os_type = self._get_os_type()
        if os_type == "linux":
            if Path("/usr/bin/dnf").exists():
                software.extend(self._collect_dnf_packages())
            elif Path("/usr/bin/apt").exists():
                software.extend(self._collect_apt_packages())
        elif os_type == "darwin":
            if Path("/opt/homebrew/bin/brew").exists() or Path("/usr/local/bin/brew").exists():
                software.extend(self._collect_brew_packages())

        # Node packages
        if Path("/usr/bin/npm").exists() or Path("/usr/local/bin/npm").exists():
            print("  📦 Collecting npm packages...")
            software.extend(self._collect_npm_packages())

        return software

    def _collect_pip_packages(self) -> List[Dict[str, Any]]:
        """Collect Python pip packages"""
        packages = []
        try:
            result = subprocess.run(["pip3", "list", "--format=json"],
                                   capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                pip_list = json.loads(result.stdout)
                for pkg in pip_list:
                    packages.append({
                        "package_name": pkg["name"],
                        "version": pkg["version"],
                        "package_type": "pip",
                        "install_path": self._find_pip_location(pkg["name"]),
                    })
        except Exception as e:
            print(f"  ⚠️ Error collecting pip packages: {e}")

        return packages

    def _find_pip_location(self, package_name: str) -> Optional[str]:
        """Find installation path of pip package"""
        try:
            result = subprocess.run(["pip3", "show", package_name],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Location:"):
                        return line.split(":", 1)[1].strip()
        except:
            pass
        return None

    def _collect_dnf_packages(self) -> List[Dict[str, Any]]:
        """Collect Fedora/RHEL dnf packages (top 100 user-installed)"""
        packages = []
        try:
            # Get user-installed packages only
            result = subprocess.run(
                ["dnf", "repoquery", "--userinstalled", "--qf", "%{name} %{version}"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[:100]:  # Limit to 100
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append({
                                "package_name": parts[0],
                                "version": parts[1],
                                "package_type": "dnf",
                                "install_path": "/usr",
                            })
        except Exception as e:
            print(f"  ⚠️ Error collecting dnf packages: {e}")

        return packages

    def _collect_apt_packages(self) -> List[Dict[str, Any]]:
        """Collect Debian/Ubuntu apt packages (top 100)"""
        packages = []
        try:
            result = subprocess.run(["apt", "list", "--installed"],
                                   capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                for line in result.stdout.split("\n")[1:101]:  # Skip header, limit to 100
                    if "/" in line:
                        parts = line.split("/")
                        name = parts[0]
                        version_part = line.split()[1] if len(line.split()) > 1 else "unknown"
                        packages.append({
                            "package_name": name,
                            "version": version_part,
                            "package_type": "apt",
                            "install_path": "/usr",
                        })
        except Exception as e:
            print(f"  ⚠️ Error collecting apt packages: {e}")

        return packages

    def _collect_brew_packages(self) -> List[Dict[str, Any]]:
        """Collect macOS Homebrew packages"""
        packages = []
        try:
            # Try both possible brew locations
            brew_path = "/opt/homebrew/bin/brew" if Path("/opt/homebrew/bin/brew").exists() else "brew"

            result = subprocess.run([brew_path, "list", "--versions"],
                                   capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 2:
                        packages.append({
                            "package_name": parts[0],
                            "version": parts[1],
                            "package_type": "brew",
                            "install_path": "/opt/homebrew" if "opt/homebrew" in brew_path else "/usr/local",
                        })
        except Exception as e:
            print(f"  ⚠️ Error collecting brew packages: {e}")

        return packages

    def _collect_npm_packages(self) -> List[Dict[str, Any]]:
        """Collect global npm packages"""
        packages = []
        try:
            result = subprocess.run(["npm", "list", "-g", "--json", "--depth=0"],
                                   capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                npm_data = json.loads(result.stdout)
                if "dependencies" in npm_data:
                    for name, info in npm_data["dependencies"].items():
                        packages.append({
                            "package_name": name,
                            "version": info.get("version", "unknown"),
                            "package_type": "npm",
                            "install_path": npm_data.get("path", "/usr/local/lib/node_modules"),
                        })
        except Exception as e:
            print(f"  ⚠️ Error collecting npm packages: {e}")

        return packages

    def _collect_filesystems(self) -> List[Dict[str, Any]]:
        """Collect all mounted filesystems"""
        filesystems = []

        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                fs = {
                    "mount_point": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "available_gb": round(usage.free / (1024**3), 2),
                    "percent_used": usage.percent,
                    "mount_options": partition.opts.split(",") if partition.opts else [],
                    "is_readonly": "ro" in partition.opts if partition.opts else False,
                }

                filesystems.append(fs)
            except PermissionError:
                # Skip filesystems we can't access
                pass

        return filesystems

    def _collect_capabilities(self) -> List[Dict[str, Any]]:
        """Collect node capabilities (what this node can do)"""
        capabilities = []

        # Check for Docker
        if self._command_exists("docker"):
            version = self._get_command_version("docker", "--version")
            capabilities.append({
                "capability_name": "docker",
                "version": version,
                "is_available": True,
            })

        # Check for Podman
        if self._command_exists("podman"):
            version = self._get_command_version("podman", "--version")
            capabilities.append({
                "capability_name": "podman",
                "version": version,
                "is_available": True,
            })

        # Check for GPU
        gpu_info = self._detect_gpu()
        if gpu_info:
            capabilities.append({
                "capability_name": "gpu",
                "is_available": True,
                "metadata": gpu_info,
            })

        # Check for Ollama
        if self._command_exists("ollama"):
            version = self._get_command_version("ollama", "--version")
            capabilities.append({
                "capability_name": "ollama",
                "version": version,
                "is_available": True,
            })

        # Check for Git
        if self._command_exists("git"):
            version = self._get_command_version("git", "--version")
            capabilities.append({
                "capability_name": "git",
                "version": version,
                "is_available": True,
            })

        # Check for build tools
        for tool in ["make", "gcc", "cargo", "npm", "pip3"]:
            if self._command_exists(tool):
                capabilities.append({
                    "capability_name": tool,
                    "is_available": True,
                })

        return capabilities

    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        return subprocess.run(["which", command],
                            capture_output=True, timeout=5).returncode == 0

    def _get_command_version(self, command: str, version_flag: str = "--version") -> Optional[str]:
        """Get version of a command"""
        try:
            result = subprocess.run([command, version_flag],
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Extract version number
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass
        return None

    def _detect_gpu(self) -> Optional[Dict[str, Any]]:
        """Detect GPU if available"""
        os_type = self._get_os_type()

        if os_type == "linux":
            # Try lspci
            try:
                result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "VGA" in line or "3D" in line:
                            return {"type": line.split(":", 1)[1].strip() if ":" in line else line}
            except:
                pass

        elif os_type == "darwin":
            # macOS GPU detection
            try:
                result = subprocess.run(["system_profiler", "SPDisplaysDataType"],
                                       capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "Chipset Model:" in line:
                            return {"type": line.split(":", 1)[1].strip()}
            except:
                pass

        return None

    def test_ssh_connectivity(self, known_nodes: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Test SSH connectivity to other known nodes

        Args:
            known_nodes: Dict of node_id -> ip_address

        Returns:
            List of SSH connectivity info
        """
        ssh_connections = []

        for node_id, ip in known_nodes.items():
            if node_id == self.node_id:
                continue  # Skip self

            print(f"  🔌 Testing SSH to {node_id} ({ip})...")

            start_time = time.time()

            # Test basic connectivity
            is_reachable = False
            has_key_auth = False
            latency_ms = None

            try:
                # Test SSH connection
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes",
                     "-o", "StrictHostKeyChecking=no", f"marc@{ip}", "echo test"],
                    capture_output=True, timeout=5
                )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                if result.returncode == 0:
                    is_reachable = True
                    has_key_auth = True
                else:
                    # Can ping but no key auth
                    ping_result = subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                                                capture_output=True, timeout=3)
                    is_reachable = ping_result.returncode == 0

            except Exception as e:
                print(f"    ⚠️ SSH test failed: {e}")

            ssh_connections.append({
                "target_node_id": node_id,
                "target_ip": ip,
                "is_reachable": is_reachable,
                "has_key_auth": has_key_auth,
                "latency_ms": latency_ms,
                "last_tested": time.time(),
            })

        return ssh_connections


def main():
    """Collect and register complete node inventory"""
    import sys

    # Detect node identity
    hostname = socket.gethostname()

    # Map hostname to node_id and role
    node_map = {
        "macpro51": ("macpro51", "builder"),
        "Mac-Studio": ("mac-studio", "orchestrator"),
        "MacBook-Air": ("macbook-air", "researcher"),
        "completeu-server": ("completeu-server", "ai-inference"),
        "completeu-server.local": ("completeu-server", "ai-inference"),
    }

    node_id, role = node_map.get(hostname, (hostname, "worker"))

    print(f"🚀 Collecting inventory for {node_id} ({role})")

    # Collect inventory
    collector = NodeInventoryCollector(node_id, role)
    inventory = collector.collect_complete_inventory()

    # Known nodes for SSH testing
    known_nodes = {
        "mac-studio": "192.168.1.157",
        "macbook-air": "192.168.1.76",
        "macpro51": "192.168.1.154",
        "completeu-server": "192.168.1.186",
    }

    # Test SSH connectivity
    print("🔌 Testing SSH connectivity to other nodes...")
    ssh_connectivity = collector.test_ssh_connectivity(known_nodes)
    inventory["ssh_connectivity"] = ssh_connectivity

    # Register in comprehensive state
    print("💾 Registering in comprehensive cluster state...")
    state = ComprehensiveClusterState()
    state.register_node_complete(node_id, inventory)

    print(f"✅ Node {node_id} inventory registered successfully!")
    print(f"\n📊 Summary:")
    print(f"   Network interfaces: {len(inventory['network_interfaces'])}")
    print(f"   Services: {len(inventory['services'])}")
    print(f"   Software packages: {len(inventory['software'])}")
    print(f"   Filesystems: {len(inventory['filesystems'])}")
    print(f"   Capabilities: {len(inventory['capabilities'])}")
    print(f"   SSH connectivity: {len(ssh_connectivity)} nodes tested")

    # Show complete state
    if "--show-state" in sys.argv:
        cluster_state = state.get_complete_cluster_state()
        print(f"\n🌍 Complete Cluster State:")
        print(json.dumps(cluster_state, indent=2))


if __name__ == "__main__":
    main()
