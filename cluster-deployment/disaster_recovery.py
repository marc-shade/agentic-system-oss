#!/usr/bin/env python3
"""
Disaster Recovery System
========================

Enables rapid node recovery when OS reinstall or hardware failure occurs.

Key Features:
1. Centralized config storage (replicated across all nodes)
2. One-command node bootstrap
3. Automatic config sync from surviving nodes
4. State recovery from cluster backups
5. Self-healing cluster topology

Recovery Scenarios:
- Node OS reinstall: Pull config from cluster, run bootstrap
- Hardware failure: Replace hardware, bootstrap new node
- Complete cluster recovery: Bootstrap from offsite backup

Usage:
    # From a working node, prepare recovery bundle:
    python3 disaster_recovery.py bundle --for-node macpro51

    # On freshly installed node:
    curl -sSL http://surviving-node:9000/bootstrap/macpro51.sh | bash

    # Or manually:
    python3 disaster_recovery.py bootstrap --from-node mac-studio
"""
import platform

import os
import sys
import json
import time
import shutil
import socket
import hashlib
import tarfile
import sqlite3
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime


# =============================================================================
# Configuration - What makes a node an "agentic node"
# =============================================================================

NODE_CONFIGS = {
    "mac-studio": {
        "os": "macos",
        "arch": "arm64",
        "role": "orchestrator",
        "storage_base": str(_STORAGE_BASE),
        "ssh_user": "marc",
        "services": ["temporal", "autokitteh", "monitoring"],
        "special_hardware": ["arduino"],
    },
    "macbook-air-m3": {
        "os": "macos",
        "arch": "arm64",
        "role": "researcher",
        "storage_base": "/Users/marc/agentic-system",
        "ssh_user": "marc",
        "services": ["claude-code"],
        "special_hardware": [],
    },
    "completeu-server": {
        "os": "macos",
        "arch": "arm64",
        "role": "inference",
        "storage_base": str(_STORAGE_BASE),
        "ssh_user": "marc",
        "services": ["ollama", "mlx"],
        "special_hardware": [],
    },
    "macpro51": {
        "os": "linux",
        "arch": "x86_64",
        "role": "builder",
        "storage_base": str(_STORAGE_BASE),
        "ssh_user": "marc",
        "services": ["podman", "builder-api", "monitoring"],
        "special_hardware": ["raid10"],
    },
}

# Files/directories critical for node recovery
CRITICAL_CONFIGS = [
    # Claude Code configuration
    "~/.claude.json",
    "~/.claude/settings.json",
    "~/.claude/settings.local.json",
    "~/.claude/node-config.json",

    # SSH keys (for cluster communication)
    "~/.ssh/id_ed25519",
    "~/.ssh/id_ed25519.pub",
    "~/.ssh/authorized_keys",
    "~/.ssh/config",

    # Git configuration
    "~/.gitconfig",

    # Shell configuration
    "~/.bashrc",
    "~/.zshrc",
    "~/.config/fish/config.fish",
]

# Project files needed for bootstrap
PROJECT_ESSENTIAL = [
    "CLAUDE.md",
    "cluster-deployment/cluster-nodes.json",
    "cluster-deployment/node_discovery.py",
    "cluster-deployment/resilient_cluster.py",
    "scripts/init-node.sh",
    "scripts/detect-storage.sh",
    "mcp-servers/enhanced-memory-mcp/requirements.txt",
    ".claude/",
    ".mcp.json",
]


# =============================================================================
# Recovery Bundle
# =============================================================================

