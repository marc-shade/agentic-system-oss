#!/usr/bin/env python3
"""
Visual Sync Daemon - Automated bridge from visual captures to enhanced memory

Watches the visual daemon's capture directory and syncs new images
to the enhanced memory system using the VisualMemory class directly.

Features:
- Filesystem watching with inotify (Linux) or polling fallback
- Parses filename metadata (activity, timestamp, status)
- Significance scoring based on activity level
- Deduplication via image hash
- Batch processing for efficiency
- Graceful shutdown handling

Usage:
    python3 visual_sync_daemon.py [--once] [--verbose]

Options:
    --once      Process existing files once and exit (no watching)
    --verbose   Enable debug logging
"""
import platform

import os
import sys
import time
import signal
import logging
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
import json

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Storage path detection
STORAGE_BASE = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))

# Import visual memory directly (bypasses MCP)
from visual_memory import VisualMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('visual_sync_daemon')

# Configuration
SCREENSHOTS_DIR = STORAGE_BASE / "databases" / "sensory" / "screenshots"
SYNC_STATE_FILE = STORAGE_BASE / "databases" / "sensory" / ".visual_sync_state.json"
POLL_INTERVAL = 30  # seconds between directory scans
BATCH_SIZE = 10     # max files to process per batch

# Activity significance mapping
ACTIVITY_SIGNIFICANCE = {
    "person_very_active": 0.9,
    "person_active": 0.8,
    "User active (high motion)": 0.85,
    "User active (medium motion)": 0.75,
    "User active (low motion)": 0.65,
    "person_present_still": 0.6,
    "movement_no_person": 0.4,
    "Empty and still": 0.2,
    "empty_still": 0.2,
}


