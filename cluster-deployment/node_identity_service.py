#!/usr/bin/env python3
"""
Node Identity Service - Enhanced Self-Awareness for Cluster Nodes
==================================================================

Each node must deeply understand itself to:
1. Know what capabilities it has vs peers
2. Understand its unique environment (paths, venvs, hardware)
3. Recognize what features it's missing
4. Know how to adapt foreign features to local setup

This service provides comprehensive self-introspection that goes beyond
simple cataloging to include:
- Environment mapping (paths, venvs, services)
- Capability fingerprinting (what this node can do)
- Dependency analysis (what's needed for each feature)
- Adaptation knowledge (how to translate paths/configs)
"""

import json
import os
import sqlite3
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import hashlib

# Get storage base from node config (mandatory - no fallbacks)
def _get_storage_base() -> str:
    config_path = Path.home() / ".claude" / "node-config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Node config not found at {config_path}")
    with open(config_path) as f:
        config = json.load(f)
        return config.get('storage', {}).get('base', str(Path.home() / "agentic-system"))

STORAGE_BASE = _get_storage_base()
CLAUDE_HOME = Path.home() / ".claude"
DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("node-identity")


class NodeIdentityService:
    """
    Comprehensive self-awareness service for cluster nodes.

    Enables nodes to:
    - Deeply understand their own capabilities
    - Map their unique environment
    - Generate adaptation strategies for foreign features
    - Share identity with peers for capability matching
    """

    def __init__(self):
        self.node_config = self._load_node_config()
        self.node_id = self.node_config.get('node_id', platform.node())
        self.identity = None

    def _load_node_config(self) -> Dict:
        """Load node configuration"""
        config_path = CLAUDE_HOME / "node-config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {"node_id": platform.node()}

    def generate_identity(self) -> Dict[str, Any]:
        """
        Generate comprehensive node identity.

        This is the foundation for self-awareness - understanding
        exactly what this node is and what it can do.
        """
        logger.info(f"Generating identity for {self.node_id}")

        self.identity = {
            "node_id": self.node_id,
            "generated_at": datetime.now().isoformat(),
            "platform": self._get_platform_info(),
            "environment": self._map_environment(),
            "capabilities": self._fingerprint_capabilities(),
            "claude_config": self._catalog_claude_config(),
            "services": self._discover_services(),
            "adaptation_map": self._generate_adaptation_map(),
            "identity_hash": None  # Set after generation
        }

        # Generate identity hash for quick comparison
        identity_str = json.dumps(self.identity, sort_keys=True)
        self.identity["identity_hash"] = hashlib.sha256(identity_str.encode()).hexdigest()[:16]

        return self.identity

    def _get_platform_info(self) -> Dict[str, Any]:
        """Get detailed platform information"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "is_macos": platform.system() == "Darwin",
            "is_linux": platform.system() == "Linux",
            "has_apple_silicon": platform.machine() == "arm64" and platform.system() == "Darwin",
            "hardware": self.node_config.get("hardware", {})
        }

    def _map_environment(self) -> Dict[str, Any]:
        """Map the node's unique environment"""
        env = {
            "storage_base": STORAGE_BASE,
            "claude_home": str(CLAUDE_HOME),
            "home_dir": str(Path.home()),
            "paths": {
                "agentic_system": STORAGE_BASE,
                "databases": str(Path(STORAGE_BASE) / "databases"),
                "mcp_servers": str(Path(STORAGE_BASE) / "mcp-servers"),
                "cluster": str(Path(STORAGE_BASE) / "cluster-deployment"),
                "logs": self.node_config.get('storage', {}).get('logs', str(Path(STORAGE_BASE) / "logs")),
                "scripts": str(Path(STORAGE_BASE) / "scripts"),
                "intelligent_agents": str(Path(STORAGE_BASE) / "intelligent-agents"),
            },
            "venvs": self._discover_venvs(),
            "path_translation": self._generate_path_translation()
        }
        return env

    def _discover_venvs(self) -> Dict[str, str]:
        """Discover Python virtual environments"""
        venvs = {}

        # Common venv locations to check
        venv_paths = [
            Path(STORAGE_BASE) / ".venv",
            Path(STORAGE_BASE) / "venv",
            Path(STORAGE_BASE) / "mcp-servers" / ".venv",
            Path(STORAGE_BASE) / "intelligent-agents" / ".venv",
            Path.home() / ".venvs",
        ]

        for venv_path in venv_paths:
            if venv_path.exists() and (venv_path / "bin" / "python").exists():
                venvs[str(venv_path)] = str(venv_path / "bin" / "python")

        return venvs

    def _generate_path_translation(self) -> Dict[str, str]:
        """
        Generate path translation rules for adapting foreign configs.

        This is crucial - when this node receives a feature from a peer,
        it needs to know how to translate paths.
        """
        is_macos = platform.system() == "Darwin"

        if is_macos:
            # macOS node - translate from Linux paths
            return {
                "/home/marc/agentic-system": STORAGE_BASE,
                "/mnt/agentic-system": STORAGE_BASE,
                "~": str(Path.home()),
            }
        else:
            # Linux node - translate from macOS paths
            return {
                "/Volumes/SSDRAID0/agentic-system": STORAGE_BASE,
                "~": str(Path.home()),
            }

    def _fingerprint_capabilities(self) -> Dict[str, Any]:
        """
        Generate capability fingerprint.

        What can this node actually DO?
        """
        caps = {
            "node_role": self.node_config.get("persona", "unknown"),
            "explicit_capabilities": self.node_config.get("capabilities", []),
            "detected_capabilities": [],
            "runtimes": {},
            "hardware_capabilities": []
        }

        # Detect runtimes
        caps["runtimes"] = {
            "python": self._check_command(["python3", "--version"]),
            "node": self._check_command(["node", "--version"]),
            "npm": self._check_command(["npm", "--version"]),
            "cargo": self._check_command(["cargo", "--version"]),
            "docker": self._check_command(["docker", "--version"]),
            "podman": self._check_command(["podman", "--version"]),
            "ollama": self._check_command(["ollama", "--version"]),
        }

        # Detect capabilities based on available tools
        detected = []
        if caps["runtimes"].get("docker") or caps["runtimes"].get("podman"):
            detected.append("containerization")
        if caps["runtimes"].get("cargo"):
            detected.append("rust-development")
        if caps["runtimes"].get("node"):
            detected.append("nodejs-development")
        if caps["runtimes"].get("ollama"):
            detected.append("local-llm-inference")

        # Linux-specific
        if platform.system() == "Linux":
            if self._check_command(["systemctl", "--version"]):
                detected.append("systemd-services")
            if self._check_command(["mdadm", "--version"]):
                detected.append("raid-management")
            if self._check_command(["semanage", "--help"]):
                detected.append("selinux-management")

        # macOS-specific
        if platform.system() == "Darwin":
            if self._check_command(["container", "help"]):
                detected.append("apple-container")
            if Path("/usr/local/opt/temporal").exists():
                detected.append("temporal-server")

        caps["detected_capabilities"] = detected

        # Hardware capabilities
        hw = self.node_config.get("hardware", {})
        if "gpu" in str(hw).lower() or "cuda" in str(hw).lower():
            caps["hardware_capabilities"].append("gpu-inference")
        if hw.get("chip", "").startswith("Apple"):
            caps["hardware_capabilities"].append("apple-silicon")
        if "xeon" in str(hw).lower():
            caps["hardware_capabilities"].append("multi-core-x86")

        return caps

    def _check_command(self, cmd: List[str]) -> Optional[str]:
        """Check if a command exists and get version"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def _catalog_claude_config(self) -> Dict[str, Any]:
        """Catalog Claude Code configuration"""
        config = {
            "hooks": self._catalog_hooks(),
            "agents": self._catalog_items(CLAUDE_HOME / "agents", "*.md"),
            "skills": self._catalog_items(CLAUDE_HOME / "skills", "*.md"),
            "commands": self._catalog_items(CLAUDE_HOME / "commands", "*.md"),
            "mcp_servers": self._catalog_mcp_servers(),
            "permissions": self._catalog_permissions(),
        }
        return config

    def _catalog_hooks(self) -> Dict[str, Any]:
        """Catalog all hooks with their content hashes"""
        hooks = {
            "count": 0,
            "types": {},
            "helper_modules": []
        }

        settings_file = CLAUDE_HOME / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    hook_config = settings.get("hooks", {})

                    for hook_type in ["SessionStart", "SessionEnd", "PreToolUse", "PostToolUse"]:
                        hook_list = hook_config.get(hook_type, [])
                        hooks["types"][hook_type] = []
                        for hook_group in hook_list:
                            for hook in hook_group.get("hooks", []):
                                cmd = hook.get("command", "")
                                hooks["types"][hook_type].append(cmd)
                                hooks["count"] += 1
            except Exception as e:
                logger.warning(f"Error reading hooks: {e}")

        # Catalog helper modules
        hooks_dir = CLAUDE_HOME / "hooks"
        if hooks_dir.exists():
            for py_file in hooks_dir.glob("*.py"):
                # Skip if file doesn't exist (broken symlink, etc.)
                if not py_file.exists():
                    continue
                try:
                    hooks["helper_modules"].append({
                        "name": py_file.name,
                        "size": py_file.stat().st_size,
                        "hash": self._file_hash(py_file)
                    })
                except (OSError, IOError) as e:
                    logger.warning(f"Error reading hook file {py_file}: {e}")

        return hooks

    def _catalog_items(self, directory: Path, pattern: str) -> Dict[str, Any]:
        """Catalog items in a directory with content hashes"""
        result = {"count": 0, "items": []}

        if directory.exists():
            for item in directory.glob(pattern):
                result["items"].append({
                    "name": item.stem,
                    "file": item.name,
                    "size": item.stat().st_size,
                    "hash": self._file_hash(item)
                })
            result["count"] = len(result["items"])

        return result

    def _catalog_mcp_servers(self) -> Dict[str, Any]:
        """Catalog MCP server configurations"""
        mcp = {
            "user_level": {},
            "project_level": {},
            "total": 0
        }

        # User-level (in home directory)
        user_mcp = Path.home() / ".claude.json"
        if user_mcp.exists():
            try:
                with open(user_mcp) as f:
                    config = json.load(f)
                    for name, server in config.get("mcpServers", {}).items():
                        mcp["user_level"][name] = {
                            "command": server.get("command", ""),
                            "disabled": server.get("disabled", False)
                        }
            except Exception as e:
                logger.warning(f"Error reading user MCP config: {e}")

        mcp["total"] = len(mcp["user_level"]) + len(mcp["project_level"])
        return mcp

    def _catalog_permissions(self) -> Dict[str, Any]:
        """Catalog tool permissions"""
        perms = {"allow": [], "deny": []}

        settings_file = CLAUDE_HOME / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    p = settings.get("permissions", {})
                    perms["allow"] = p.get("allow", [])
                    perms["deny"] = p.get("deny", [])
            except Exception as e:
                logger.warning(f"Error reading permissions: {e}")

        return perms

    def _discover_services(self) -> Dict[str, Any]:
        """Discover running services relevant to the agentic system"""
        services = {
            "mcp_ports": self.node_config.get("mcp_servers", {}),
            "detected_services": [],
            "systemd_units": []
        }

        # Check common ports
        port_checks = {
            8101: "enhanced-memory",
            8102: "agent-runtime",
            8103: "node-chat",
            6333: "qdrant",
            11434: "ollama",
            9000: "builder-api",
            4100: "kutira-framework",
            3002: "kutira-api",
        }

        for port, service in port_checks.items():
            if self._check_port(port):
                services["detected_services"].append({
                    "name": service,
                    "port": port,
                    "status": "running"
                })

        # Linux: Check systemd user units
        if platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "list-units", "--type=service", "--state=running"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'kutira' in line.lower() or 'agentic' in line.lower() or 'builder' in line.lower():
                            services["systemd_units"].append(line.strip())
            except Exception:
                pass

        return services

    def _check_port(self, port: int) -> bool:
        """Check if a port is in use"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def _generate_adaptation_map(self) -> Dict[str, Any]:
        """
        Generate rules for adapting foreign features to this node.

        This is the KEY to curiosity-driven propagation - knowing HOW
        to integrate features from other nodes.
        """
        return {
            "path_rules": self._generate_path_translation(),
            "venv_strategy": "use_local_venv" if self._discover_venvs() else "create_new",
            "package_manager": "pip3" if platform.system() == "Linux" else "pip3",
            "service_manager": "systemd" if platform.system() == "Linux" else "launchd",
            "container_runtime": "podman" if platform.system() == "Linux" else "docker",
            "adaptation_notes": self._get_adaptation_notes()
        }

    def _get_adaptation_notes(self) -> List[str]:
        """Node-specific adaptation notes"""
        notes = []

        if self.node_id == "macpro51":
            notes.extend([
                "Linux x86_64 - use Podman for containers",
                "No local GPU - offload inference to cluster nodes",
                "RAID10 storage at /mnt/agentic-system",
                "Systemd user services for daemon management"
            ])
        elif self.node_id == "mac-studio":
            notes.extend([
                "macOS ARM64 - Apple Silicon optimizations available",
                "Primary orchestrator - receives all cluster updates",
                "Apple Container preferred for containerization",
                "Temporal server available locally"
            ])
        elif self.node_id == "macbook-air":
            notes.extend([
                "macOS ARM64 - Apple Silicon",
                "Researcher role - focus on analysis tasks",
                "Mobile workstation - battery-conscious operations"
            ])
        elif self.node_id == "completeu-server":
            notes.extend([
                "AI inference node - GPU available",
                "Ollama primary host - 23+ models",
                "Dedicated to inference workloads"
            ])

        return notes

    def _file_hash(self, filepath: Path) -> str:
        """Generate short hash of file contents"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:12]
        except Exception:
            return "unknown"

    def save_identity(self):
        """Save identity to cluster database"""
        if not self.identity:
            self.generate_identity()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create identity table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_identities (
                node_id TEXT PRIMARY KEY,
                identity_hash TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                platform_json TEXT,
                environment_json TEXT,
                capabilities_json TEXT,
                claude_config_json TEXT,
                services_json TEXT,
                adaptation_map_json TEXT,
                full_identity_json TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        # Upsert identity
        cursor.execute("""
            INSERT OR REPLACE INTO node_identities
            (node_id, identity_hash, generated_at, platform_json, environment_json,
             capabilities_json, claude_config_json, services_json, adaptation_map_json,
             full_identity_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.identity["node_id"],
            self.identity["identity_hash"],
            self.identity["generated_at"],
            json.dumps(self.identity["platform"]),
            json.dumps(self.identity["environment"]),
            json.dumps(self.identity["capabilities"]),
            json.dumps(self.identity["claude_config"]),
            json.dumps(self.identity["services"]),
            json.dumps(self.identity["adaptation_map"]),
            json.dumps(self.identity),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Identity saved for {self.node_id} (hash: {self.identity['identity_hash']})")

    def get_peer_identities(self) -> List[Dict]:
        """Get identities of all peer nodes"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT node_id, identity_hash, full_identity_json, updated_at
            FROM node_identities
            WHERE node_id != ?
            ORDER BY updated_at DESC
        """, (self.node_id,))

        peers = []
        for row in cursor.fetchall():
            peers.append({
                "node_id": row[0],
                "identity_hash": row[1],
                "identity": json.loads(row[2]) if row[2] else {},
                "updated_at": row[3]
            })

        conn.close()
        return peers

    def compare_with_peer(self, peer_identity: Dict) -> Dict[str, Any]:
        """
        Compare this node's identity with a peer's.

        Returns what the peer has that we don't (the basis for curiosity).
        """
        if not self.identity:
            self.generate_identity()

        comparison = {
            "peer_node": peer_identity.get("node_id"),
            "our_node": self.node_id,
            "features_peer_has": [],
            "features_we_have": [],
            "shared_features": [],
            "adaptation_required": []
        }

        # Compare Claude configs
        our_config = self.identity["claude_config"]
        peer_config = peer_identity.get("claude_config", {})

        # Compare agents
        our_agents = set(a["name"] for a in our_config.get("agents", {}).get("items", []))
        peer_agents = set(a["name"] for a in peer_config.get("agents", {}).get("items", []))

        comparison["features_peer_has"].extend([
            {"type": "agent", "name": a} for a in (peer_agents - our_agents)
        ])
        comparison["features_we_have"].extend([
            {"type": "agent", "name": a} for a in (our_agents - peer_agents)
        ])
        comparison["shared_features"].extend([
            {"type": "agent", "name": a} for a in (our_agents & peer_agents)
        ])

        # Compare skills
        our_skills = set(s["name"] for s in our_config.get("skills", {}).get("items", []))
        peer_skills = set(s["name"] for s in peer_config.get("skills", {}).get("items", []))

        comparison["features_peer_has"].extend([
            {"type": "skill", "name": s} for s in (peer_skills - our_skills)
        ])
        comparison["features_we_have"].extend([
            {"type": "skill", "name": s} for s in (our_skills - peer_skills)
        ])

        # Compare commands
        our_cmds = set(c["name"] for c in our_config.get("commands", {}).get("items", []))
        peer_cmds = set(c["name"] for c in peer_config.get("commands", {}).get("items", []))

        comparison["features_peer_has"].extend([
            {"type": "command", "name": c} for c in (peer_cmds - our_cmds)
        ])

        # Compare MCP servers
        our_mcp = set(our_config.get("mcp_servers", {}).get("user_level", {}).keys())
        peer_mcp = set(peer_config.get("mcp_servers", {}).get("user_level", {}).keys())

        comparison["features_peer_has"].extend([
            {"type": "mcp_server", "name": m} for m in (peer_mcp - our_mcp)
        ])

        # Compare hooks helper modules
        our_helpers = set(h["name"] for h in our_config.get("hooks", {}).get("helper_modules", []))
        peer_helpers = set(h["name"] for h in peer_config.get("hooks", {}).get("helper_modules", []))

        comparison["features_peer_has"].extend([
            {"type": "hook_helper", "name": h} for h in (peer_helpers - our_helpers)
        ])

        # Note what adaptations are needed
        for feature in comparison["features_peer_has"]:
            comparison["adaptation_required"].append({
                "feature": feature,
                "needs_path_translation": True,
                "needs_venv_setup": feature["type"] in ["mcp_server", "hook_helper"],
                "platform_compatible": self._check_compatibility(feature, peer_identity)
            })

        return comparison

    def _check_compatibility(self, feature: Dict, peer_identity: Dict) -> bool:
        """Check if a feature from peer is compatible with this node"""
        # Most features are compatible - just need path translation
        # Some may have platform-specific requirements
        peer_platform = peer_identity.get("platform", {}).get("system", "")
        our_platform = platform.system()

        # Check for obvious incompatibilities
        feature_name = feature.get("name", "").lower()

        if "apple" in feature_name and our_platform != "Darwin":
            return False
        if "linux" in feature_name and our_platform != "Linux":
            return False
        if "systemd" in feature_name and our_platform != "Linux":
            return False
        if "launchd" in feature_name and our_platform != "Darwin":
            return False

        return True


