#!/usr/bin/env python3
"""
Visual Perceiver - Pre-Cognition Agent for Camera Feeds

This agent processes raw camera frames into semantic observations
before feeding them to the consciousness daemon.

Capabilities:
- Object detection
- Scene classification
- Human presence/pose detection
- Motion detection
- Lighting analysis

Outputs structured, tagged observations with confidence scores.
"""

import cv2
import numpy as np
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visual_perceiver")

# Try to import TPU visual inference for Edge TPU acceleration
try:
    from tpu_visual_inference import TPUVisualInference
    _HAS_TPU = True
except ImportError:
    _HAS_TPU = False
    logger.info("TPU visual inference not available, using CPU fallback")

# Configuration
CAMERA_DEVICE = 0  # /dev/video0
CAPTURE_FPS = 1  # Process 1 frame per second
PERCEPTION_QUEUE = Path("/tmp/perception_queue_visual.json")


class VisualPerceiver:
    """
    Pre-cognition agent for visual perception
    Processes camera frames into semantic observations
    """

    def __init__(self, camera_device: int = CAMERA_DEVICE, prefer_tpu: bool = True):
        self.camera = None
        self.camera_device = camera_device
        self.last_frame = None
        self.last_observation = None
        self.use_tpu = False
        self.tpu = None

        # Load pre-trained models
        self._load_models(prefer_tpu)

    def _load_models(self, prefer_tpu: bool = True):
        """Load computer vision models - TPU preferred, CPU fallback"""

        # Try TPU first if available and preferred
        if _HAS_TPU and prefer_tpu:
            try:
                self.tpu = TPUVisualInference()
                if self.tpu.is_available:
                    self.use_tpu = True
                    logger.info("Using Edge TPU for visual perception (~15ms inference)")
                else:
                    logger.warning("TPU hardware not available, using CPU fallback")
            except Exception as e:
                logger.warning(f"TPU initialization failed: {e}, using CPU fallback")

        # Always load CPU fallback models
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.body_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_upperbody.xml'
        )

        backend = "Edge TPU" if self.use_tpu else "CPU (Haar cascades)"
        logger.info(f"Visual perception ready - backend: {backend}")

    def open_camera(self) -> bool:
        """Initialize camera connection"""
        try:
            self.camera = cv2.VideoCapture(self.camera_device)
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera device {self.camera_device}")
                return False

            # Set resolution (lower for faster processing)
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
            self.last_frame = frame
            return frame
        return None

    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect human faces in frame - TPU preferred, CPU fallback"""
        frame_h, frame_w = frame.shape[:2]

        # Use TPU if available
        if self.use_tpu and self.tpu:
            try:
                tpu_faces = self.tpu.detect_faces(frame, threshold=0.5)
                face_list = []
                for face in tpu_faces:
                    bbox = face["bbox"]
                    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
                    center_x = (x + w/2) / frame_w
                    center_y = (y + h/2) / frame_h

                    # Determine position description
                    if center_x < 0.33:
                        pos_x = "left"
                    elif center_x < 0.67:
                        pos_x = "center"
                    else:
                        pos_x = "right"

                    if center_y < 0.33:
                        pos_y = "top"
                    elif center_y < 0.67:
                        pos_y = "middle"
                    else:
                        pos_y = "bottom"

                    face_list.append({
                        "type": "face",
                        "position": f"{pos_y}_{pos_x}",
                        "size": "large" if w > 100 else "medium" if w > 50 else "small",
                        "confidence": face["confidence"],
                        "latency_ms": face.get("latency_ms", 0)
                    })
                return face_list
            except Exception as e:
                logger.warning(f"TPU face detection failed, falling back to CPU: {e}")

        # CPU fallback using Haar cascades
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        face_list = []
        for (x, y, w, h) in faces:
            center_x = (x + w/2) / frame_w
            center_y = (y + h/2) / frame_h

            # Determine position description
            if center_x < 0.33:
                pos_x = "left"
            elif center_x < 0.67:
                pos_x = "center"
            else:
                pos_x = "right"

            if center_y < 0.33:
                pos_y = "top"
            elif center_y < 0.67:
                pos_y = "middle"
            else:
                pos_y = "bottom"

            face_list.append({
                "type": "face",
                "position": f"{pos_y}_{pos_x}",
                "size": "large" if w > 100 else "medium" if w > 50 else "small",
                "confidence": 0.8  # Haar cascades don't provide confidence scores
            })

        return face_list

    def detect_motion(self, current_frame: np.ndarray) -> Dict[str, Any]:
        """Detect motion between frames"""
        if self.last_frame is None:
            return {"motion_detected": False, "intensity": 0.0}

        # Convert to grayscale
        gray1 = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        # Calculate frame difference
        diff = cv2.absdiff(gray1, gray2)

        # Threshold
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # Calculate motion intensity (percentage of changed pixels)
        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        intensity = motion_pixels / total_pixels

        return {
            "motion_detected": intensity > 0.01,  # 1% threshold
            "intensity": float(intensity),
            "level": "high" if intensity > 0.1 else "medium" if intensity > 0.03 else "low"
        }

    def analyze_lighting(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze lighting conditions"""
        # Convert to grayscale and calculate mean brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)

        # Classify lighting
        if brightness < 50:
            condition = "dark"
        elif brightness < 100:
            condition = "dim"
        elif brightness < 180:
            condition = "normal"
        else:
            condition = "bright"

        return {
            "brightness": float(brightness),
            "condition": condition
        }

    def classify_scene(self, frame: np.ndarray, faces: List[Dict], motion: Dict) -> str:
        """High-level scene classification"""
        # Simple rule-based classification
        # Future: Use trained scene classifier

        if len(faces) > 0:
            if motion["motion_detected"]:
                return "person_active"
            else:
                return "person_present_still"
        else:
            if motion["motion_detected"]:
                return "activity_no_person"
            else:
                return "empty_still"

    def perceive(self) -> Dict[str, Any]:
        """
        Main perception function - processes frame into semantic observation
        This is what gets sent to consciousness daemon
        """
        frame = self.capture_frame()
        if frame is None:
            return {
                "error": "Failed to capture frame",
                "timestamp": datetime.now().isoformat()
            }

        # Process frame through perception pipeline
        faces = self.detect_faces(frame)
        motion = self.detect_motion(frame)
        lighting = self.analyze_lighting(frame)
        scene = self.classify_scene(frame, faces, motion)

        # TPU scene classification (additional AI-based classification)
        tpu_scene = None
        tpu_objects = []
        if self.use_tpu and self.tpu:
            try:
                # Get AI scene classification
                scene_results = self.tpu.classify_scene(frame, top_k=3)
                if scene_results:
                    tpu_scene = {
                        "top_label": scene_results[0]["label"],
                        "confidence": scene_results[0]["confidence"],
                        "latency_ms": scene_results[0].get("latency_ms", 0),
                        "alternatives": [
                            {"label": r["label"], "confidence": r["confidence"]}
                            for r in scene_results[1:3]
                        ]
                    }
                # Get object detections
                objects = self.tpu.detect_objects(frame, threshold=0.4)
                tpu_objects = [
                    {"label": o["label"], "confidence": o["confidence"]}
                    for o in objects[:5]  # Top 5 objects
                ]
            except Exception as e:
                logger.debug(f"TPU scene/object detection failed: {e}")

        # Build structured observation
        observation = {
            "source": "visual_perceiver",
            "timestamp": datetime.now().isoformat(),
            "backend": "tpu" if self.use_tpu else "cpu",
            "scene_type": scene,
            "humans": {
                "detected": len(faces) > 0,
                "count": len(faces),
                "faces": faces
            },
            "motion": motion,
            "lighting": lighting,
            "confidence": 0.85 if self.use_tpu else 0.75,
            "summary": self._generate_summary(scene, faces, motion)
        }

        # Add TPU-specific data if available
        if tpu_scene:
            observation["ai_scene"] = tpu_scene
        if tpu_objects:
            observation["objects"] = tpu_objects

        self.last_observation = observation
        return observation

    def _generate_summary(self, scene: str, faces: List, motion: Dict) -> str:
        """Generate human-readable summary of observation"""
        if scene == "person_present_still":
            return f"Person present ({len(faces)} face(s)), sitting still"
        elif scene == "person_active":
            return f"Person active ({len(faces)} face(s)), {motion['level']} motion"
        elif scene == "activity_no_person":
            return f"Activity detected but no person visible"
        elif scene == "empty_still":
            return "Room empty and still"
        else:
            return "Unknown scene"

    def write_to_perception_queue(self, observation: Dict[str, Any]):
        """Write observation to shared queue for consciousness daemon"""
        try:
            # Append to queue file (consciousness daemon will read)
            with open(PERCEPTION_QUEUE, 'w') as f:
                json.dump(observation, f, indent=2)
            logger.debug(f"Observation written to queue: {observation['summary']}")
        except Exception as e:
            logger.error(f"Failed to write to perception queue: {e}")

    def run(self, duration_seconds: Optional[int] = None):
        """
        Main loop - continuous perception

        Args:
            duration_seconds: Run for this many seconds (None = forever)
        """
        if not self.open_camera():
            logger.error("Cannot start perception without camera")
            return

        logger.info("Visual perceiver starting continuous perception...")
        start_time = time.time()
        frame_count = 0

        try:
            while True:
                # Check duration limit
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break

                # Perceive current frame
                observation = self.perceive()

                # Write to queue for consciousness daemon
                self.write_to_perception_queue(observation)

                # Log occasionally
                frame_count += 1
                if frame_count % 10 == 0:
                    logger.info(f"Processed {frame_count} frames. Latest: {observation['summary']}")

                # Wait for next frame (1 FPS)
                time.sleep(1.0 / CAPTURE_FPS)

        except KeyboardInterrupt:
            logger.info("Visual perceiver stopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Release resources"""
        if self.camera:
            self.camera.release()
            logger.info("Camera released")


def main():
    """Entry point for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Perceiver - Pre-Cognition Agent")
    parser.add_argument("--duration", type=int, default=30,
                       help="Run for N seconds (default: 30, 0=forever)")
    parser.add_argument("--device", type=int, default=0,
                       help="Camera device number (default: 0)")

    args = parser.parse_args()

    perceiver = VisualPerceiver(camera_device=args.device)
    perceiver.run(duration_seconds=args.duration if args.duration > 0 else None)


if __name__ == "__main__":
    main()
