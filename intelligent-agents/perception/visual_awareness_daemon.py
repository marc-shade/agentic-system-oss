#!/usr/bin/env python3
"""
Visual Awareness Daemon - Continuous Environmental Intelligence

This daemon provides continuous visual awareness across the cluster by:
1. Monitoring webcam captures from all nodes
2. Analyzing new frames with available vision models
3. Storing insights in cluster memory
4. Providing real-time awareness queries

The daemon is designed to run as a systemd service and integrate
with the cluster's memory and awareness systems.
"""
import platform

import json
import sqlite3
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visual_awareness_daemon")

# Configuration
STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
SCREENSHOTS_DIR = STORAGE_BASE / "databases" / "sensory" / "screenshots"
ANALYSIS_INTERVAL = 30  # Analyze every 30 seconds
MAX_QUEUE_SIZE = 100


class ImageEventHandler(FileSystemEventHandler):
    """Watch for new image captures"""

    def __init__(self, analysis_queue: queue.Queue):
        self.queue = analysis_queue

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.jpg', '.jpeg', '.png')):
            logger.info(f"New image detected: {event.src_path}")
            try:
                self.queue.put_nowait({
                    "path": event.src_path,
                    "timestamp": datetime.now().isoformat(),
                    "event": "created"
                })
            except queue.Full:
                logger.warning("Analysis queue full, dropping oldest")


