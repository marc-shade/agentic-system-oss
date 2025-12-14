#!/usr/bin/env python3
"""
Visual Analysis Daemon - Persistent Environmental Awareness Agent

This daemon continuously captures webcam frames and analyzes them to build
environmental awareness for the AGI system. It integrates with the enhanced
memory system to store visual observations.

Capabilities:
- Continuous webcam monitoring
- Person presence/absence detection
- Activity level analysis (still, moving, active)
- Lighting condition tracking
- Environmental change detection
- Memory integration for pattern learning

Runs as a persistent background service.
"""

import cv2
import numpy as np
import json
import time
import logging
import sqlite3
import threading
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import deque
import hashlib

# Try to import TPU visual inference for Edge TPU acceleration
try:
    from tpu_visual_inference import TPUVisualInference
    _HAS_TPU = True
except ImportError:
    _HAS_TPU = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/mnt/agentic-system/logs/visual_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("visual_analysis_daemon")

# Configuration
CAMERA_DEVICE = 0
CAPTURE_INTERVAL = 5  # seconds between captures
ANALYSIS_WINDOW = 60  # seconds of history to maintain
SCREENSHOT_DIR = Path("/mnt/agentic-system/databases/sensory/screenshots")
SENSORY_DB = Path("/mnt/agentic-system/databases/sensory/sensory_memory.db")
PERCEPTION_QUEUE = Path("/tmp/perception_queue_visual.json")
MAX_STORED_IMAGES = 100  # Rolling buffer of saved images