@dataclass
class RecoveryBundle:
    """Everything needed to restore a node."""
    node_id: str
    created_at: float
    created_by: str
    config: dict
    files: Dict[str, bytes]  # path -> content
    databases: Dict[str, bytes]  # db_name -> sqlite backup
    secrets_hash: str  # For verification (not actual secrets)

    def to_archive(self, output_path: str):
        """Create tar.gz archive of recovery bundle."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / f"recovery_{self.node_id}"
            bundle_dir.mkdir()

            # Write manifest
            manifest = {
                "node_id": self.node_id,
                "created_at": self.created_at,
                "created_by": self.created_by,
                "config": self.config,
                "files": list(self.files.keys()),
                "databases": list(self.databases.keys()),
                "secrets_hash": self.secrets_hash,
            }
            (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

            # Write files
            files_dir = bundle_dir / "files"
            files_dir.mkdir()
            for path, content in self.files.items():
                safe_path = path.replace("/", "_").replace("~", "HOME")
                (files_dir / safe_path).write_bytes(content)

            # Write databases
            db_dir = bundle_dir / "databases"
            db_dir.mkdir()
            for name, content in self.databases.items():
                (db_dir / f"{name}.db").write_bytes(content)

            # Create archive
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(bundle_dir, arcname=f"recovery_{self.node_id}")

    @classmethod
    def from_archive(cls, archive_path: str) -> 'RecoveryBundle':
        """Load recovery bundle from archive."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(tmpdir)

            # Find bundle directory
            bundle_dirs = list(Path(tmpdir).glob("recovery_*"))
            if not bundle_dirs:
                raise ValueError("Invalid recovery archive")

            bundle_dir = bundle_dirs[0]

            # Read manifest
            manifest = json.loads((bundle_dir / "manifest.json").read_text())

            # Read files
            files = {}
            files_dir = bundle_dir / "files"
            if files_dir.exists():
                for f in files_dir.iterdir():
                    original_path = f.name.replace("_", "/").replace("HOME", "~")
                    files[original_path] = f.read_bytes()

            # Read databases
            databases = {}
            db_dir = bundle_dir / "databases"
            if db_dir.exists():
                for f in db_dir.glob("*.db"):
                    databases[f.stem] = f.read_bytes()

            return cls(
                node_id=manifest["node_id"],
                created_at=manifest["created_at"],
                created_by=manifest["created_by"],
                config=manifest["config"],
                files=files,
                databases=databases,
                secrets_hash=manifest["secrets_hash"],
            )


# =============================================================================
# Disaster Recovery Manager
# =============================================================================