class VisualAwarenessDaemon:
    """
    Continuous visual awareness service
    """

    def __init__(self, analyze_existing: bool = True):
        self.running = False
        self.analysis_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.observers = []
        self.analyzer = None
        self.analyze_existing = analyze_existing
        self._ensure_tables()
        self._init_analyzer()

    def _ensure_tables(self):
        """Ensure database tables exist"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visual_awareness_state (
                    id INTEGER PRIMARY KEY,
                    last_update TEXT,
                    nodes_active TEXT,
                    user_location TEXT,
                    cluster_state TEXT,
                    activity_summary TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visual_analysis_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT,
                    node_id TEXT,
                    queued_at TEXT,
                    analyzed_at TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to ensure tables: {e}")

    def _init_analyzer(self):
        """Initialize the visual analyzer"""
        try:
            # Try to import visual intelligence
            from visual_intelligence import VisualIntelligence
            self.analyzer = VisualIntelligence(prefer_local=True)
            logger.info("Visual Intelligence analyzer initialized")
        except ImportError:
            logger.warning("Visual Intelligence not available, using basic analysis")
            self.analyzer = None

    def start(self):
        """Start the awareness daemon"""
        self.running = True

        # Start file watchers for each node's screenshot directory
        if SCREENSHOTS_DIR.exists():
            for node_dir in SCREENSHOTS_DIR.iterdir():
                if node_dir.is_dir():
                    logger.info(f"Watching {node_dir}")
                    observer = Observer()
                    observer.schedule(
                        ImageEventHandler(self.analysis_queue),
                        str(node_dir),
                        recursive=False
                    )
                    observer.start()
                    self.observers.append(observer)

        # Queue existing recent images for analysis
        if self.analyze_existing:
            self._queue_recent_images()

        # Start analysis thread
        self.analysis_thread = threading.Thread(target=self._analysis_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

        # Start state update thread
        self.state_thread = threading.Thread(target=self._state_update_loop)
        self.state_thread.daemon = True
        self.state_thread.start()

        logger.info("Visual Awareness Daemon started")

    def stop(self):
        """Stop the daemon"""
        self.running = False
        for observer in self.observers:
            observer.stop()
            observer.join()
        logger.info("Visual Awareness Daemon stopped")

    def _queue_recent_images(self, minutes: int = 5):
        """Queue recent images for analysis"""
        cutoff = datetime.now() - timedelta(minutes=minutes)

        for node_dir in SCREENSHOTS_DIR.iterdir():
            if not node_dir.is_dir():
                continue

            for img_path in sorted(node_dir.glob("*.jpg"),
                                   key=lambda p: p.stat().st_mtime,
                                   reverse=True)[:3]:
                mtime = datetime.fromtimestamp(img_path.stat().st_mtime)
                if mtime > cutoff:
                    try:
                        self.analysis_queue.put_nowait({
                            "path": str(img_path),
                            "timestamp": mtime.isoformat(),
                            "event": "existing"
                        })
                        logger.info(f"Queued recent image: {img_path.name}")
                    except queue.Full:
                        break

    def _analysis_loop(self):
        """Main analysis loop"""
        while self.running:
            try:
                # Get next image from queue with timeout
                try:
                    item = self.analysis_queue.get(timeout=5)
                except queue.Empty:
                    continue

                image_path = item["path"]

                # Skip if file no longer exists
                if not Path(image_path).exists():
                    continue

                # Extract node_id from path
                node_id = Path(image_path).parent.name

                # Analyze the image
                if self.analyzer:
                    logger.info(f"Analyzing {image_path}")
                    result = self.analyzer.analyze(
                        image_path,
                        context=f"Webcam from {node_id}"
                    )

                    if result.get("success"):
                        self._store_analysis_result(node_id, image_path, result)
                        logger.info(f"Stored analysis for {node_id}: {result.get('summary', '')[:50]}")
                    else:
                        logger.warning(f"Analysis failed: {result.get('error')}")
                else:
                    # Basic analysis without vision model
                    self._store_basic_observation(node_id, image_path)

                # Small delay between analyses
                time.sleep(2)

            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                time.sleep(5)

    def _store_analysis_result(self, node_id: str, image_path: str, result: Dict):
        """Store analysis result to database"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Import self analyzer for storage
            from self_visual_analyzer import SelfVisualAnalyzer
            analyzer = SelfVisualAnalyzer()

            analyzer.store_analysis(
                scene=result.get("scene", ""),
                people=result.get("people", ""),
                activity=result.get("activity", ""),
                lighting=result.get("lighting", ""),
                mood=result.get("mood", ""),
                node_id=node_id,
                image_path=image_path,
                summary=result.get("summary"),
                source=result.get("backend", "unknown")
            )

            conn.close()
        except Exception as e:
            logger.error(f"Failed to store result: {e}")

    def _store_basic_observation(self, node_id: str, image_path: str):
        """Store basic observation without vision analysis"""
        try:
            # Extract info from filename
            filename = Path(image_path).name
            # Format: capture_nodeid_YYYYMMDD_HHMMSS_classification.jpg
            parts = filename.replace(".jpg", "").split("_")

            classification = parts[-1] if len(parts) > 4 else "unknown"
            person_present = "person" in classification.lower()
            lighting = "low" if "low_light" in classification else "normal"

            from self_visual_analyzer import SelfVisualAnalyzer
            analyzer = SelfVisualAnalyzer()

            analyzer.store_analysis(
                scene=f"Webcam view from {node_id}",
                people="Person present" if person_present else "No person detected",
                activity=classification.replace("_", " "),
                lighting=lighting,
                mood="active" if person_present else "idle",
                node_id=node_id,
                image_path=image_path,
                source="filename_classification"
            )
        except Exception as e:
            logger.error(f"Failed to store basic observation: {e}")

    def _state_update_loop(self):
        """Update cluster visual state periodically"""
        while self.running:
            try:
                self._update_cluster_state()
            except Exception as e:
                logger.error(f"State update error: {e}")
            time.sleep(ANALYSIS_INTERVAL)

    def _update_cluster_state(self):
        """Update the overall cluster visual state"""
        try:
            from self_visual_analyzer import SelfVisualAnalyzer
            analyzer = SelfVisualAnalyzer()

            awareness = analyzer.get_awareness_summary()

            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO visual_awareness_state
                (id, last_update, nodes_active, user_location, cluster_state, activity_summary)
                VALUES (1, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                json.dumps(awareness.get("nodes_with_data", [])),
                json.dumps(awareness.get("person_detected_at", [])),
                awareness.get("user_status", "unknown"),
                json.dumps(awareness.get("nodes", {}))
            ))

            conn.commit()
            conn.close()

            logger.debug(f"Updated cluster state: {awareness.get('user_status')}")

        except Exception as e:
            logger.error(f"Failed to update cluster state: {e}")

    def get_current_awareness(self) -> Dict[str, Any]:
        """Get current visual awareness"""
        try:
            from self_visual_analyzer import SelfVisualAnalyzer
            analyzer = SelfVisualAnalyzer()
            return analyzer.get_awareness_summary()
        except Exception as e:
            return {"error": str(e)}


def main():
    import argparse
    import signal

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


    parser = argparse.ArgumentParser(description="Visual Awareness Daemon")
    parser.add_argument("--no-analyze-existing", action="store_true",
                       help="Don't analyze existing recent images on start")
    parser.add_argument("--status", action="store_true",
                       help="Show current awareness and exit")

    args = parser.parse_args()

    if args.status:
        daemon = VisualAwarenessDaemon(analyze_existing=False)
        awareness = daemon.get_current_awareness()
        print(json.dumps(awareness, indent=2))
        return

    daemon = VisualAwarenessDaemon(analyze_existing=not args.no_analyze_existing)

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        daemon.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    daemon.start()

    # Keep running
    try:
        while daemon.running:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
