#!/usr/bin/env python3
"""
Cluster Code Change Notifier - Broadcasts when code changes on Builder node.

This runs on macpro51 (Builder) and watches for file changes, then notifies
all cluster nodes that updates are available.

Usage:
    python3 cluster-code-change-notifier.py [--interval SECONDS]
"""
import platform

import os
import sys
import json
import time
import hashlib
import logging
import argparse
import subprocess
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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.expanduser('~/agentic-system/logs/code-notifier.log'))
    ]
)
logger = logging.getLogger(__name__)

# Paths to watch for changes
WATCH_PATHS = [
    '.claude/agents',
    '.claude/commands',
    '.claude/skills',
    '.claude/hooks',
    '.claude/helpers',
    'mcp-servers',
    'scripts',
    'cluster-deployment',
    'intelligent-agents',
]

# File extensions to track
TRACKED_EXTENSIONS = {'.py', '.sh', '.json', '.yaml', '.yml', '.md', '.toml'}

# Cluster nodes
CLUSTER_NODES = {
    'mac-studio': {'ip': '192.168.1.16', 'role': 'orchestrator'},
    'macbook-air': {'ip': '192.168.1.172', 'role': 'researcher'},
    'completeu-server': {'ip': '192.168.1.186', 'role': 'ai-inference'},
}

class CodeChangeNotifier:
    def __init__(self, base_path: str, check_interval: int = 60):
        self.base_path = Path(base_path)
        self.check_interval = check_interval
        self.file_hashes: Dict[str, str] = {}
        self.state_file = self.base_path / '.code-notifier-state.json'
        self.inbox_path = self.base_path / 'cluster-inbox'
        self.load_state()

    def load_state(self):
        """Load previous file hashes from state file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self.file_hashes = json.load(f)
                logger.info(f"Loaded state: tracking {len(self.file_hashes)} files")
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
                self.file_hashes = {}

    def save_state(self):
        """Save current file hashes to state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.file_hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state: {e}")

    def hash_file(self, filepath: Path) -> Optional[str]:
        """Calculate MD5 hash of a file."""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

    def scan_files(self) -> Dict[str, str]:
        """Scan all tracked paths and return file hashes."""
        current_hashes = {}

        for watch_path in WATCH_PATHS:
            full_path = self.base_path / watch_path
            if not full_path.exists():
                continue

            for filepath in full_path.rglob('*'):
                if filepath.is_file() and filepath.suffix in TRACKED_EXTENSIONS:
                    # Skip __pycache__ and .git
                    if '__pycache__' in str(filepath) or '.git' in str(filepath):
                        continue
                    rel_path = str(filepath.relative_to(self.base_path))
                    file_hash = self.hash_file(filepath)
                    if file_hash:
                        current_hashes[rel_path] = file_hash

        return current_hashes

    def detect_changes(self) -> Dict[str, Set[str]]:
        """Detect file changes since last scan."""
        current_hashes = self.scan_files()

        changes = {
            'added': set(),
            'modified': set(),
            'deleted': set(),
        }

        # Check for added and modified files
        for filepath, hash_val in current_hashes.items():
            if filepath not in self.file_hashes:
                changes['added'].add(filepath)
            elif self.file_hashes[filepath] != hash_val:
                changes['modified'].add(filepath)

        # Check for deleted files
        for filepath in self.file_hashes:
            if filepath not in current_hashes:
                changes['deleted'].add(filepath)

        # Update state
        self.file_hashes = current_hashes
        self.save_state()

        return changes

    def create_notification(self, changes: Dict[str, Set[str]]) -> Dict:
        """Create notification message for cluster nodes."""
        total_changes = sum(len(v) for v in changes.values())

        return {
            'type': 'code_update_available',
            'source_node': 'macpro51',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'added': len(changes['added']),
                'modified': len(changes['modified']),
                'deleted': len(changes['deleted']),
                'total': total_changes,
            },
            'files': {
                'added': list(changes['added'])[:20],  # Limit to 20 per category
                'modified': list(changes['modified'])[:20],
                'deleted': list(changes['deleted'])[:20],
            },
            'sync_command': 'cd /path/to/agentic-system && ./scripts/cluster-code-sync.sh',
            'smb_share': '//192.168.1.27/agentic-system',
        }

    def write_inbox_notification(self, notification: Dict):
        """Write notification to cluster inbox for each node."""
        for node_name in CLUSTER_NODES:
            node_inbox = self.inbox_path / node_name
            node_inbox.mkdir(parents=True, exist_ok=True)

            notif_file = node_inbox / f"code_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(notif_file, 'w') as f:
                json.dump(notification, f, indent=2)
            logger.info(f"Wrote notification to {notif_file}")

    def broadcast_via_universal_chat(self, notification: Dict):
        """Try to broadcast via universal-ai-chat MCP if available."""
        try:
            # Create a simple broadcast message
            message = f"""🔄 Code Update Available from Builder (macpro51)

Changes detected:
- Added: {notification['summary']['added']} files
- Modified: {notification['summary']['modified']} files
- Deleted: {notification['summary']['deleted']} files

To sync: Mount //192.168.1.27/agentic-system and run cluster-code-sync.sh

Modified paths:
{chr(10).join('  • ' + f for f in list(notification['files']['modified'])[:5])}
"""
            # Write to shared context file that other nodes can read
            shared_context_file = self.base_path / 'cluster-inbox' / 'LATEST_UPDATE.json'
            with open(shared_context_file, 'w') as f:
                json.dump(notification, f, indent=2)
            logger.info("Updated shared context file")

        except Exception as e:
            logger.warning(f"Could not broadcast: {e}")

    def notify_nodes(self, changes: Dict[str, Set[str]]):
        """Send notifications to all cluster nodes."""
        notification = self.create_notification(changes)

        # Write to inbox (file-based notification)
        self.write_inbox_notification(notification)

        # Try broadcast
        self.broadcast_via_universal_chat(notification)

        # Log summary
        logger.info(f"Notified cluster: {notification['summary']['total']} changes")

    def run(self):
        """Main run loop - watch for changes and notify."""
        logger.info(f"Starting Code Change Notifier")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Watching paths: {WATCH_PATHS}")

        # Initial scan
        initial_hashes = self.scan_files()
        if not self.file_hashes:
            self.file_hashes = initial_hashes
            self.save_state()
            logger.info(f"Initial scan: tracking {len(self.file_hashes)} files")

        while True:
            try:
                changes = self.detect_changes()
                total_changes = sum(len(v) for v in changes.values())

                if total_changes > 0:
                    logger.info(f"Detected {total_changes} changes")
                    for change_type, files in changes.items():
                        if files:
                            logger.info(f"  {change_type}: {len(files)} files")
                            for f in list(files)[:5]:
                                logger.info(f"    - {f}")

                    self.notify_nodes(changes)
                else:
                    logger.debug("No changes detected")

            except Exception as e:
                logger.error(f"Error in check loop: {e}")

            time.sleep(self.check_interval)


def main():
    parser = argparse.ArgumentParser(description='Watch for code changes and notify cluster')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')
    parser.add_argument('--base-path', type=str, default=str(_STORAGE_BASE),
                        help='Base path to watch')
    args = parser.parse_args()

    # Ensure log directory exists
    log_dir = Path(args.base_path) / 'logs'
    log_dir.mkdir(exist_ok=True)

    notifier = CodeChangeNotifier(args.base_path, args.interval)
    notifier.run()


if __name__ == '__main__':
    main()
# Test modification at Tue Dec  2 10:08:50 AM EST 2025
