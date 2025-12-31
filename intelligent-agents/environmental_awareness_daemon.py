#!/usr/bin/env python3
"""
Environmental Awareness Daemon
==============================
Persistent sensory system for AGI environmental and situational awareness.

Capabilities:
- Screenshot capture (rolling buffer)
- Webcam capture (rolling buffer)
- Audio listening (via voice-mode)
- Vision analysis (extract insights from captures)
- Automatic cleanup (prevent drive fill)

Storage Policy:
- Max 500MB screenshots
- Max 500MB webcam
- Max 1 hour retention for raw captures
- Insights persist forever in enhanced-memory
"""

import asyncio
import subprocess
import sqlite3
import json
import hashlib
import os
import time
import socket
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import threading
import base64

# Configuration
STORAGE_BASE = Path("/Volumes/SSDRAID0/agentic-system")
SENSORY_DIR = STORAGE_BASE / "databases" / "sensory"
SCREENSHOTS_DIR = SENSORY_DIR / "screenshots" / socket.gethostname().lower().replace(" ", "-")
WEBCAM_DIR = SENSORY_DIR / "webcam" / socket.gethostname().lower().replace(" ", "-")
DB_PATH = SENSORY_DIR / f"sensory_memory_{socket.gethostname().lower().replace(' ', '-')}.db"

# Rolling buffer limits
MAX_SCREENSHOT_MB = 500
MAX_WEBCAM_MB = 500
MAX_RETENTION_MINUTES = 60
SCREENSHOT_INTERVAL_SECONDS = 30
WEBCAM_INTERVAL_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

# Quality settings (balance between detail and storage)
SCREENSHOT_QUALITY = 50  # JPEG quality 0-100
WEBCAM_QUALITY = 50
SCREENSHOT_SCALE = 50  # Percentage of original size


@dataclass
class CaptureRecord:
    id: int
    capture_type: str  # screenshot, webcam, audio
    filepath: str
    timestamp: datetime
    size_bytes: int
    processed: bool
    insights: Optional[str]
    hash: str


class SensoryDatabase:
    """SQLite database for tracking captures and insights."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS captures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capture_type TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    size_bytes INTEGER,
                    processed BOOLEAN DEFAULT FALSE,
                    insights TEXT,
                    hash TEXT,
                    deleted BOOLEAN DEFAULT FALSE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS awareness_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    description TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    screenshots_mb REAL,
                    webcam_mb REAL,
                    total_captures INTEGER,
                    processed_captures INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_captures_type ON captures(capture_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_captures_processed ON captures(processed)")
            conn.commit()

    def record_capture(self, capture_type: str, filepath: str, size_bytes: int, file_hash: str) -> int:
        """Record a new capture."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO captures (capture_type, filepath, size_bytes, hash)
                VALUES (?, ?, ?, ?)
            """, (capture_type, filepath, size_bytes, file_hash))
            return cursor.lastrowid

    def mark_processed(self, capture_id: int, insights: str):
        """Mark capture as processed with extracted insights."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE captures SET processed = TRUE, insights = ?
                WHERE id = ?
            """, (insights, capture_id))
            conn.commit()

    def get_unprocessed(self, limit: int = 10) -> List[Dict]:
        """Get unprocessed captures."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM captures
                WHERE processed = FALSE AND deleted = FALSE
                ORDER BY timestamp ASC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_old_captures(self, max_age_minutes: int) -> List[Dict]:
        """Get captures older than max_age_minutes."""
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM captures
                WHERE timestamp < ? AND deleted = FALSE
            """, (cutoff.isoformat(),)).fetchall()
            return [dict(row) for row in rows]

    def mark_deleted(self, capture_id: int):
        """Mark capture as deleted."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE captures SET deleted = TRUE WHERE id = ?", (capture_id,))
            conn.commit()

    def get_storage_usage(self) -> Dict[str, float]:
        """Get current storage usage by type in MB."""
        with sqlite3.connect(self.db_path) as conn:
            result = {}
            for capture_type in ['screenshot', 'webcam']:
                row = conn.execute("""
                    SELECT COALESCE(SUM(size_bytes), 0) / 1048576.0 as mb
                    FROM captures
                    WHERE capture_type = ? AND deleted = FALSE
                """, (capture_type,)).fetchone()
                result[capture_type] = row[0] if row else 0
            return result

    def log_event(self, event_type: str, description: str, metadata: Dict = None):
        """Log an awareness event."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO awareness_log (event_type, description, metadata)
                VALUES (?, ?, ?)
            """, (event_type, description, json.dumps(metadata) if metadata else None))
            conn.commit()

    def record_storage_stats(self, screenshots_mb: float, webcam_mb: float,
                            total_captures: int, processed_captures: int):
        """Record storage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO storage_stats (screenshots_mb, webcam_mb, total_captures, processed_captures)
                VALUES (?, ?, ?, ?)
            """, (screenshots_mb, webcam_mb, total_captures, processed_captures))
            conn.commit()


