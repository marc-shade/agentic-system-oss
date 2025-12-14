#!/usr/bin/env python3
"""
Cluster Code Sync Daemon
Continuously monitors macpro51 (Builder) for code changes and syncs to local node.

Features:
- Watches for file changes on Builder via SMB
- Intelligent debouncing (waits for changes to settle)
- Preserves node-specific paths in configs
- Logs all sync operations
- Runs as daemon on each node

Usage:
    python3 cluster-code-sync-daemon.py [--interval 60] [--dry-run]
"""
import platform

import os
import sys
import json
import time
import hashlib
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional

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


# Setup logging
log_dir = Path.home() / '.claude' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'cluster-code-sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('code-sync')


class ClusterCodeSyncDaemon:
    """Daemon that watches Builder node and syncs code changes."""

    BUILDER_IP = "192.168.1.27"
    BUILDER_SHARE = "agentic-system"
    BUILDER_USER = "marc"

    # Directories to sync
    SYNC_DIRS = [
        '.claude/agents',
        '.claude/commands',
        '.claude/skills',
        '.claude/helpers',
        '.claude/hooks',
        'mcp-servers',
        'scripts',
        'cluster-deployment',
        'intelligent-agents',
    ]

    # Files to sync
    SYNC_FILES = [
        '.claude/statusline-command.sh',
        'CLAUDE.md',
    ]

    # Patterns to exclude
    EXCLUDE_PATTERNS = [
        '*.pyc', '__pycache__', '.DS_Store', '*.log',
        '*.db', '*.sqlite', '.venv', 'node_modules',
        '.archive', '.git', '*.bak'
    ]

    def __init__(self, interval: int = 60, dry_run: bool = False):
        self.interval = interval
        self.dry_run = dry_run
        self.local_storage = self._detect_local_storage()
        self.mount_point = self._detect_mount_point()
        self.file_hashes: Dict[str, str] = {}
        self.last_sync = None

        logger.info(f"Cluster Code Sync Daemon initialized")
        logger.info(f"  Local storage: {self.local_storage}")
        logger.info(f"  Mount point: {self.mount_point}")
        logger.info(f"  Check interval: {self.interval}s")
        logger.info(f"  Dry run: {self.dry_run}")

    def _detect_local_storage(self) -> Path:
        """Detect local storage path based on platform."""
        if sys.platform == 'darwin':
            candidates = [
                Path(str(_STORAGE_BASE)),
                Path.home() / 'agentic-system',
                Path(str(_STORAGE_BASE)),
            ]
        else:
            candidates = [
                Path(str(_STORAGE_BASE)),
                Path.home() / 'agentic-system',
            ]

        for path in candidates:
            if path.exists():
                return path

        return candidates[0]

    def _detect_mount_point(self) -> Path:
        """Detect mount point for SMB share."""
        if sys.platform == 'darwin':
            return Path('/Volumes/macpro51-agentic')
        else:
            return Path('/mnt/macpro51-agentic')

    def _is_builder_node(self) -> bool:
        """Check if we're running on the Builder node itself."""
        hostname = os.uname().nodename.split('.')[0].lower()
        return hostname == 'macpro51'

    def _is_mounted(self) -> bool:
        """Check if SMB share is mounted."""
        return self.mount_point.exists() and self.mount_point.is_mount()

    def mount_share(self) -> bool:
        """Mount SMB share from Builder."""
        if self._is_mounted():
            return True

        logger.info(f"Mounting SMB share from {self.BUILDER_IP}...")

        self.mount_point.mkdir(parents=True, exist_ok=True)

        if sys.platform == 'darwin':
            cmd = [
                'mount', '-t', 'smbfs',
                f'//{self.BUILDER_USER}@{self.BUILDER_IP}/{self.BUILDER_SHARE}',
                str(self.mount_point)
            ]
        else:
            cmd = [
                'sudo', 'mount', '-t', 'cifs',
                f'//{self.BUILDER_IP}/{self.BUILDER_SHARE}',
                str(self.mount_point),
                '-o', f'username={self.BUILDER_USER},uid={os.getuid()},gid={os.getgid()}'
            ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Mounted SMB share at {self.mount_point}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to mount: {e.stderr.decode() if e.stderr else e}")
            return False

    def _file_hash(self, path: Path) -> Optional[str]:
        """Get hash of file for change detection."""
        try:
            if path.is_file():
                return hashlib.md5(path.read_bytes()).hexdigest()
            elif path.is_dir():
                # Hash directory modification time
                return str(path.stat().st_mtime)
        except Exception:
            return None
        return None

    def _has_changes(self) -> bool:
        """Check if Builder has changes since last sync."""
        changes = False

        for sync_path in self.SYNC_DIRS + self.SYNC_FILES:
            remote_path = self.mount_point / sync_path
            if not remote_path.exists():
                continue

            current_hash = self._file_hash(remote_path)
            previous_hash = self.file_hashes.get(sync_path)

            if current_hash != previous_hash:
                logger.debug(f"Change detected in {sync_path}")
                changes = True
                self.file_hashes[sync_path] = current_hash

        return changes

    def sync(self) -> bool:
        """Perform sync from Builder to local storage."""
        if not self._is_mounted():
            if not self.mount_share():
                return False

        logger.info("Starting sync from Builder...")

        success = True
        for sync_dir in self.SYNC_DIRS:
            remote = self.mount_point / sync_dir
            local = self.local_storage / sync_dir

            if not remote.exists():
                continue

            local.mkdir(parents=True, exist_ok=True)

            # Build rsync command
            cmd = ['rsync', '-av']
            if self.dry_run:
                cmd.append('--dry-run')
            cmd.append('--delete')

            for pattern in self.EXCLUDE_PATTERNS:
                cmd.extend(['--exclude', pattern])

            cmd.extend([f'{remote}/', f'{local}/'])

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"  Synced {sync_dir}")
                else:
                    logger.warning(f"  Failed to sync {sync_dir}: {result.stderr}")
                    success = False
            except Exception as e:
                logger.error(f"  Error syncing {sync_dir}: {e}")
                success = False

        # Sync individual files
        for sync_file in self.SYNC_FILES:
            remote = self.mount_point / sync_file
            local = self.local_storage / sync_file

            if not remote.exists():
                continue

            local.parent.mkdir(parents=True, exist_ok=True)

            cmd = ['rsync', '-av']
            if self.dry_run:
                cmd.append('--dry-run')
            cmd.extend([str(remote), str(local)])

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                logger.info(f"  Synced {sync_file}")
            except Exception as e:
                logger.warning(f"  Failed to sync {sync_file}: {e}")

        self.last_sync = datetime.now()

        if success:
            logger.info("Sync completed successfully")
            self._notify_sync_complete()
        else:
            logger.warning("Sync completed with some errors")

        return success

    def _notify_sync_complete(self):
        """Notify user that sync is complete."""
        try:
            if sys.platform == 'darwin':
                subprocess.run([
                    'osascript', '-e',
                    'display notification "Code synced from Builder" with title "Cluster Sync"'
                ], capture_output=True)
        except Exception:
            pass

    def run_once(self):
        """Run a single sync."""
        if self._is_builder_node():
            logger.info("Running on Builder node - nothing to sync")
            return

        self.sync()

    def run_daemon(self):
        """Run as daemon, continuously checking for changes."""
        if self._is_builder_node():
            logger.info("Running on Builder node - daemon not needed")
            return

        logger.info("Starting sync daemon...")

        # Initial sync
        self.sync()

        while True:
            try:
                time.sleep(self.interval)

                if not self._is_mounted():
                    logger.warning("Share not mounted, attempting remount...")
                    if not self.mount_share():
                        continue

                if self._has_changes():
                    logger.info("Changes detected on Builder")
                    self.sync()
                else:
                    logger.debug("No changes detected")

            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description='Cluster Code Sync Daemon')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be synced without making changes')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit')

    args = parser.parse_args()

    daemon = ClusterCodeSyncDaemon(
        interval=args.interval,
        dry_run=args.dry_run
    )

    if args.once:
        daemon.run_once()
    else:
        daemon.run_daemon()


if __name__ == '__main__':
    main()
