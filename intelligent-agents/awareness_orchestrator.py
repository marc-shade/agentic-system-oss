#!/usr/bin/env python3
"""
Awareness Orchestrator
======================
Master controller for AGI environmental and situational awareness.

Coordinates:
- Environmental Awareness Daemon (screenshots, webcam)
- Visual Memory Agent (image → memory)
- Audio Awareness Agent (listen → transcribe)
- Drive Health Monitor (prevent disk fill)

Ensures the system maintains continuous awareness while protecting
storage resources through intelligent rolling buffers.
"""

import asyncio
import json
import sqlite3
import subprocess
import socket
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import signal
import sys

# Configuration
STORAGE_BASE = Path("/Volumes/SSDRAID0/agentic-system")
SENSORY_DIR = STORAGE_BASE / "databases" / "sensory"
DB_PATH = SENSORY_DIR / f"awareness_orchestrator_{socket.gethostname().lower().replace(' ', '-')}.db"

# Storage limits
SSDRAID0_WARNING_PERCENT = 80  # Warn at 80% usage
SSDRAID0_CRITICAL_PERCENT = 90  # Critical at 90%
FILES_WARNING_PERCENT = 70
FILES_CRITICAL_PERCENT = 85

# Cleanup thresholds
MAX_SENSORY_GB = 2.0  # Maximum total sensory data
MAX_LOG_AGE_DAYS = 7

# Health check interval
HEALTH_CHECK_INTERVAL_SECONDS = 60


class DriveHealthMonitor:
    """Monitors drive health and triggers cleanup when needed."""

    def __init__(self):
        self.drives = {
            'SSDRAID0': {
                'path': '/Volumes/SSDRAID0',
                'warning_percent': SSDRAID0_WARNING_PERCENT,
                'critical_percent': SSDRAID0_CRITICAL_PERCENT,
                'type': 'hot'
            },
            'FILES': {
                'path': '/Volumes/FILES',
                'warning_percent': FILES_WARNING_PERCENT,
                'critical_percent': FILES_CRITICAL_PERCENT,
                'type': 'cold'
            }
        }

    def get_drive_usage(self, path: str) -> Dict:
        """Get disk usage for a path."""
        try:
            usage = shutil.disk_usage(path)
            percent = (usage.used / usage.total) * 100
            return {
                'total_gb': usage.total / (1024**3),
                'used_gb': usage.used / (1024**3),
                'free_gb': usage.free / (1024**3),
                'percent_used': percent
            }
        except Exception as e:
            return {'error': str(e)}

    def check_all_drives(self) -> Dict[str, Dict]:
        """Check all configured drives."""
        results = {}
        for name, config in self.drives.items():
            usage = self.get_drive_usage(config['path'])
            if 'error' not in usage:
                usage['status'] = self._get_status(usage['percent_used'], config)
                usage['type'] = config['type']
            results[name] = usage
        return results

    def _get_status(self, percent: float, config: Dict) -> str:
        """Determine drive status based on usage."""
        if percent >= config['critical_percent']:
            return 'critical'
        elif percent >= config['warning_percent']:
            return 'warning'
        return 'healthy'

    def needs_cleanup(self) -> bool:
        """Check if any drive needs cleanup."""
        for name, usage in self.check_all_drives().items():
            if usage.get('status') in ('warning', 'critical'):
                return True
        return False