class DisasterRecoveryManager:
    """
    Manages disaster recovery for the cluster.

    Can run on any node to:
    - Create recovery bundles for any node
    - Serve bootstrap scripts
    - Coordinate recovery operations
    """

    def __init__(self, node_id: str = None, storage_base: str = None):
        self.node_id = node_id or self._detect_node_id()

        if storage_base is None:
            config = NODE_CONFIGS.get(self.node_id, {})
            storage_base = config.get("storage_base", "~/agentic-system")

        self.storage_base = Path(os.path.expanduser(storage_base))
        self.recovery_dir = self.storage_base / "disaster-recovery"
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

    def _detect_node_id(self) -> str:
        """Auto-detect node ID."""
        hostname = socket.gethostname().lower()

        if "macpro" in hostname:
            return "macpro51"
        elif "studio" in hostname:
            return "mac-studio"
        elif "air" in hostname:
            return "macbook-air-m3"
        elif "completeu" in hostname:
            return "completeu-server"
        return hostname

    def create_recovery_bundle(self, for_node: str = None) -> str:
        """
        Create a recovery bundle for a node.

        Args:
            for_node: Target node (defaults to self)

        Returns:
            Path to created bundle archive
        """
        target_node = for_node or self.node_id
        print(f"Creating recovery bundle for {target_node}...")

        config = NODE_CONFIGS.get(target_node, {})
        files = {}
        databases = {}

        # Collect critical config files
        for path in CRITICAL_CONFIGS:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                try:
                    if os.path.isfile(expanded):
                        files[path] = Path(expanded).read_bytes()
                    elif os.path.isdir(expanded):
                        # For directories, create tarball
                        pass  # Skip for now
                except PermissionError:
                    print(f"  Warning: Cannot read {path}")

        # Collect project essential files
        for path in PROJECT_ESSENTIAL:
            full_path = self.storage_base / path
            if full_path.exists():
                if full_path.is_file():
                    files[path] = full_path.read_bytes()

        # Backup critical databases
        db_paths = [
            self.storage_base / "databases/cluster/shared_memories.db",
            self.storage_base / "databases/cluster/node_registry.db",
            self.storage_base / "databases/cluster/cluster_state.db",
            self.storage_base / "databases/mcp/agent_runtime.db",
        ]

        for db_path in db_paths:
            if db_path.exists():
                try:
                    databases[db_path.stem] = db_path.read_bytes()
                except Exception as e:
                    print(f"  Warning: Cannot backup {db_path}: {e}")

        # Create secrets hash (for verification)
        secrets_content = ""
        for secret_file in ["~/.ssh/id_ed25519.pub"]:
            expanded = os.path.expanduser(secret_file)
            if os.path.exists(expanded):
                secrets_content += Path(expanded).read_text()
        secrets_hash = hashlib.sha256(secrets_content.encode()).hexdigest()[:16]

        # Create bundle
        bundle = RecoveryBundle(
            node_id=target_node,
            created_at=time.time(),
            created_by=self.node_id,
            config=config,
            files=files,
            databases=databases,
            secrets_hash=secrets_hash,
        )

        # Save to recovery directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = str(self.recovery_dir / f"recovery_{target_node}_{timestamp}.tar.gz")
        bundle.to_archive(archive_path)

        print(f"Created recovery bundle: {archive_path}")
        print(f"  Files: {len(files)}")
        print(f"  Databases: {len(databases)}")
        print(f"  Secrets hash: {secrets_hash}")

        return archive_path

    def generate_bootstrap_script(self, target_node: str) -> str:
        """
        Generate a bootstrap script for a fresh node.

        This script can be run on a freshly installed OS to
        join the cluster.
        """
        config = NODE_CONFIGS.get(target_node, {})

        if config.get("os") == "linux":
            return self._generate_linux_bootstrap(target_node, config)
        else:
            return self._generate_macos_bootstrap(target_node, config)

    def _generate_linux_bootstrap(self, node_id: str, config: dict) -> str:
        """Generate bootstrap script for Linux (Fedora)."""
        storage_base = config.get("storage_base", str(_STORAGE_BASE))

        return f'''#!/bin/bash
# Bootstrap script for {node_id} (Linux)
# Generated by disaster_recovery.py
# Run: curl -sSL http://surviving-node:9000/bootstrap/{node_id}.sh | bash

set -e

echo "=== Bootstrapping {node_id} ==="
echo "Storage base: {storage_base}"

# 1. Install required packages
echo "[1/8] Installing packages..."
sudo dnf install -y \\
    git python3 python3-pip python3-venv \\
    podman docker-compose \\
    sqlite avahi avahi-tools \\
    curl wget jq \\
    nodejs npm

# 2. Create storage directory
echo "[2/8] Setting up storage..."
sudo mkdir -p {storage_base}
sudo chown $USER:$USER {storage_base}

# 3. Clone or sync agentic-system
echo "[3/8] Syncing agentic-system..."
if [ -d "{storage_base}/.git" ]; then
    cd {storage_base} && git pull
else
    # Try to clone from another node
    SURVIVING_NODES=("mac-studio" "completeu-server" "macbook-air-m3")
    for node in "${{SURVIVING_NODES[@]}}"; do
        if ping -c 1 -W 2 "$node.local" &>/dev/null; then
            echo "Syncing from $node..."
            rsync -avz --progress "$node.local:{storage_base}/" "{storage_base}/" || true
            break
        fi
    done
fi

cd {storage_base}

# 4. Setup Python environment
echo "[4/8] Setting up Python..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r mcp-servers/enhanced-memory-mcp/requirements.txt

# 5. Restore SSH keys from cluster
echo "[5/8] Restoring SSH keys..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Try to get keys from surviving node
for node in "${{SURVIVING_NODES[@]}}"; do
    if ping -c 1 -W 2 "$node.local" &>/dev/null; then
        echo "Fetching SSH keys from $node..."
        scp "$node.local:~/.ssh/id_ed25519" ~/.ssh/ 2>/dev/null || true
        scp "$node.local:~/.ssh/id_ed25519.pub" ~/.ssh/ 2>/dev/null || true
        scp "$node.local:~/.ssh/authorized_keys" ~/.ssh/ 2>/dev/null || true
        chmod 600 ~/.ssh/id_ed25519 2>/dev/null || true
        break
    fi
done

# 6. Setup Claude Code config
echo "[6/8] Configuring Claude Code..."
mkdir -p ~/.claude

# Restore from bundle or create minimal config
if [ -f "{storage_base}/disaster-recovery/recovery_{node_id}_latest.tar.gz" ]; then
    echo "Restoring from recovery bundle..."
    cd {storage_base}
    python3 disaster_recovery.py restore --bundle disaster-recovery/recovery_{node_id}_latest.tar.gz
else
    # Create minimal config
    cat > ~/.claude.json << 'CLAUDEJSON'
{{
  "version": "1.0",
  "mcpServers": {{
    "enhanced-memory": {{
      "command": "python3",
      "args": ["{storage_base}/mcp-servers/enhanced-memory-mcp/server.py"],
      "env": {{}},
      "disabled": false
    }},
    "agent-runtime": {{
      "command": "python3",
      "args": ["{storage_base}/mcp-servers/agent-runtime-mcp/server.py"],
      "env": {{}},
      "disabled": false
    }}
  }}
}}
CLAUDEJSON
fi

# 7. Setup services
echo "[7/8] Setting up services..."
cd {storage_base}
./scripts/init-node.sh

# Enable systemd services
if [ -f "services/systemd/builder-node-api.service" ]; then
    mkdir -p ~/.config/systemd/user
    cp services/systemd/*.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable builder-node-api
    systemctl --user start builder-node-api
fi

# 8. Join cluster
echo "[8/8] Joining cluster..."
cd {storage_base}/cluster-deployment
python3 resilient_cluster.py --status

echo ""
echo "=== Bootstrap Complete ==="
echo "Node {node_id} is ready!"
echo ""
echo "Next steps:"
echo "  1. Verify: python3 system_health_check.py"
echo "  2. Start daemon: python3 cluster-deployment/resilient_cluster.py"
echo ""
'''

    def _generate_macos_bootstrap(self, node_id: str, config: dict) -> str:
        """Generate bootstrap script for macOS."""
        storage_base = config.get("storage_base", "~/agentic-system")

        return f'''#!/bin/bash
# Bootstrap script for {node_id} (macOS)
# Generated by disaster_recovery.py
# Run: curl -sSL http://surviving-node:9000/bootstrap/{node_id}.sh | bash

set -e

echo "=== Bootstrapping {node_id} ==="
echo "Storage base: {storage_base}"

# 1. Install Homebrew if needed
if ! command -v brew &>/dev/null; then
    echo "[1/8] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. Install required packages
echo "[2/8] Installing packages..."
brew install python3 node git sqlite jq

# 3. Create storage directory
echo "[3/8] Setting up storage..."
mkdir -p {storage_base}

# 4. Sync from surviving node
echo "[4/8] Syncing agentic-system..."
SURVIVING_NODES=("mac-studio" "completeu-server" "macbook-air-m3" "macpro51")
for node in "${{SURVIVING_NODES[@]}}"; do
    if [ "$node" != "{node_id}" ]; then
        if ping -c 1 -W 2 "$node.local" &>/dev/null; then
            echo "Syncing from $node..."
            rsync -avz --progress "marc@$node.local:~/agentic-system/" "{storage_base}/" || true
            break
        fi
    fi
done

cd {storage_base}

# 5. Setup Python environment
echo "[5/8] Setting up Python..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r mcp-servers/enhanced-memory-mcp/requirements.txt

# 6. Restore SSH keys
echo "[6/8] Restoring SSH keys..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

for node in "${{SURVIVING_NODES[@]}}"; do
    if [ "$node" != "{node_id}" ]; then
        if ping -c 1 -W 2 "$node.local" &>/dev/null; then
            scp "marc@$node.local:~/.ssh/id_ed25519" ~/.ssh/ 2>/dev/null || true
            scp "marc@$node.local:~/.ssh/id_ed25519.pub" ~/.ssh/ 2>/dev/null || true
            chmod 600 ~/.ssh/id_ed25519 2>/dev/null || true
            break
        fi
    fi
done

# 7. Setup Claude Code
echo "[7/8] Configuring Claude Code..."
mkdir -p ~/.claude

# Run init-node
./scripts/init-node.sh

# 8. Join cluster
echo "[8/8] Joining cluster..."
cd {storage_base}/cluster-deployment
python3 resilient_cluster.py --status

echo ""
echo "=== Bootstrap Complete ==="
echo "Node {node_id} is ready!"
'''

    def restore_from_bundle(self, bundle_path: str, dry_run: bool = False):
        """
        Restore node from recovery bundle.

        Args:
            bundle_path: Path to recovery archive
            dry_run: If True, only show what would be done
        """
        print(f"Restoring from bundle: {bundle_path}")

        bundle = RecoveryBundle.from_archive(bundle_path)
        print(f"  Node: {bundle.node_id}")
        print(f"  Created: {datetime.fromtimestamp(bundle.created_at)}")
        print(f"  Files: {len(bundle.files)}")
        print(f"  Databases: {len(bundle.databases)}")

        if dry_run:
            print("\n[DRY RUN] Would restore:")
            for path in bundle.files:
                print(f"  File: {path}")
            for name in bundle.databases:
                print(f"  Database: {name}")
            return

        # Restore files
        for path, content in bundle.files.items():
            target = os.path.expanduser(path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            Path(target).write_bytes(content)
            print(f"  Restored: {path}")

        # Restore databases
        db_dir = self.storage_base / "databases/cluster"
        db_dir.mkdir(parents=True, exist_ok=True)

        for name, content in bundle.databases.items():
            target = db_dir / f"{name}.db"
            target.write_bytes(content)
            print(f"  Restored database: {name}")

        print("\nRestore complete!")

    def list_bundles(self) -> List[dict]:
        """List available recovery bundles."""
        bundles = []
        for f in self.recovery_dir.glob("recovery_*.tar.gz"):
            try:
                stat = f.stat()
                parts = f.stem.split("_")
                bundles.append({
                    "path": str(f),
                    "node_id": parts[1] if len(parts) > 1 else "unknown",
                    "timestamp": parts[2] if len(parts) > 2 else "unknown",
                    "size_mb": stat.st_size / (1024 * 1024),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                pass
        return sorted(bundles, key=lambda x: x["created"], reverse=True)

    def sync_bundles_to_nodes(self) -> Dict[str, bool]:
        """
        Sync recovery bundles to all other nodes.
        Ensures bundles are available even if this node dies.
        """
        results = {}

        for node_id, config in NODE_CONFIGS.items():
            if node_id == self.node_id:
                continue

            target_base = config.get("storage_base", "~/agentic-system")

            # Try to sync via rsync
            for hostname in [f"{node_id}.local", config.get("storage_base", "").split("/")[0]]:
                try:
                    cmd = [
                        "rsync", "-avz", "--progress",
                        str(self.recovery_dir) + "/",
                        f"marc@{hostname}:{target_base}/disaster-recovery/"
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=60)
                    results[node_id] = result.returncode == 0
                    if results[node_id]:
                        print(f"  Synced to {node_id}")
                        break
                except Exception as e:
                    results[node_id] = False

        return results


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

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


    parser = argparse.ArgumentParser(description="Disaster Recovery Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # bundle command
    bundle_parser = subparsers.add_parser("bundle", help="Create recovery bundle")
    bundle_parser.add_argument("--for-node", help="Target node ID")

    # bootstrap command
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Generate bootstrap script")
    bootstrap_parser.add_argument("--node", required=True, help="Target node ID")
    bootstrap_parser.add_argument("--output", help="Output file path")

    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from bundle")
    restore_parser.add_argument("--bundle", required=True, help="Bundle archive path")
    restore_parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    # list command
    subparsers.add_parser("list", help="List recovery bundles")

    # sync command
    subparsers.add_parser("sync", help="Sync bundles to all nodes")

    # status command
    subparsers.add_parser("status", help="Show disaster recovery status")

    args = parser.parse_args()

    manager = DisasterRecoveryManager()

    if args.command == "bundle":
        manager.create_recovery_bundle(args.for_node)

    elif args.command == "bootstrap":
        script = manager.generate_bootstrap_script(args.node)
        if args.output:
            Path(args.output).write_text(script)
            os.chmod(args.output, 0o755)
            print(f"Bootstrap script written to: {args.output}")
        else:
            print(script)

    elif args.command == "restore":
        manager.restore_from_bundle(args.bundle, args.dry_run)

    elif args.command == "list":
        bundles = manager.list_bundles()
        if not bundles:
            print("No recovery bundles found")
        else:
            print("Available recovery bundles:")
            print("-" * 60)
            for b in bundles:
                print(f"  {b['node_id']:20} {b['timestamp']:15} {b['size_mb']:.1f}MB")
            print(f"\nTotal: {len(bundles)} bundles")

    elif args.command == "sync":
        print("Syncing recovery bundles to all nodes...")
        results = manager.sync_bundles_to_nodes()
        for node, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {node}: {status}")

    elif args.command == "status":
        bundles = manager.list_bundles()
        print(f"Disaster Recovery Status")
        print("=" * 50)
        print(f"Node: {manager.node_id}")
        print(f"Storage: {manager.storage_base}")
        print(f"Recovery dir: {manager.recovery_dir}")
        print(f"Bundles available: {len(bundles)}")

        if bundles:
            print(f"\nLatest bundle:")
            latest = bundles[0]
            print(f"  Node: {latest['node_id']}")
            print(f"  Created: {latest['created']}")
            print(f"  Size: {latest['size_mb']:.1f}MB")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
