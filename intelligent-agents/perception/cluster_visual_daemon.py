#!/usr/bin/env python3
"""
Cluster Visual Daemon - Cross-Platform Visual Perception for Distributed AGI

This daemon provides visual perception capabilities across the entire cluster,
supporting both macOS and Linux nodes with platform-specific optimizations.

macOS features:
- Screenshot capture via screencapture command
- Webcam capture via OpenCV
- launchd service integration

Linux features:
- Webcam capture via OpenCV
- systemd service integration

All nodes sync to the shared cluster memory for collective visual awareness.
"""

import cv2
import numpy as np
import json
import time
import logging
import sqlite3
import subprocess
import socket
import platform
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import deque
import hashlib

# PIL for screen capture on macOS (more reliable than screencapture via SSH)
try:
    from PIL import ImageGrab
    HAS_PIL_IMAGEGRAB = True
except ImportError:
    HAS_PIL_IMAGEGRAB = False

# Configure logging
LOG_DIR = Path(os.path.expanduser("~/agentic-system/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'cluster_visual_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cluster_visual_daemon")

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
NODE_ID = socket.gethostname().replace('.local', '').replace('.', '_').lower()

# Configuration - platform aware
if IS_MACOS:
    STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
    if not STORAGE_BASE.exists():
        STORAGE_BASE = Path(os.path.expanduser("~/agentic-system"))
else:
    STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
    if not STORAGE_BASE.exists():
        STORAGE_BASE = Path(os.path.expanduser("~/agentic-system"))

SCREENSHOT_DIR = STORAGE_BASE / "databases" / "sensory" / "screenshots" / NODE_ID
SENSORY_DB = STORAGE_BASE / "databases" / "sensory" / f"sensory_memory_{NODE_ID}.db"
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
PERCEPTION_QUEUE = Path(f"/tmp/perception_queue_visual_{NODE_ID}.json")

# Capture settings
CAPTURE_INTERVAL = 10  # seconds between captures
WEBCAM_ENABLED = True
SCREENSHOT_ENABLED = IS_MACOS  # Only on macOS for now
MAX_STORED_IMAGES = 50  # Per node

# Ensure directories exist
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
SENSORY_DB.parent.mkdir(parents=True, exist_ok=True)


class ClusterVisualDaemon:
    """
    Cross-platform visual perception daemon for cluster nodes
    """

    def __init__(self, camera_device: int = 0):
        self.camera_device = camera_device
        self.camera = None
        self.running = False
        self.node_id = NODE_ID

        # Analysis state
        self.last_frame = None
        self.last_screenshot = None
        self.observation_history: deque = deque(maxlen=100)

        # Load models
        self._load_models()

        # Statistics
        self.frames_captured = 0
        self.screenshots_captured = 0
        self.session_start = None

        # Instance config (can be overridden)
        self.capture_interval = CAPTURE_INTERVAL
        self.webcam_enabled = WEBCAM_ENABLED
        self.screenshot_enabled = SCREENSHOT_ENABLED

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"Cluster Visual Daemon initialized on {self.node_id}")
        logger.info(f"Platform: {platform.system()}, Storage: {STORAGE_BASE}")

    def _load_models(self):
        """Load computer vision models"""
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.body_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_upperbody.xml'
            )
            logger.info("Visual models loaded")
        except Exception as e:
            logger.warning(f"Failed to load Haar cascades: {e}")
            self.face_cascade = None
            self.body_cascade = None

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def open_camera(self) -> bool:
        """Initialize camera"""
        if not self.webcam_enabled:
            return False

        try:
            self.camera = cv2.VideoCapture(self.camera_device)
            if not self.camera.isOpened():
                logger.warning(f"Failed to open camera device {self.camera_device}")
                return False

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            logger.info(f"Camera {self.camera_device} opened successfully")
            return True
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False

    def capture_webcam(self) -> Optional[np.ndarray]:
        """Capture frame from webcam"""
        if not self.camera or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        if ret:
            return frame
        return None

    def capture_screenshot(self) -> Optional[str]:
        """Capture screenshot using PIL ImageGrab (works via SSH on macOS)"""
        if not self.screenshot_enabled:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_{self.node_id}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename

        try:
            # Try PIL ImageGrab first (more reliable via SSH/launchd)
            if HAS_PIL_IMAGEGRAB:
                try:
                    screenshot = ImageGrab.grab()
                    if screenshot:
                        screenshot.save(str(filepath))
                        if filepath.exists():
                            self.screenshots_captured += 1
                            logger.info(f"[PIL] Screenshot captured: {filepath}")
                            return str(filepath)
                except Exception as pil_err:
                    logger.warning(f"PIL ImageGrab failed: {pil_err}, trying screencapture")

            # Fall back to screencapture command (requires GUI context)
            if IS_MACOS:
                result = subprocess.run(
                    ['screencapture', '-x', str(filepath)],  # -x = no sound
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and filepath.exists():
                    self.screenshots_captured += 1
                    logger.info(f"[screencapture] Screenshot captured: {filepath}")
                    return str(filepath)
                else:
                    logger.warning(f"screencapture failed: {result.stderr.decode() if result.stderr else 'unknown error'}")
            else:
                # Linux - use gnome-screenshot if available
                for cmd in [['gnome-screenshot', '-f', str(filepath)],
                           ['scrot', str(filepath)]]:
                    try:
                        result = subprocess.run(cmd, capture_output=True, timeout=5)
                        if result.returncode == 0 and filepath.exists():
                            self.screenshots_captured += 1
                            logger.info(f"Screenshot captured: {filepath}")
                            return str(filepath)
                    except FileNotFoundError:
                        continue

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")

        return None

    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in frame"""
        if self.face_cascade is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        face_list = []
        frame_h, frame_w = frame.shape[:2]

        for (x, y, w, h) in faces:
            center_x = (x + w/2) / frame_w
            center_y = (y + h/2) / frame_h

            pos_x = "left" if center_x < 0.33 else "center" if center_x < 0.67 else "right"
            pos_y = "top" if center_y < 0.33 else "middle" if center_y < 0.67 else "bottom"

            face_area = (w * h) / (frame_w * frame_h)
            size = "close" if face_area > 0.1 else "medium" if face_area > 0.02 else "far"

            face_list.append({
                "position": f"{pos_y}_{pos_x}",
                "size": size,
                "area_ratio": float(face_area)
            })

        return face_list

    def detect_motion(self, current_frame: np.ndarray) -> Dict[str, Any]:
        """Detect motion between frames"""
        if self.last_frame is None:
            return {"motion_detected": False, "intensity": 0.0, "level": "none"}

        gray1 = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        intensity = motion_pixels / total_pixels

        return {
            "motion_detected": intensity > 0.01,
            "intensity": float(intensity),
            "level": "high" if intensity > 0.1 else "medium" if intensity > 0.03 else "low" if intensity > 0.01 else "none"
        }

    def analyze_lighting(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze lighting conditions"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        contrast = np.std(gray)

        if brightness < 40:
            condition = "dark"
        elif brightness < 80:
            condition = "dim"
        elif brightness < 160:
            condition = "normal"
        elif brightness < 220:
            condition = "bright"
        else:
            condition = "overexposed"

        return {
            "brightness": float(brightness),
            "contrast": float(contrast),
            "condition": condition
        }

    def classify_scene(self, faces: List, motion: Dict, lighting: Dict) -> str:
        """Classify the scene"""
        person_present = len(faces) > 0
        is_moving = motion["motion_detected"]
        is_dark = lighting["condition"] in ["dark", "dim"]

        if is_dark:
            return "person_in_low_light" if person_present else "dark_empty"

        if person_present:
            if is_moving:
                return "person_very_active" if motion["level"] == "high" else "person_active"
            else:
                close_faces = [f for f in faces if f.get("size") == "close"]
                return "person_at_desk" if close_faces else "person_present_still"
        else:
            return "movement_no_person" if is_moving else "empty_still"

    def analyze_frame(self, frame: np.ndarray, source: str = "webcam") -> Dict[str, Any]:
        """Complete frame analysis"""
        faces = self.detect_faces(frame)
        motion = self.detect_motion(frame)
        lighting = self.analyze_lighting(frame)
        scene = self.classify_scene(faces, motion, lighting)

        observation = {
            "source": f"cluster_visual_daemon_{source}",
            "node_id": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "scene_context": scene,
            "humans": {
                "detected": len(faces) > 0,
                "count": len(faces),
                "faces": faces
            },
            "motion": motion,
            "lighting": lighting,
            "capture_type": source
        }

        # Generate summary
        if scene == "person_at_desk":
            observation["summary"] = f"[{self.node_id}] User at desk"
        elif "active" in scene:
            observation["summary"] = f"[{self.node_id}] User active ({motion['level']} motion)"
        elif scene == "empty_still":
            observation["summary"] = f"[{self.node_id}] Empty and still"
        else:
            observation["summary"] = f"[{self.node_id}] {scene}"

        return observation

    def save_frame(self, frame: np.ndarray, observation: Dict, suffix: str = "") -> Optional[str]:
        """Save frame to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scene = observation.get("scene_context", "unknown")
        filename = f"capture_{self.node_id}_{timestamp}_{scene}{suffix}.jpg"
        filepath = SCREENSHOT_DIR / filename

        try:
            cv2.imwrite(str(filepath), frame)
            self._cleanup_old_frames()
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return None

    def _cleanup_old_frames(self):
        """Remove old frames if over limit"""
        files = sorted(SCREENSHOT_DIR.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_STORED_IMAGES:
            oldest = files.pop(0)
            try:
                oldest.unlink()
            except Exception as e:
                logger.error(f"Failed to remove {oldest}: {e}")

    def store_observation(self, observation: Dict, frame_path: Optional[str] = None):
        """Store observation in local sensory database"""
        try:
            conn = sqlite3.connect(str(SENSORY_DB))
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    node_id TEXT,
                    data TEXT,
                    metadata TEXT,
                    synced INTEGER DEFAULT 0
                )
            ''')

            event_data = {**observation, "frame_path": frame_path}

            cursor.execute('''
                INSERT INTO sensory_events (timestamp, event_type, node_id, data, metadata, synced)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (
                observation["timestamp"],
                "visual_observation",
                self.node_id,
                json.dumps(event_data),
                json.dumps({"platform": platform.system()})
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to store observation: {e}")

    def sync_to_cluster(self, observation: Dict):
        """Sync observation to cluster shared memory"""
        if not CLUSTER_DB.exists():
            logger.debug("Cluster DB not available for sync")
            return

        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Ensure visual_observations table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cluster_visual_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    scene_context TEXT,
                    person_present INTEGER,
                    motion_level TEXT,
                    lighting_condition TEXT,
                    summary TEXT,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO cluster_visual_observations
                (node_id, timestamp, scene_context, person_present, motion_level, lighting_condition, summary, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.node_id,
                observation["timestamp"],
                observation.get("scene_context"),
                1 if observation.get("humans", {}).get("detected") else 0,
                observation.get("motion", {}).get("level"),
                observation.get("lighting", {}).get("condition"),
                observation.get("summary"),
                json.dumps(observation)
            ))

            conn.commit()
            conn.close()
            logger.debug(f"Synced to cluster: {observation.get('summary')}")

        except Exception as e:
            logger.error(f"Failed to sync to cluster: {e}")

    def write_perception_queue(self, observation: Dict):
        """Write to perception queue for other agents"""
        try:
            with open(PERCEPTION_QUEUE, 'w') as f:
                json.dump(observation, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write perception queue: {e}")

    def run(self):
        """Main daemon loop"""
        camera_available = self.open_camera() if self.webcam_enabled else False
        self.running = True
        self.session_start = datetime.now()

        logger.info(f"Cluster Visual Daemon starting on {self.node_id}...")
        logger.info(f"Camera available: {camera_available}, Screenshot enabled: {self.screenshot_enabled}")

        loop_count = 0
        try:
            while self.running:
                observation = None
                frame_path = None
                loop_count += 1

                # Capture webcam if available
                if camera_available:
                    frame = self.capture_webcam()
                    if frame is not None:
                        observation = self.analyze_frame(frame, "webcam")
                        self.frames_captured += 1

                        # Save interesting frames
                        if observation.get("humans", {}).get("detected") or \
                           observation.get("motion", {}).get("level") in ["medium", "high"]:
                            frame_path = self.save_frame(frame, observation)

                        self.last_frame = frame.copy()

                # Capture screenshot (macOS) - every 6 loops (~60 seconds at 10s interval)
                if self.screenshot_enabled and loop_count % 6 == 0:
                    screenshot_path = self.capture_screenshot()
                    if screenshot_path:
                        # Read and analyze screenshot
                        screen_frame = cv2.imread(screenshot_path)
                        if screen_frame is not None:
                            screen_obs = self.analyze_frame(screen_frame, "screenshot")
                            self.store_observation(screen_obs, screenshot_path)
                            self.sync_to_cluster(screen_obs)
                            self.screenshots_captured += 1
                            logger.info(f"[{self.node_id}] Screenshot {self.screenshots_captured}: {screen_obs.get('summary')}")

                # Store and sync main observation
                if observation:
                    self.store_observation(observation, frame_path)
                    self.sync_to_cluster(observation)
                    self.write_perception_queue(observation)
                    self.observation_history.append(observation)

                # Log periodically
                if loop_count % 12 == 0:
                    if observation:
                        logger.info(f"[{self.node_id}] Frame {self.frames_captured}: {observation.get('summary')}")
                    else:
                        logger.info(f"[{self.node_id}] Loop {loop_count}: No webcam, screenshots: {self.screenshots_captured}")

                time.sleep(self.capture_interval)

        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Release resources"""
        if self.camera:
            self.camera.release()
            logger.info("Camera released")

        if self.session_start:
            duration = datetime.now() - self.session_start
            logger.info(f"Session ended: {self.frames_captured} webcam frames, "
                       f"{self.screenshots_captured} screenshots in {duration}")


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


    parser = argparse.ArgumentParser(description="Cluster Visual Daemon")
    parser.add_argument("--device", type=int, default=0, help="Camera device")
    parser.add_argument("--interval", type=int, default=10, help="Capture interval (seconds)")
    parser.add_argument("--no-webcam", action="store_true", help="Disable webcam")
    parser.add_argument("--no-screenshot", action="store_true", help="Disable screenshots")
    parser.add_argument("--status", action="store_true", help="Show status and exit")

    args = parser.parse_args()

    # Apply configuration from args
    capture_interval = args.interval
    webcam_enabled = WEBCAM_ENABLED and not args.no_webcam
    screenshot_enabled = SCREENSHOT_ENABLED and not args.no_screenshot

    if args.status:
        print(f"Cluster Visual Daemon")
        print(f"  Node ID: {NODE_ID}")
        print(f"  Platform: {platform.system()}")
        print(f"  Storage: {STORAGE_BASE}")
        print(f"  Screenshot dir: {SCREENSHOT_DIR}")
        print(f"  Webcam enabled: {webcam_enabled}")
        print(f"  Screenshot enabled: {screenshot_enabled}")
        return

    daemon = ClusterVisualDaemon(camera_device=args.device)
    daemon.capture_interval = capture_interval
    daemon.webcam_enabled = webcam_enabled
    daemon.screenshot_enabled = screenshot_enabled
    daemon.run()


if __name__ == "__main__":
    main()