# Ensure directories exist
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class VisualAnalysisDaemon:
    """
    Persistent visual analysis daemon for environmental awareness
    """

    def __init__(self, camera_device: int = CAMERA_DEVICE, prefer_tpu: bool = True):
        self.camera_device = camera_device
        self.camera = None
        self.running = False

        # TPU state
        self.use_tpu = False
        self.tpu = None

        # Analysis state
        self.last_frame = None
        self.frame_history: deque = deque(maxlen=int(ANALYSIS_WINDOW / CAPTURE_INTERVAL))
        self.observation_history: deque = deque(maxlen=100)

        # Load models
        self._load_models(prefer_tpu)

        # Statistics
        self.frames_captured = 0
        self.persons_detected_total = 0
        self.session_start = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Visual Analysis Daemon initialized")

    def _load_models(self, prefer_tpu: bool = True):
        """Load computer vision models - TPU preferred, CPU fallback"""

        # Try TPU first if available and preferred
        if _HAS_TPU and prefer_tpu:
            try:
                self.tpu = TPUVisualInference()
                if self.tpu.is_available:
                    self.use_tpu = True
                    logger.info("Using Edge TPU for visual analysis (~15ms inference)")
                else:
                    logger.warning("TPU hardware not available, using CPU fallback")
            except Exception as e:
                logger.warning(f"TPU initialization failed: {e}, using CPU fallback")

        # Always load CPU fallback models (Haar cascades)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.body_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_upperbody.xml'
        )
        self.fullbody_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_fullbody.xml'
        )

        backend = "Edge TPU" if self.use_tpu else "CPU (Haar cascades)"
        logger.info(f"Visual analysis ready - backend: {backend}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def open_camera(self) -> bool:
        """Initialize camera connection"""
        try:
            self.camera = cv2.VideoCapture(self.camera_device)
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera device {self.camera_device}")
                return False

            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            logger.info(f"Camera {self.camera_device} opened successfully")
            return True
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture single frame from camera"""
        if not self.camera or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        if ret:
            return frame
        return None

    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect human faces with position analysis - TPU preferred, CPU fallback"""
        frame_h, frame_w = frame.shape[:2]

        # Use TPU if available
        if self.use_tpu and self.tpu:
            try:
                tpu_faces = self.tpu.detect_faces(frame, threshold=0.5)
                face_list = []
                for face in tpu_faces:
                    bbox = face["bbox"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]

                    # Position analysis
                    center_x = (x + w/2) / frame_w
                    center_y = (y + h/2) / frame_h

                    pos_x = "left" if center_x < 0.33 else "center" if center_x < 0.67 else "right"
                    pos_y = "top" if center_y < 0.33 else "middle" if center_y < 0.67 else "bottom"

                    # Size analysis (relative to frame)
                    face_area = (w * h) / (frame_w * frame_h)
                    size = "close" if face_area > 0.1 else "medium" if face_area > 0.02 else "far"

                    face_list.append({
                        "type": "face",
                        "position": f"{pos_y}_{pos_x}",
                        "size": size,
                        "area_ratio": float(face_area),
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "confidence": face["confidence"],
                        "latency_ms": face.get("latency_ms", 0)
                    })
                return face_list
            except Exception as e:
                logger.warning(f"TPU face detection failed, falling back to CPU: {e}")

        # CPU fallback using Haar cascades
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        face_list = []
        for (x, y, w, h) in faces:
            # Position analysis
            center_x = (x + w/2) / frame_w
            center_y = (y + h/2) / frame_h

            pos_x = "left" if center_x < 0.33 else "center" if center_x < 0.67 else "right"
            pos_y = "top" if center_y < 0.33 else "middle" if center_y < 0.67 else "bottom"

            # Size analysis (relative to frame)
            face_area = (w * h) / (frame_w * frame_h)
            size = "close" if face_area > 0.1 else "medium" if face_area > 0.02 else "far"

            face_list.append({
                "type": "face",
                "position": f"{pos_y}_{pos_x}",
                "size": size,
                "area_ratio": float(face_area),
                "bbox": [int(x), int(y), int(w), int(h)],
                "confidence": 0.8  # Haar cascades don't provide confidence
            })

        return face_list

    def detect_motion(self, current_frame: np.ndarray) -> Dict[str, Any]:
        """Detect motion between frames"""
        if self.last_frame is None:
            return {"motion_detected": False, "intensity": 0.0, "level": "none"}

        # Convert to grayscale
        gray1 = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        # Blur to reduce noise
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

        # Calculate frame difference
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # Calculate motion intensity
        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        intensity = motion_pixels / total_pixels

        # Find motion regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_motion_areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 500]

        return {
            "motion_detected": intensity > 0.01,
            "intensity": float(intensity),
            "level": "high" if intensity > 0.1 else "medium" if intensity > 0.03 else "low" if intensity > 0.01 else "none",
            "motion_regions": len(significant_motion_areas)
        }

    def analyze_lighting(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze lighting conditions"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        contrast = np.std(gray)

        # Classify lighting
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

    def analyze_scene_context(self, faces: List, motion: Dict, lighting: Dict) -> str:
        """High-level scene context classification"""
        person_present = len(faces) > 0
        is_moving = motion["motion_detected"]
        is_dark = lighting["condition"] in ["dark", "dim"]

        if is_dark:
            if person_present:
                return "person_in_low_light"
            else:
                return "dark_empty"

        if person_present:
            if is_moving:
                if motion["level"] == "high":
                    return "person_very_active"
                else:
                    return "person_active"
            else:
                # Check if face is large (close to camera - probably working)
                close_faces = [f for f in faces if f.get("size") == "close"]
                if close_faces:
                    return "person_at_desk"
                return "person_present_still"
        else:
            if is_moving:
                return "movement_no_person"
            else:
                return "empty_still"

    def compute_frame_hash(self, frame: np.ndarray) -> str:
        """Compute perceptual hash for duplicate detection"""
        # Resize to small thumbnail
        small = cv2.resize(frame, (16, 16))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        # Compute difference hash
        avg = gray.mean()
        diff = gray > avg
        return hashlib.md5(diff.tobytes()).hexdigest()[:8]

    def should_save_frame(self, observation: Dict) -> bool:
        """Determine if frame is interesting enough to save"""
        # Always save if person detected
        if observation["humans"]["detected"]:
            return True

        # Save if significant motion
        if observation["motion"]["level"] in ["medium", "high"]:
            return True

        # Save if lighting changed significantly
        if len(self.observation_history) > 0:
            last = self.observation_history[-1]
            if abs(observation["lighting"]["brightness"] - last.get("lighting", {}).get("brightness", 0)) > 30:
                return True

        # Otherwise, save periodically (every 10th frame)
        return self.frames_captured % 10 == 0

    def save_frame(self, frame: np.ndarray, observation: Dict) -> Optional[str]:
        """Save frame to disk with metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scene_type = observation.get("scene_context", "unknown")
        filename = f"capture_{timestamp}_{scene_type}.jpg"
        filepath = SCREENSHOT_DIR / filename

        try:
            cv2.imwrite(str(filepath), frame)

            # Cleanup old files if over limit
            self._cleanup_old_frames()

            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return None

    def _cleanup_old_frames(self):
        """Remove oldest frames if over limit"""
        files = sorted(SCREENSHOT_DIR.glob("capture_*.jpg"), key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_STORED_IMAGES:
            oldest = files.pop(0)
            try:
                oldest.unlink()
                logger.debug(f"Removed old frame: {oldest}")
            except Exception as e:
                logger.error(f"Failed to remove {oldest}: {e}")

    def store_observation(self, observation: Dict, frame_path: Optional[str] = None):
        """Store observation in sensory database"""
        try:
            conn = sqlite3.connect(str(SENSORY_DB))
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT,
                    metadata TEXT,
                    indexed_at TEXT
                )
            ''')

            # Store event
            event_data = {
                **observation,
                "frame_path": frame_path
            }

            cursor.execute('''
                INSERT INTO sensory_events (timestamp, event_type, data, metadata, indexed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                observation["timestamp"],
                "visual_observation",
                json.dumps(event_data),
                json.dumps({"source": "visual_analysis_daemon", "camera": self.camera_device}),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to store observation: {e}")

    def write_to_perception_queue(self, observation: Dict):
        """Write observation for other agents to consume"""
        try:
            with open(PERCEPTION_QUEUE, 'w') as f:
                json.dump(observation, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write perception queue: {e}")

    def generate_summary(self, observation: Dict) -> str:
        """Generate human-readable summary"""
        scene = observation.get("scene_context", "unknown")
        faces = observation["humans"]["count"]
        motion = observation["motion"]["level"]
        lighting = observation["lighting"]["condition"]

        summaries = {
            "person_at_desk": f"User at desk ({faces} face(s)), {lighting} lighting",
            "person_very_active": f"User very active ({motion} motion)",
            "person_active": f"User moving ({motion} motion)",
            "person_present_still": f"User present but still",
            "person_in_low_light": f"User in {lighting} environment",
            "movement_no_person": f"Movement detected but no person visible",
            "empty_still": f"Room empty and still, {lighting} lighting",
            "dark_empty": "Dark empty room"
        }

        return summaries.get(scene, f"Scene: {scene}")

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Complete frame analysis pipeline"""
        # Run all detections
        faces = self.detect_faces(frame)
        motion = self.detect_motion(frame)
        lighting = self.analyze_lighting(frame)
        scene_context = self.analyze_scene_context(faces, motion, lighting)
        frame_hash = self.compute_frame_hash(frame)

        # Build observation
        observation = {
            "source": "visual_analysis_daemon",
            "timestamp": datetime.now().isoformat(),
            "scene_context": scene_context,
            "humans": {
                "detected": len(faces) > 0,
                "count": len(faces),
                "faces": faces
            },
            "motion": motion,
            "lighting": lighting,
            "frame_hash": frame_hash,
            "frame_number": self.frames_captured
        }

        observation["summary"] = self.generate_summary(observation)

        return observation

    def run(self):
        """Main daemon loop"""
        if not self.open_camera():
            logger.error("Cannot start daemon without camera")
            return

        self.running = True
        self.session_start = datetime.now()

        logger.info("Visual Analysis Daemon starting continuous monitoring...")

        try:
            while self.running:
                # Capture frame
                frame = self.capture_frame()
                if frame is None:
                    logger.warning("Failed to capture frame, retrying...")
                    time.sleep(1)
                    continue

                # Analyze
                observation = self.analyze_frame(frame)
                self.frames_captured += 1

                if observation["humans"]["detected"]:
                    self.persons_detected_total += 1

                # Store history
                self.observation_history.append(observation)

                # Save frame if interesting
                frame_path = None
                if self.should_save_frame(observation):
                    frame_path = self.save_frame(frame, observation)

                # Store in database
                self.store_observation(observation, frame_path)

                # Write to queue for other agents
                self.write_to_perception_queue(observation)

                # Update last frame for motion detection
                self.last_frame = frame.copy()

                # Log periodically
                if self.frames_captured % 12 == 0:  # Every minute at 5s interval
                    logger.info(f"Processed {self.frames_captured} frames | Last: {observation['summary']}")

                # Wait for next capture
                time.sleep(CAPTURE_INTERVAL)

        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Release resources"""
        if self.camera:
            self.camera.release()
            logger.info("Camera released")

        # Log session summary
        if self.session_start:
            duration = datetime.now() - self.session_start
            logger.info(f"Session ended: {self.frames_captured} frames in {duration}, "
                       f"{self.persons_detected_total} person detections")

    def get_status(self) -> Dict[str, Any]:
        """Get current daemon status"""
        return {
            "running": self.running,
            "frames_captured": self.frames_captured,
            "persons_detected_total": self.persons_detected_total,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "last_observation": self.observation_history[-1] if self.observation_history else None,
            "camera_device": self.camera_device,
            "capture_interval": CAPTURE_INTERVAL
        }


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Analysis Daemon")
    parser.add_argument("--device", type=int, default=0, help="Camera device number")
    parser.add_argument("--interval", type=int, default=5, help="Capture interval in seconds")
    parser.add_argument("--status", action="store_true", help="Show status and exit")

    args = parser.parse_args()

    if args.status:
        # Just show what would run
        print(f"Visual Analysis Daemon")
        print(f"  Camera device: {args.device}")
        print(f"  Capture interval: {args.interval}s")
        print(f"  Screenshot dir: {SCREENSHOT_DIR}")
        print(f"  Database: {SENSORY_DB}")
        return

    global CAPTURE_INTERVAL
    CAPTURE_INTERVAL = args.interval

    daemon = VisualAnalysisDaemon(camera_device=args.device)
    daemon.run()


if __name__ == "__main__":
    main()