class EnvironmentalAwarenessDaemon:
    """Main daemon for environmental awareness."""

    def __init__(self):
        # Ensure directories exist
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        WEBCAM_DIR.mkdir(parents=True, exist_ok=True)

        self.db = SensoryDatabase(DB_PATH)
        self.running = False
        self.node_id = socket.gethostname().lower().replace(" ", "-")

        # Check for required tools
        self._check_tools()

    def _check_tools(self):
        """Verify required capture tools are available."""
        tools = {
            'screencapture': 'Screenshot capture',
            'imagesnap': 'Webcam capture (install with: brew install imagesnap)',
            'sips': 'Image processing'
        }

        missing = []
        for tool, description in tools.items():
            result = subprocess.run(['which', tool], capture_output=True)
            if result.returncode != 0:
                missing.append(f"{tool}: {description}")

        if missing:
            print(f"Warning: Missing tools:\n" + "\n".join(missing))

    def _file_hash(self, filepath: Path) -> str:
        """Calculate file hash for deduplication."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:16]

    async def capture_screenshot(self) -> Optional[Path]:
        """Capture a screenshot with compression."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = SCREENSHOTS_DIR / f"temp_{timestamp}.png"
        final_path = SCREENSHOTS_DIR / f"screen_{timestamp}.jpg"

        try:
            # Capture screenshot
            subprocess.run([
                'screencapture', '-x', '-C', str(temp_path)
            ], check=True, capture_output=True)

            # Compress and resize with sips
            subprocess.run([
                'sips', '-s', 'format', 'jpeg',
                '-s', 'formatOptions', str(SCREENSHOT_QUALITY),
                '-Z', str(int(1920 * SCREENSHOT_SCALE / 100)),  # Max width
                str(temp_path), '--out', str(final_path)
            ], check=True, capture_output=True)

            # Remove temp file
            temp_path.unlink(missing_ok=True)

            # Record in database
            size = final_path.stat().st_size
            file_hash = self._file_hash(final_path)
            self.db.record_capture('screenshot', str(final_path), size, file_hash)
            self.db.log_event('capture', f'Screenshot captured: {final_path.name}',
                            {'size_kb': size // 1024})

            return final_path

        except Exception as e:
            temp_path.unlink(missing_ok=True)
            self.db.log_event('error', f'Screenshot capture failed: {e}')
            return None

    async def capture_webcam(self) -> Optional[Path]:
        """Capture a webcam image with compression."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = WEBCAM_DIR / f"temp_{timestamp}.jpg"
        final_path = WEBCAM_DIR / f"webcam_{timestamp}.jpg"

        try:
            # Capture webcam image
            subprocess.run([
                'imagesnap', '-q', '-w', '1.0', str(temp_path)
            ], check=True, capture_output=True, timeout=10)

            # Compress with sips
            subprocess.run([
                'sips', '-s', 'format', 'jpeg',
                '-s', 'formatOptions', str(WEBCAM_QUALITY),
                '-Z', '640',  # Max width for webcam
                str(temp_path), '--out', str(final_path)
            ], check=True, capture_output=True)

            # Remove temp file
            temp_path.unlink(missing_ok=True)

            # Record in database
            size = final_path.stat().st_size
            file_hash = self._file_hash(final_path)
            self.db.record_capture('webcam', str(final_path), size, file_hash)
            self.db.log_event('capture', f'Webcam captured: {final_path.name}',
                            {'size_kb': size // 1024})

            return final_path

        except subprocess.TimeoutExpired:
            self.db.log_event('error', 'Webcam capture timeout - camera may be in use')
            return None
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            self.db.log_event('error', f'Webcam capture failed: {e}')
            return None

    async def cleanup_old_captures(self):
        """Delete captures older than retention period and enforce storage limits."""
        # Delete old captures
        old_captures = self.db.get_old_captures(MAX_RETENTION_MINUTES)
        deleted_count = 0
        freed_bytes = 0

        for capture in old_captures:
            filepath = Path(capture['filepath'])
            if filepath.exists():
                freed_bytes += filepath.stat().st_size
                filepath.unlink()
                deleted_count += 1
            self.db.mark_deleted(capture['id'])

        if deleted_count > 0:
            self.db.log_event('cleanup', f'Deleted {deleted_count} old captures',
                            {'freed_mb': freed_bytes / 1048576})

        # Enforce storage limits
        usage = self.db.get_storage_usage()

        if usage['screenshot'] > MAX_SCREENSHOT_MB:
            await self._trim_captures('screenshot', MAX_SCREENSHOT_MB)

        if usage['webcam'] > MAX_WEBCAM_MB:
            await self._trim_captures('webcam', MAX_WEBCAM_MB)

    async def _trim_captures(self, capture_type: str, max_mb: float):
        """Trim oldest captures to fit within storage limit."""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get captures ordered by age (oldest first)
            captures = conn.execute("""
                SELECT * FROM captures
                WHERE capture_type = ? AND deleted = FALSE
                ORDER BY timestamp ASC
            """, (capture_type,)).fetchall()

            current_mb = sum(c['size_bytes'] for c in captures) / 1048576.0
            deleted = 0

            for capture in captures:
                if current_mb <= max_mb * 0.8:  # Trim to 80% to avoid constant cleanup
                    break

                filepath = Path(capture['filepath'])
                if filepath.exists():
                    current_mb -= capture['size_bytes'] / 1048576.0
                    filepath.unlink()
                    deleted += 1

                conn.execute("UPDATE captures SET deleted = TRUE WHERE id = ?",
                           (capture['id'],))

            conn.commit()

            if deleted > 0:
                self.db.log_event('storage_trim',
                                f'Trimmed {deleted} {capture_type} captures to stay under {max_mb}MB')

    async def process_captures(self):
        """Process unprocessed captures and extract insights."""
        unprocessed = self.db.get_unprocessed(limit=5)

        for capture in unprocessed:
            filepath = Path(capture['filepath'])
            if not filepath.exists():
                self.db.mark_deleted(capture['id'])
                continue

            # For now, just mark as processed with basic metadata
            # In production, this would call vision AI to extract insights
            insights = {
                'processed_at': datetime.now().isoformat(),
                'type': capture['capture_type'],
                'size_kb': capture['size_bytes'] // 1024,
                'filename': filepath.name
            }

            self.db.mark_processed(capture['id'], json.dumps(insights))

    def get_status(self) -> Dict:
        """Get current daemon status."""
        usage = self.db.get_storage_usage()

        with sqlite3.connect(self.db.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM captures WHERE deleted = FALSE").fetchone()[0]
            processed = conn.execute("SELECT COUNT(*) FROM captures WHERE processed = TRUE AND deleted = FALSE").fetchone()[0]

        return {
            'node_id': self.node_id,
            'running': self.running,
            'storage': {
                'screenshots_mb': round(usage['screenshot'], 2),
                'webcam_mb': round(usage['webcam'], 2),
                'total_mb': round(usage['screenshot'] + usage['webcam'], 2),
                'limit_mb': MAX_SCREENSHOT_MB + MAX_WEBCAM_MB
            },
            'captures': {
                'total': total,
                'processed': processed,
                'pending': total - processed
            },
            'settings': {
                'screenshot_interval_sec': SCREENSHOT_INTERVAL_SECONDS,
                'webcam_interval_sec': WEBCAM_INTERVAL_SECONDS,
                'retention_minutes': MAX_RETENTION_MINUTES
            }
        }

    async def run(self):
        """Main daemon loop."""
        self.running = True
        self.db.log_event('startup', f'Environmental Awareness Daemon started on {self.node_id}')

        print(f"Environmental Awareness Daemon starting on {self.node_id}")
        print(f"Screenshots: every {SCREENSHOT_INTERVAL_SECONDS}s, max {MAX_SCREENSHOT_MB}MB")
        print(f"Webcam: every {WEBCAM_INTERVAL_SECONDS}s, max {MAX_WEBCAM_MB}MB")
        print(f"Retention: {MAX_RETENTION_MINUTES} minutes")
        print(f"Storage: {SENSORY_DIR}")

        last_screenshot = 0
        last_webcam = 0
        last_cleanup = 0

        try:
            while self.running:
                now = time.time()

                # Screenshot capture
                if now - last_screenshot >= SCREENSHOT_INTERVAL_SECONDS:
                    asyncio.create_task(self.capture_screenshot())
                    last_screenshot = now

                # Webcam capture
                if now - last_webcam >= WEBCAM_INTERVAL_SECONDS:
                    asyncio.create_task(self.capture_webcam())
                    last_webcam = now

                # Cleanup old captures
                if now - last_cleanup >= CLEANUP_INTERVAL_SECONDS:
                    await self.cleanup_old_captures()
                    await self.process_captures()

                    # Record stats
                    usage = self.db.get_storage_usage()
                    status = self.get_status()
                    self.db.record_storage_stats(
                        usage['screenshot'], usage['webcam'],
                        status['captures']['total'], status['captures']['processed']
                    )
                    last_cleanup = now

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            self.db.log_event('shutdown', 'Environmental Awareness Daemon stopped')

    def stop(self):
        """Stop the daemon."""
        self.running = False


async def main():
    """Main entry point."""
    daemon = EnvironmentalAwarenessDaemon()

    # Print initial status
    status = daemon.get_status()
    print(f"\nInitial Status: {json.dumps(status, indent=2)}")

    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