def main():
    """Generate and display node identity"""
    service = NodeIdentityService()
    identity = service.generate_identity()
    service.save_identity()

    print("\n" + "="*80)
    print(f"NODE IDENTITY: {identity['node_id']}")
    print("="*80)
    print(f"Identity Hash: {identity['identity_hash']}")
    print(f"Platform: {identity['platform']['system']} {identity['platform']['machine']}")
    print(f"Storage Base: {identity['environment']['storage_base']}")
    print()
    print("CAPABILITIES:")
    print(f"  Role: {identity['capabilities']['node_role']}")
    print(f"  Explicit: {', '.join(identity['capabilities']['explicit_capabilities'])}")
    print(f"  Detected: {', '.join(identity['capabilities']['detected_capabilities'])}")
    print()
    print("CLAUDE CONFIG:")
    cc = identity['claude_config']
    print(f"  Agents: {cc['agents']['count']}")
    print(f"  Skills: {cc['skills']['count']}")
    print(f"  Commands: {cc['commands']['count']}")
    print(f"  MCP Servers: {cc['mcp_servers']['total']}")
    print(f"  Hook Helpers: {len(cc['hooks']['helper_modules'])}")
    print()
    print("ADAPTATION MAP:")
    am = identity['adaptation_map']
    print(f"  Venv Strategy: {am['venv_strategy']}")
    print(f"  Container Runtime: {am['container_runtime']}")
    print(f"  Service Manager: {am['service_manager']}")
    print("  Notes:")
    for note in am['adaptation_notes']:
        print(f"    - {note}")
    print("="*80)

    # Check for peers
    peers = service.get_peer_identities()
    if peers:
        print(f"\nPEER NODES: {len(peers)}")
        for peer in peers:
            print(f"  - {peer['node_id']} (hash: {peer['identity_hash']})")

        # Compare with first peer
        print(f"\nCOMPARISON WITH {peers[0]['node_id']}:")
        comparison = service.compare_with_peer(peers[0]['identity'])
        print(f"  Features they have that we don't: {len(comparison['features_peer_has'])}")
        for f in comparison['features_peer_has'][:5]:
            print(f"    - {f['type']}: {f['name']}")
        if len(comparison['features_peer_has']) > 5:
            print(f"    ... and {len(comparison['features_peer_has']) - 5} more")

    print()


if __name__ == "__main__":
    main()
