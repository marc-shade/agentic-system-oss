#!/usr/bin/env python3
"""
System Card Generator
Automatically generates comprehensive system cards for cluster nodes.

Each node should run this to maintain its own system card, which is then
accessible to the cluster mind for architectural decision-making.
"""

import json
import os
import subprocess
import socket
import platform
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class SystemCardGenerator:
    """Generates comprehensive system cards for cluster nodes"""

    SCHEMA_VERSION = "system-card-v1"

    def __init__(self, node_id: str, storage_base: str):
        self.node_id = node_id
        self.storage_base = Path(storage_base)
        self.card_path = self.storage_base / "cluster-deployment" / "system-cards" / f"{node_id}.json"
        self.card_path.parent.mkdir(parents=True, exist_ok=True)

    def generate(self) -> Dict[str, Any]:
        """Generate complete system card"""
        return {
            "$schema": self.SCHEMA_VERSION,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "node_id": self.node_id,
            "identity": self._get_identity(),
            "hardware": self._get_hardware(),
            "software": self._get_software(),
            "services": self._get_services(),
            "capabilities": self._get_capabilities(),
            "performance_profile": self._get_performance_profile(),
            "cluster_integration": self._get_cluster_integration(),
            "operational": self._get_operational()
        }

    def _get_identity(self) -> Dict:
        """Get node identity information"""
        roles = {
            "macpro51": ("builder", "pragmatic, execution-focused", "Compilation, testing, containerization"),
            "mac-studio": ("orchestrator", "strategic, coordinating", "Cluster orchestration, monitoring"),
            "macbook-air-m3": ("researcher", "analytical, thorough", "Research, documentation, analysis"),
            "completeu-server": ("ai-inference", "efficient, responsive", "LLM inference, model serving")
        }
        role, persona, function = roles.get(self.node_id, ("unknown", "unknown", "unknown"))

        return {
            "hostname": socket.gethostname(),
            "role": role,
            "persona": persona,
            "primary_function": function
        }

    def _get_hardware(self) -> Dict:
        """Get hardware specifications"""
        hw = {"system": {}, "cpu": {}, "memory": {}, "gpu": {}, "storage": {}, "network": {}, "thermal": {}}

        # CPU info
        hw["cpu"] = {
            "architecture": platform.machine(),
            "total_threads": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
        }

        # Try to get detailed CPU info on Linux
        if platform.system() == "Linux":
            try:
                lscpu = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
                for line in lscpu.stdout.split("\n"):
                    if "Model name:" in line:
                        hw["cpu"]["model"] = line.split(":")[1].strip()
                    elif "Socket(s):" in line:
                        hw["cpu"]["sockets"] = int(line.split(":")[1].strip())
                    elif "Core(s) per socket:" in line:
                        hw["cpu"]["cores_per_socket"] = int(line.split(":")[1].strip())
                    elif "CPU max MHz:" in line:
                        hw["cpu"]["max_clock_ghz"] = float(line.split(":")[1].strip()) / 1000
            except:
                pass

        # Memory
        mem = psutil.virtual_memory()
        hw["memory"] = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1)
        }

        # Storage
        hw["storage"] = {"devices": []}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                hw["storage"]["devices"].append({
                    "mount": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1)
                })
            except:
                pass

        # Network
        hw["network"] = {"interfaces": []}
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    hw["network"]["interfaces"].append({
                        "name": iface,
                        "ip": addr.address
                    })

        # GPU detection
        hw["gpu"] = self._detect_gpu()

        return hw

    def _detect_gpu(self) -> Dict:
        """Detect GPU information"""
        gpu = {"present": False}

        if platform.system() == "Linux":
            try:
                lspci = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
                for line in lspci.stdout.split("\n"):
                    if "VGA" in line or "3D" in line:
                        gpu["present"] = True
                        gpu["description"] = line.split(": ")[-1] if ": " in line else line
                        break
            except:
                pass
        elif platform.system() == "Darwin":
            try:
                sp = subprocess.run(["system_profiler", "SPDisplaysDataType"],
                                   capture_output=True, text=True, timeout=10)
                if "Chipset Model:" in sp.stdout:
                    gpu["present"] = True
                    for line in sp.stdout.split("\n"):
                        if "Chipset Model:" in line:
                            gpu["model"] = line.split(":")[1].strip()
                            break
            except:
                pass

        return gpu

    def _get_software(self) -> Dict:
        """Get software/runtime information"""
        sw = {
            "os": {
                "name": platform.system(),
                "version": platform.version(),
                "release": platform.release()
            },
            "runtimes": {},
            "containers": {}
        }

        # Detect runtimes
        runtimes = [
            ("python", ["python3", "--version"]),
            ("node", ["node", "--version"]),
            ("rust", ["rustc", "--version"]),
            ("go", ["go", "version"]),
        ]

        for name, cmd in runtimes:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    sw["runtimes"][name] = result.stdout.strip()
            except:
                pass

        # Detect container runtimes
        containers = [
            ("docker", ["docker", "--version"]),
            ("podman", ["podman", "--version"]),
        ]

        for name, cmd in containers:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    sw["containers"][name] = result.stdout.strip()
            except:
                pass

        return sw

    def _get_services(self) -> Dict:
        """Get running services"""
        services = {"running": [], "containers": []}

        # Get systemd services on Linux
        if platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "list-units", "--type=service",
                     "--state=running", "--no-pager", "--no-legend"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n"):
                    if line:
                        service_name = line.split()[0].replace(".service", "")
                        services["running"].append(service_name)
            except:
                pass

        # Get containers
        for runtime in ["podman", "docker"]:
            try:
                result = subprocess.run(
                    [runtime, "ps", "--format", "{{.Names}}"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for name in result.stdout.strip().split("\n"):
                        if name and name not in services["containers"]:
                            services["containers"].append(name)
            except:
                pass

        return services

    def _get_capabilities(self) -> Dict:
        """Determine node capabilities"""
        caps = {
            "compute": {
                "parallel_jobs": psutil.cpu_count(),
                "can_compile": [],
                "can_containerize": False
            },
            "ai_inference": {
                "local_llm": False,
                "embedding_models": False
            },
            "storage": {
                "can_host_databases": True
            }
        }

        # Check compilers
        compilers = ["gcc", "clang", "rustc", "go", "python3", "node"]
        for compiler in compilers:
            try:
                result = subprocess.run(["which", compiler], capture_output=True, timeout=2)
                if result.returncode == 0:
                    caps["compute"]["can_compile"].append(compiler)
            except:
                pass

        # Check container runtimes
        for runtime in ["docker", "podman"]:
            try:
                result = subprocess.run(["which", runtime], capture_output=True, timeout=2)
                if result.returncode == 0:
                    caps["compute"]["can_containerize"] = True
                    break
            except:
                pass

        # Check for Ollama (LLM capability)
        try:
            result = subprocess.run(["pgrep", "-f", "ollama"], capture_output=True, timeout=2)
            if result.returncode == 0:
                caps["ai_inference"]["local_llm"] = True
        except:
            pass

        return caps

    def _get_performance_profile(self) -> Dict:
        """Get performance profile"""
        cpu_count = psutil.cpu_count()
        mem_gb = psutil.virtual_memory().total / (1024**3)

        return {
            "cpu_threads": cpu_count,
            "memory_gb": round(mem_gb, 1),
            "multi_thread_score": "high" if cpu_count >= 16 else "medium" if cpu_count >= 8 else "low",
            "memory_score": "high" if mem_gb >= 64 else "medium" if mem_gb >= 16 else "low"
        }

    def _get_cluster_integration(self) -> Dict:
        """Get cluster integration info"""
        return {
            "protocols": ["ssh", "http", "node-chat-mcp"],
            "storage_base": str(self.storage_base)
        }

    def _get_operational(self) -> Dict:
        """Get operational info"""
        return {
            "uptime_hours": round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
        }

    def save(self, card: Optional[Dict] = None) -> Path:
        """Save system card to file"""
        if card is None:
            card = self.generate()

        with open(self.card_path, 'w') as f:
            json.dump(card, f, indent=2)

        return self.card_path

    def load(self) -> Optional[Dict]:
        """Load existing system card"""
        if self.card_path.exists():
            with open(self.card_path) as f:
                return json.load(f)
        return None


def main():
    """Generate and save system card for local node"""
    import sys

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    # Detect node ID
    hostname = socket.gethostname().lower()
    if "macpro" in hostname:
        node_id = "macpro51"
        storage_base = str(_STORAGE_BASE)
    elif "mac-studio" in hostname or "macstudio" in hostname:
        node_id = "mac-studio"
        storage_base = str(_STORAGE_BASE)
    elif "macbook" in hostname:
        node_id = "macbook-air-m3"
        storage_base = "/Users/marc/agentic-system"
    elif "completeu" in hostname:
        node_id = "completeu-server"
        storage_base = str(_STORAGE_BASE)
    else:
        print(f"Unknown node: {hostname}")
        sys.exit(1)

    generator = SystemCardGenerator(node_id, storage_base)
    card = generator.generate()
    path = generator.save(card)

    print(f"Generated system card: {path}")
    print(json.dumps(card, indent=2))


if __name__ == "__main__":
    main()