class VisualSyncDaemon:
    """Daemon that syncs visual captures to enhanced memory"""

    def __init__(self, node_id: str = None, verbose: bool = False):
        self.node_id = node_id or self._detect_node_id()
        self.verbose = verbose
        self.running = True
        self.visual_memory = None
        self.processed_hashes: Set[str] = set()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if verbose:
            logger.setLevel(logging.DEBUG)

        logger.info(f"Visual Sync Daemon initializing for node: {self.node_id}")

    def _detect_node_id(self) -> str:
        """Detect current node ID"""
        import socket

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

        hostname = socket.gethostname().lower()

        # Map hostnames to node IDs
        node_map = {
            "macpro51": "macpro51",
            "mac-studio": "mac-studio",
            "macbook-air": "macbook-air",
            "completeu-server": "completeu-server",
        }

        for key, node_id in node_map.items():
            if key in hostname:
                return node_id

        return hostname.split('.')[0]

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _load_sync_state(self) -> Dict[str, Any]:
        """Load sync state from file"""
        if SYNC_STATE_FILE.exists():
            try:
                with open(SYNC_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.processed_hashes = set(state.get('processed_hashes', []))
                    return state
            except Exception as e:
                logger.warning(f"Could not load sync state: {e}")
        return {'processed_hashes': [], 'last_sync': None}

    def _save_sync_state(self):
        """Save sync state to file"""
        try:
            SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'processed_hashes': list(self.processed_hashes)[-1000:],  # Keep last 1000
                'last_sync': datetime.now().isoformat(),
                'node_id': self.node_id
            }
            with open(SYNC_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save sync state: {e}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # Short hash

    def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """
        Parse capture filename for metadata

        Format: capture_macpro51_YYYYMMDD_HHMMSS_activity_status.jpg
        Example: capture_macpro51_20251201_110956_movement_no_person.jpg
        """
        metadata = {
            'timestamp': None,
            'activity': 'unknown',
            'person_present': False,
            'significance': 0.5
        }

        try:
            # Remove extension and split
            name = filename.replace('.jpg', '').replace('.png', '')
            parts = name.split('_')

            # Extract timestamp (YYYYMMDD_HHMMSS)
            if len(parts) >= 4:
                date_str = parts[2]  # YYYYMMDD
                time_str = parts[3]  # HHMMSS

                try:
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    metadata['timestamp'] = dt.isoformat()
                except ValueError:
                    pass

            # Extract activity (everything after timestamp)
            if len(parts) >= 5:
                activity_parts = parts[4:]
                activity = '_'.join(activity_parts)
                metadata['activity'] = activity

                # Determine person presence
                activity_lower = activity.lower()
                metadata['person_present'] = (
                    'person' in activity_lower or
                    'user' in activity_lower or
                    'active' in activity_lower
                )

                # Map to significance
                for key, sig in ACTIVITY_SIGNIFICANCE.items():
                    if key.lower() in activity_lower or activity_lower in key.lower():
                        metadata['significance'] = sig
                        break

        except Exception as e:
            logger.debug(f"Could not parse filename {filename}: {e}")

        return metadata

    def _get_pending_files(self) -> List[Path]:
        """Get list of capture files that haven't been synced"""
        pending = []

        # Check node-specific directory
        node_dir = SCREENSHOTS_DIR / self.node_id
        if not node_dir.exists():
            logger.warning(f"Screenshots directory not found: {node_dir}")
            return pending

        # Scan for image files
        for ext in ['*.jpg', '*.png', '*.jpeg']:
            for file_path in node_dir.glob(ext):
                try:
                    file_hash = self._compute_file_hash(file_path)
                    if file_hash not in self.processed_hashes:
                        pending.append(file_path)
                except Exception as e:
                    logger.debug(f"Error checking file {file_path}: {e}")

        # Sort by modification time (oldest first)
        pending.sort(key=lambda p: p.stat().st_mtime)

        return pending

    def _sync_file(self, file_path: Path) -> bool:
        """Sync a single capture file to enhanced memory"""
        try:
            # Check if file still exists (may be deleted by visual daemon)
            if not file_path.exists():
                logger.debug(f"File no longer exists (deleted by daemon): {file_path.name}")
                return False

            # Parse filename for metadata
            metadata = self._parse_filename(file_path.name)

            # Build context string
            context = f"[{self.node_id}] {metadata['activity']}"
            if metadata['timestamp']:
                context = f"{context} at {metadata['timestamp']}"

            # Store in visual memory
            episode_id = self.visual_memory.store_visual_episode(
                image_path=str(file_path),
                context=context,
                significance=metadata['significance'],
                metadata={
                    'node_id': self.node_id,
                    'activity': metadata['activity'],
                    'person_present': metadata['person_present'],
                    'source': 'visual_sync_daemon',
                    'original_filename': file_path.name
                }
            )

            if episode_id:
                # Track as processed
                file_hash = self._compute_file_hash(file_path)
                self.processed_hashes.add(file_hash)

                logger.info(
                    f"Synced: {file_path.name} -> episode {episode_id} "
                    f"(sig={metadata['significance']:.2f}, person={metadata['person_present']})"
                )
                return True
            else:
                logger.warning(f"Failed to store episode for {file_path.name}")
                return False

        except FileNotFoundError:
            # Expected - visual daemon may delete file between our checks
            logger.debug(f"File deleted during sync (expected race condition): {file_path.name}")
            return False
        except Exception as e:
            logger.error(f"Error syncing {file_path}: {e}")
            return False

    def sync_batch(self, max_files: int = BATCH_SIZE) -> Dict[str, int]:
        """Process a batch of pending files"""
        stats = {'processed': 0, 'failed': 0, 'skipped': 0}

        pending = self._get_pending_files()
        batch = pending[:max_files]

        if not batch:
            logger.debug("No pending files to sync")
            return stats

        logger.info(f"Processing batch of {len(batch)} files ({len(pending)} total pending)")

        for file_path in batch:
            try:
                if self._sync_file(file_path):
                    stats['processed'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"Batch error for {file_path}: {e}")
                stats['failed'] += 1

        # Save state after batch
        self._save_sync_state()

        return stats

    def run_once(self) -> Dict[str, int]:
        """Process all pending files once and return"""
        logger.info("Running one-time sync...")

        # Initialize visual memory
        self.visual_memory = VisualMemory()
        self._load_sync_state()

        total_stats = {'processed': 0, 'failed': 0, 'skipped': 0}

        while True:
            stats = self.sync_batch(max_files=BATCH_SIZE)
            total_stats['processed'] += stats['processed']
            total_stats['failed'] += stats['failed']

            # Continue until no more pending
            if stats['processed'] == 0 and stats['failed'] == 0:
                break

        logger.info(
            f"One-time sync complete: {total_stats['processed']} processed, "
            f"{total_stats['failed']} failed"
        )

        return total_stats

    def run(self):
        """Main daemon loop"""
        logger.info(f"Starting Visual Sync Daemon for {self.node_id}")
        logger.info(f"Watching: {SCREENSHOTS_DIR / self.node_id}")
        logger.info(f"Poll interval: {POLL_INTERVAL}s")

        # Initialize visual memory
        self.visual_memory = VisualMemory()
        self._load_sync_state()

        logger.info(f"Loaded {len(self.processed_hashes)} previously processed hashes")

        # Initial sync
        stats = self.sync_batch(max_files=BATCH_SIZE * 2)
        logger.info(f"Initial sync: {stats['processed']} processed")

        # Main loop
        while self.running:
            try:
                time.sleep(POLL_INTERVAL)

                if not self.running:
                    break

                stats = self.sync_batch()

                if stats['processed'] > 0:
                    logger.info(
                        f"Sync cycle: {stats['processed']} processed, "
                        f"{stats['failed']} failed"
                    )

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(5)  # Brief pause on error

        # Final save
        self._save_sync_state()
        logger.info("Visual Sync Daemon stopped")


def main():
    parser = argparse.ArgumentParser(description='Visual Sync Daemon')
    parser.add_argument('--once', action='store_true',
                        help='Process existing files once and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--node', type=str, default=None,
                        help='Override node ID detection')
    args = parser.parse_args()

    daemon = VisualSyncDaemon(node_id=args.node, verbose=args.verbose)

    if args.once:
        stats = daemon.run_once()
        sys.exit(0 if stats['failed'] == 0 else 1)
    else:
        daemon.run()


if __name__ == "__main__":
    main()