class AwarenessOrchestrator:
    """Master orchestrator for all awareness systems."""

    def __init__(self):
        self.node_id = socket.gethostname().lower().replace(" ", "-")
        self.running = False
        self.drive_monitor = DriveHealthMonitor()
        self.processes: Dict[str, subprocess.Popen] = {}
        self._ensure_db()

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def _ensure_db(self):
        """Ensure database has required tables."""
        SENSORY_DIR.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orchestrator_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    component TEXT,
                    description TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    drives_json TEXT,
                    sensory_size_mb REAL,
                    components_status TEXT
                )
            """)
            conn.commit()

    def _log(self, event_type: str, component: str, description: str, metadata: Dict = None):
        """Log orchestrator event."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO orchestrator_log (event_type, component, description, metadata)
                VALUES (?, ?, ?, ?)
            """, (event_type, component, description, json.dumps(metadata) if metadata else None))
            conn.commit()

    def get_sensory_size_mb(self) -> float:
        """Get total size of sensory data directory."""
        total = 0
        for f in SENSORY_DIR.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)

    async def cleanup_old_data(self):
        """Clean up old sensory data and logs."""
        cleaned_mb = 0
        cleaned_files = 0

        # Clean old captures from database records
        # Use strftime to match DB format (space separator, not ISO T separator)
        cutoff = datetime.now() - timedelta(hours=1)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

        sensory_db = SENSORY_DIR / f"sensory_memory_{self.node_id}.db"
        if sensory_db.exists():
            with sqlite3.connect(sensory_db) as conn:
                # Get old captures
                rows = conn.execute("""
                    SELECT filepath FROM captures
                    WHERE timestamp < ? AND deleted = FALSE
                """, (cutoff_str,)).fetchall()

                for (filepath,) in rows:
                    path = Path(filepath)
                    if path.exists():
                        size = path.stat().st_size
                        path.unlink()
                        cleaned_mb += size / (1024 * 1024)
                        cleaned_files += 1

                conn.execute("""
                    UPDATE captures SET deleted = TRUE
                    WHERE timestamp < ?
                """, (cutoff_str,))
                conn.commit()

        # Clean orphaned files
        for subdir in ['screenshots', 'webcam', 'audio']:
            dir_path = SENSORY_DIR / subdir / self.node_id
            if dir_path.exists():
                for f in dir_path.glob("*"):
                    if f.is_file():
                        age = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
                        if age > timedelta(hours=1):
                            size = f.stat().st_size
                            f.unlink()
                            cleaned_mb += size / (1024 * 1024)
                            cleaned_files += 1

        if cleaned_files > 0:
            self._log('cleanup', 'orchestrator',
                     f'Cleaned {cleaned_files} files, freed {cleaned_mb:.2f}MB')

        return cleaned_mb

    async def emergency_cleanup(self):
        """Emergency cleanup when drives are critical."""
        print("EMERGENCY CLEANUP: Drive space critical!")
        self._log('emergency', 'orchestrator', 'Emergency cleanup triggered')

        # Stop capture daemons temporarily
        await self.stop_component('environmental_awareness_daemon')

        # Aggressive cleanup - delete ALL sensory captures
        for subdir in ['screenshots', 'webcam', 'audio']:
            dir_path = SENSORY_DIR / subdir
            if dir_path.exists():
                for f in dir_path.rglob("*"):
                    if f.is_file():
                        f.unlink()

        # Clear capture records
        sensory_db = SENSORY_DIR / f"sensory_memory_{self.node_id}.db"
        if sensory_db.exists():
            with sqlite3.connect(sensory_db) as conn:
                conn.execute("UPDATE captures SET deleted = TRUE")
                conn.commit()

        self._log('emergency', 'orchestrator', 'Emergency cleanup completed')

        # Restart capture after cleanup
        await self.start_component('environmental_awareness_daemon')

    async def start_component(self, component: str):
        """Start a component process."""
        scripts = {
            'environmental_awareness_daemon': STORAGE_BASE / 'intelligent-agents' / 'environmental_awareness_daemon.py',
            'visual_memory_agent': STORAGE_BASE / 'intelligent-agents' / 'visual_memory_agent.py',
            'audio_awareness_agent': STORAGE_BASE / 'intelligent-agents' / 'audio_awareness_agent.py'
        }

        if component not in scripts:
            return False

        script_path = scripts[component]
        if not script_path.exists():
            self._log('error', component, f'Script not found: {script_path}')
            return False

        try:
            process = subprocess.Popen(
                ['python3', str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            self.processes[component] = process
            self._log('start', component, f'Started with PID {process.pid}')
            return True
        except Exception as e:
            self._log('error', component, f'Failed to start: {e}')
            return False

    async def stop_component(self, component: str):
        """Stop a component process."""
        if component in self.processes:
            process = self.processes[component]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.processes[component]
            self._log('stop', component, 'Stopped')
            return True
        return False

    def get_component_status(self, component: str) -> str:
        """Get status of a component."""
        if component in self.processes:
            process = self.processes[component]
            if process.poll() is None:
                return 'running'
            else:
                return 'stopped'
        return 'not_started'

    async def health_check(self) -> Dict:
        """Perform comprehensive health check."""
        # Check drives
        drives = self.drive_monitor.check_all_drives()

        # Check sensory size
        sensory_mb = self.get_sensory_size_mb()

        # Check components
        components = {}
        for comp in ['environmental_awareness_daemon', 'visual_memory_agent', 'audio_awareness_agent']:
            components[comp] = self.get_component_status(comp)

        # Overall health
        health = 'healthy'
        issues = []

        for drive_name, drive_status in drives.items():
            if drive_status.get('status') == 'critical':
                health = 'critical'
                issues.append(f'{drive_name} at {drive_status["percent_used"]:.1f}%')
            elif drive_status.get('status') == 'warning' and health != 'critical':
                health = 'warning'
                issues.append(f'{drive_name} at {drive_status["percent_used"]:.1f}%')

        if sensory_mb > MAX_SENSORY_GB * 1024:
            if health != 'critical':
                health = 'warning'
            issues.append(f'Sensory data at {sensory_mb:.1f}MB')

        result = {
            'timestamp': datetime.now().isoformat(),
            'node_id': self.node_id,
            'health': health,
            'issues': issues,
            'drives': drives,
            'sensory_mb': round(sensory_mb, 2),
            'max_sensory_mb': MAX_SENSORY_GB * 1024,
            'components': components
        }

        # Store snapshot
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO health_snapshots (drives_json, sensory_size_mb, components_status)
                VALUES (?, ?, ?)
            """, (json.dumps(drives), sensory_mb, json.dumps(components)))
            conn.commit()

        return result

    async def run(self):
        """Main orchestrator loop."""
        self.running = True
        self._log('startup', 'orchestrator', f'Awareness Orchestrator started on {self.node_id}')

        print(f"=== Awareness Orchestrator ===")
        print(f"Node: {self.node_id}")
        print(f"Sensory storage: {SENSORY_DIR}")
        print(f"Max sensory data: {MAX_SENSORY_GB}GB")
        print()

        # Start all components
        print("Starting awareness components...")
        await self.start_component('environmental_awareness_daemon')
        await asyncio.sleep(2)
        await self.start_component('visual_memory_agent')
        await asyncio.sleep(2)
        # Audio agent optional - may need sox installed
        # await self.start_component('audio_awareness_agent')

        print("\nOrchestrator running. Press Ctrl+C to stop.")
        print()

        try:
            while self.running:
                # Perform health check
                health = await self.health_check()

                # Print status
                status_line = f"[{datetime.now().strftime('%H:%M:%S')}] "
                status_line += f"Health: {health['health'].upper()} | "
                status_line += f"Sensory: {health['sensory_mb']:.1f}MB | "
                status_line += f"SSDRAID0: {health['drives'].get('SSDRAID0', {}).get('percent_used', 0):.1f}%"
                print(status_line)

                # Handle issues
                if health['health'] == 'critical':
                    await self.emergency_cleanup()
                elif health['health'] == 'warning':
                    await self.cleanup_old_data()

                # Regular cleanup
                await self.cleanup_old_data()

                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)

        except Exception as e:
            self._log('error', 'orchestrator', f'Error in main loop: {e}')
            raise
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown."""
        print("\nShutting down awareness systems...")

        for component in list(self.processes.keys()):
            await self.stop_component(component)

        self._log('shutdown', 'orchestrator', 'Awareness Orchestrator stopped')
        self.running = False

    def stop(self):
        """Stop the orchestrator."""
        self.running = False


def get_status() -> Dict:
    """Get orchestrator status without running."""
    orchestrator = AwarenessOrchestrator()
    return asyncio.run(orchestrator.health_check())


async def main():
    """Main entry point."""
    orchestrator = AwarenessOrchestrator()

    # Initial health check
    print("Initial health check...")
    health = await orchestrator.health_check()
    print(json.dumps(health, indent=2))
    print()

    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
