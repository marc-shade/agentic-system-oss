import os
import sys
import platform
import socket
import psutil
import json
from typing import Dict, List, Optional, Any
import asyncio
from loguru import logger
from pathlib import Path

class SystemAwarenessManager:
    """
    Manages system awareness for the Software Planning MCP.
    Detects and maps the environment, hardware capabilities, and available resources.
    """
    
    def __init__(self):
        self.system_info: Dict[str, Any] = {}
        self.hardware_info: Dict[str, Any] = {}
        self.storage_info: Dict[str, Any] = {}
        self.network_info: Dict[str, Any] = {}
        self.runtime_info: Dict[str, Any] = {}
        self.environment_variables: Dict[str, str] = {}
        
    async def initialize(self) -> None:
        """
        Initialize the system awareness manager by collecting all system information.
        """
        logger.info("Initializing system awareness manager")
        
        # Collect system information concurrently
        await asyncio.gather(
            self.collect_system_info(),
            self.collect_hardware_info(),
            self.collect_storage_info(),
            self.collect_network_info(),
            self.collect_runtime_info(),
            self.collect_environment_variables()
        )
        
        logger.info("System awareness manager initialized")
    
    async def collect_system_info(self) -> None:
        """Collect basic system information."""
        self.system_info = {
            "os": {
                "name": os.name,
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "platform": platform.platform(),
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler(),
                "build": platform.python_build(),
            },
            "hostname": socket.gethostname(),
            "username": os.getlogin() if hasattr(os, 'getlogin') else None,
            "pid": os.getpid(),
            "cwd": os.getcwd(),
        }
        
        logger.debug(f"Collected system information: {json.dumps(self.system_info, indent=2)}")
    
    async def collect_hardware_info(self) -> None:
        """Collect hardware information."""
        self.hardware_info = {
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency": {
                    "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                    "min": psutil.cpu_freq().min if psutil.cpu_freq() and psutil.cpu_freq().min else None,
                    "max": psutil.cpu_freq().max if psutil.cpu_freq() and psutil.cpu_freq().max else None,
                },
                "usage_percent": psutil.cpu_percent(interval=1),
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent,
            },
            "swap": {
                "total": psutil.swap_memory().total,
                "used": psutil.swap_memory().used,
                "free": psutil.swap_memory().free,
                "percent": psutil.swap_memory().percent,
            },
        }
        
        logger.debug(f"Collected hardware information: {json.dumps(self.hardware_info, indent=2)}")
    
    async def collect_storage_info(self) -> None:
        """Collect storage information."""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except (PermissionError, FileNotFoundError):
                # Skip partitions that cannot be accessed
                continue
        
        self.storage_info = {
            "partitions": partitions,
            "io_counters": {
                "read_count": psutil.disk_io_counters().read_count if psutil.disk_io_counters() else None,
                "write_count": psutil.disk_io_counters().write_count if psutil.disk_io_counters() else None,
                "read_bytes": psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else None,
                "write_bytes": psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else None,
            },
        }
        
        logger.debug(f"Collected storage information for {len(partitions)} partitions")
    
    async def collect_network_info(self) -> None:
        """Collect network information."""
        interfaces = {}
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            addresses = []
            for address in interface_addresses:
                addresses.append({
                    "family": str(address.family),
                    "address": address.address,
                    "netmask": address.netmask,
                    "broadcast": address.broadcast,
                })
            interfaces[interface_name] = addresses
        
        self.network_info = {
            "interfaces": interfaces,
            "connections": len(psutil.net_connections()),
            "io_counters": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv,
            },
        }
        
        logger.debug(f"Collected network information for {len(interfaces)} interfaces")
    
    async def collect_runtime_info(self) -> None:
        """Collect runtime information."""
        self.runtime_info = {
            "process": {
                "pid": os.getpid(),
                "ppid": os.getppid(),
                "name": psutil.Process().name(),
                "exe": psutil.Process().exe(),
                "cwd": psutil.Process().cwd(),
                "cmdline": psutil.Process().cmdline(),
                "create_time": psutil.Process().create_time(),
                "status": psutil.Process().status(),
                "username": psutil.Process().username(),
                "cpu_percent": psutil.Process().cpu_percent(),
                "memory_percent": psutil.Process().memory_percent(),
                "memory_info": {
                    "rss": psutil.Process().memory_info().rss,
                    "vms": psutil.Process().memory_info().vms,
                },
            },
            "python_path": sys.path,
            "loaded_modules": list(sys.modules.keys()),
        }
        
        logger.debug("Collected runtime information")
    
    async def collect_environment_variables(self) -> None:
        """Collect environment variables."""
        # Filter out sensitive environment variables
        sensitive_vars = {"API_KEY", "SECRET_KEY", "PASSWORD", "TOKEN", "CREDENTIAL"}
        self.environment_variables = {}
        
        for key, value in os.environ.items():
            # Skip sensitive environment variables
            if any(sensitive in key.upper() for sensitive in sensitive_vars):
                self.environment_variables[key] = "***REDACTED***"
            else:
                self.environment_variables[key] = value
        
        logger.debug(f"Collected {len(self.environment_variables)} environment variables")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get all system information."""
        return {
            "system": self.system_info,
            "hardware": self.hardware_info,
            "storage": self.storage_info,
            "network": self.network_info,
            "runtime": self.runtime_info,
            "environment": self.environment_variables,
        }
    
    def get_execution_environments(self) -> List[Dict[str, Any]]:
        """Get information about available execution environments."""
        environments = []
        
        # Default Python environment
        environments.append({
            "type": "python",
            "version": platform.python_version(),
            "path": sys.executable,
            "packages": self._get_installed_packages(),
        })
        
        # Node.js if available
        if self._is_executable_available("node"):
            environments.append({
                "type": "node",
                "version": self._get_command_output(["node", "--version"]),
                "path": self._get_command_output(["which", "node"]),
                "npm": self._get_command_output(["npm", "--version"]) if self._is_executable_available("npm") else None,
            })
        
        # Docker if available
        if self._is_executable_available("docker"):
            environments.append({
                "type": "docker",
                "version": self._get_command_output(["docker", "--version"]),
                "path": self._get_command_output(["which", "docker"]),
                "compose": self._get_command_output(["docker-compose", "--version"]) if self._is_executable_available("docker-compose") else None,
            })
        
        return environments
    
    def _get_installed_packages(self) -> List[Dict[str, str]]:
        """Get a list of installed Python packages."""
        try:
            import pkg_resources
            return [
                {"name": package.key, "version": package.version}
                for package in pkg_resources.working_set
            ]
        except ImportError:
            logger.warning("Could not import pkg_resources to get installed packages")
            return []
    
    def _is_executable_available(self, name: str) -> bool:
        """Check if an executable is available in the system PATH."""
        from shutil import which
        return which(name) is not None
    
    def _get_command_output(self, command: List[str]) -> str:
        """Run a command and return its output."""
        try:
            import subprocess
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Error running command {command}: {e}")
            return ""
            
    async def detect_environment(self) -> Dict[str, Any]:
        """Detect the current development environment."""
        logger.info("Detecting development environment")
        
        # Ensure we have the latest information
        if not self.system_info:
            await self.collect_system_info()
        if not self.hardware_info:
            await self.collect_hardware_info()
        
        # Determine the environment type
        env_type = "unknown"
        env_details = {}
        
        # Check for container environments
        if os.path.exists("/.dockerenv"):
            env_type = "docker"
            env_details["container_id"] = self._get_command_output(["cat", "/proc/self/cgroup"]).split("/")[-1]
        elif os.environ.get("KUBERNETES_SERVICE_HOST"):
            env_type = "kubernetes"
            env_details["namespace"] = os.environ.get("KUBERNETES_NAMESPACE", "unknown")
            env_details["pod_name"] = os.environ.get("HOSTNAME", "unknown")
        
        # Check for cloud environments
        elif os.path.exists("/sys/hypervisor/uuid"):
            hypervisor_uuid = self._get_command_output(["cat", "/sys/hypervisor/uuid"])
            if hypervisor_uuid.startswith("ec2"):
                env_type = "aws"
                env_details["instance_id"] = self._get_command_output(["curl", "-s", "http://169.254.169.254/latest/meta-data/instance-id"])
            elif "GOOGLE_CLOUD" in os.environ.get("CLOUD_PROVIDER", ""):
                env_type = "gcp"
                env_details["instance_id"] = os.environ.get("HOSTNAME", "unknown")
            elif "AZURE" in os.environ.get("CLOUD_PROVIDER", ""):
                env_type = "azure"
                env_details["instance_id"] = os.environ.get("HOSTNAME", "unknown")
        
        # Check for local development environments
        elif self._is_executable_available("code") or self._is_executable_available("code-insiders"):
            env_type = "vscode"
            env_details["workspace"] = os.getcwd()
        elif "JETBRAINS" in os.environ.get("TERMINAL_EMULATOR", ""):
            env_type = "jetbrains"
            env_details["workspace"] = os.getcwd()
        elif "TERM_PROGRAM" in os.environ and os.environ["TERM_PROGRAM"] == "Apple_Terminal":
            env_type = "terminal"
            env_details["terminal_type"] = "Apple Terminal"
        elif "TERM_PROGRAM" in os.environ and os.environ["TERM_PROGRAM"] == "iTerm.app":
            env_type = "terminal"
            env_details["terminal_type"] = "iTerm"
        
        # Determine OS type more specifically
        os_info = {}
        if platform.system() == "Darwin":
            os_info["type"] = "macos"
            os_info["version"] = platform.mac_ver()[0]
        elif platform.system() == "Linux":
            os_info["type"] = "linux"
            try:
                import distro
                os_info["distribution"] = distro.id()
                os_info["version"] = distro.version()
            except ImportError:
                os_info["distribution"] = "unknown"
                os_info["version"] = "unknown"
        elif platform.system() == "Windows":
            os_info["type"] = "windows"
            os_info["version"] = platform.win32_ver()[0]
        
        # Get available programming language environments
        languages = {}
        
        # Python
        languages["python"] = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "path": sys.executable
        }
        
        # Node.js
        if self._is_executable_available("node"):
            languages["node"] = {
                "version": self._get_command_output(["node", "--version"]),
                "npm_version": self._get_command_output(["npm", "--version"]) if self._is_executable_available("npm") else None
            }
        
        # Java
        if self._is_executable_available("java"):
            languages["java"] = {
                "version": self._get_command_output(["java", "-version"])
            }
        
        # Go
        if self._is_executable_available("go"):
            languages["go"] = {
                "version": self._get_command_output(["go", "version"])
            }
        
        # Rust
        if self._is_executable_available("rustc"):
            languages["rust"] = {
                "version": self._get_command_output(["rustc", "--version"])
            }
        
        return {
            "environment_type": env_type,
            "environment_details": env_details,
            "os": os_info,
            "languages": languages,
            "hardware": {
                "cpu_cores": self.hardware_info.get("cpu", {}).get("logical_cores", 0),
                "memory_gb": round(self.hardware_info.get("memory", {}).get("total", 0) / (1024 ** 3), 2)
            }
        }
    
    async def list_system_resources(self, resource_type: str = "all") -> Dict[str, Any]:
        """List available system resources."""
        logger.info(f"Listing system resources of type: {resource_type}")
        
        # Ensure we have the latest information
        if not self.hardware_info:
            await self.collect_hardware_info()
        if not self.storage_info:
            await self.collect_storage_info()
        if not self.network_info:
            await self.collect_network_info()
        
        result = {}
        
        if resource_type == "all" or resource_type == "cpu":
            result["cpu"] = {
                "physical_cores": self.hardware_info.get("cpu", {}).get("physical_cores", 0),
                "logical_cores": self.hardware_info.get("cpu", {}).get("logical_cores", 0),
                "frequency_mhz": self.hardware_info.get("cpu", {}).get("frequency", {}).get("current", 0),
                "usage_percent": psutil.cpu_percent(interval=0.1),
                "per_core_usage": psutil.cpu_percent(interval=0.1, percpu=True)
            }
        
        if resource_type == "all" or resource_type == "memory":
            memory = psutil.virtual_memory()
            result["memory"] = {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "usage_percent": memory.percent,
                "swap_total_gb": round(psutil.swap_memory().total / (1024 ** 3), 2),
                "swap_used_gb": round(psutil.swap_memory().used / (1024 ** 3), 2),
                "swap_usage_percent": psutil.swap_memory().percent
            }
        
        if resource_type == "all" or resource_type == "disk":
            result["disk"] = {
                "partitions": [
                    {
                        "mountpoint": partition.get("mountpoint", ""),
                        "total_gb": round(partition.get("total", 0) / (1024 ** 3), 2),
                        "used_gb": round(partition.get("used", 0) / (1024 ** 3), 2),
                        "free_gb": round(partition.get("free", 0) / (1024 ** 3), 2),
                        "usage_percent": partition.get("percent", 0)
                    }
                    for partition in self.storage_info.get("partitions", [])
                ],
                "io_counters": self.storage_info.get("io_counters", {})
            }
        
        if resource_type == "all" or resource_type == "network":
            result["network"] = {
                "interfaces": [
                    {
                        "name": name,
                        "addresses": [
                            {
                                "family": addr.get("family", ""),
                                "address": addr.get("address", "")
                            }
                            for addr in addresses
                        ]
                    }
                    for name, addresses in self.network_info.get("interfaces", {}).items()
                ],
                "io_counters": self.network_info.get("io_counters", {})
            }
        
        if resource_type == "all" or resource_type == "processes":
            result["processes"] = {
                "total": len(psutil.pids()),
                "running": len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'running']),
                "sleeping": len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'sleeping']),
                "top_by_cpu": [
                    {
                        "pid": p.pid,
                        "name": p.name(),
                        "cpu_percent": p.cpu_percent(),
                        "memory_percent": p.memory_percent()
                    }
                    for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                                   key=lambda p: p.cpu_percent(), reverse=True)[:5]
                ],
                "top_by_memory": [
                    {
                        "pid": p.pid,
                        "name": p.name(),
                        "cpu_percent": p.cpu_percent(),
                        "memory_percent": p.memory_percent()
                    }
                    for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                                   key=lambda p: p.memory_percent(), reverse=True)[:5]
                ]
            }
        
        return result
