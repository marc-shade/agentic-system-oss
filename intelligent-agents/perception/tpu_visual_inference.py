#!/usr/bin/env python3
"""
TPU Visual Inference - Edge TPU Accelerated Visual Processing

Provides fast (~15ms) visual inference using Google Coral Edge TPU:
- Face detection via face_detection_edgetpu.tflite
- Object detection via ssdlite_mobiledet_coco_edgetpu.tflite
- Scene classification via mobilenet_v2_edgetpu.tflite

ARCHITECTURE: Uses subprocess to call coral-venv Python which has pycoral installed.
This avoids dependency conflicts while keeping TPU access functional.

Usage:
    from tpu_visual_inference import TPUVisualInference

    tpu = TPUVisualInference()
    if tpu.is_available:
        faces = tpu.detect_faces(frame)
        objects = tpu.detect_objects(frame)
        scene = tpu.classify_scene(frame)
"""
import platform

import os
import sys
import cv2
import json
import base64
import tempfile
import subprocess
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("tpu_visual_inference")

# Coral venv Python path
CORAL_VENV_PYTHON = Path(str(_STORAGE_BASE / "coral-venv/bin/python"))
CORAL_TPU_SRC = Path(str(_STORAGE_BASE / "mcp-servers/coral-tpu-mcp/src"))

# Model paths
MODELS_DIR = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))) / "models/coral"
FACE_MODEL = "face_detection_edgetpu.tflite"
OBJECT_MODEL = "ssdlite_mobiledet_coco_edgetpu.tflite"
SCENE_MODEL = "mobilenet_v2_edgetpu.tflite"

# TPU availability - cached after first check
_TPU_CHECKED = False
_TPU_AVAILABLE = False


def _check_tpu_available() -> bool:
    """Check if TPU is available by testing coral-venv."""
    global _TPU_CHECKED, _TPU_AVAILABLE

    if _TPU_CHECKED:
        return _TPU_AVAILABLE

    _TPU_CHECKED = True

    if not CORAL_VENV_PYTHON.exists():
        logger.info("coral-venv not found, TPU visual inference unavailable")
        _TPU_AVAILABLE = False
        return False

    try:
        result = subprocess.run(
            [str(CORAL_VENV_PYTHON), "-c",
             "from pycoral.utils import edgetpu; print(len(edgetpu.list_edge_tpus()))"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and int(result.stdout.strip()) > 0:
            _TPU_AVAILABLE = True
            logger.info("TPU available via coral-venv for visual inference")
            return True
    except Exception as e:
        logger.warning(f"TPU check failed: {e}")

    _TPU_AVAILABLE = False
    return False


class TPUVisualInference:
    """
    Edge TPU accelerated visual inference.

    Uses subprocess calls to coral-venv for pycoral access.
    Provides face detection, object detection, and scene classification
    using Coral Edge TPU for ~15ms inference latency.
    """

    def __init__(self, lazy_load: bool = True):
        """
        Initialize TPU visual inference.

        Args:
            lazy_load: If True, TPU is checked on first use
        """
        self._labels = {}

        # Load COCO labels
        coco_labels_path = MODELS_DIR / "coco_labels.txt"
        if coco_labels_path.exists():
            self._labels["coco"] = self._load_labels(coco_labels_path)

        # Load ImageNet labels
        imagenet_labels_path = MODELS_DIR / "imagenet_labels.txt"
        if imagenet_labels_path.exists():
            self._labels["imagenet"] = self._load_labels(imagenet_labels_path)

        if not lazy_load:
            _check_tpu_available()

    def _load_labels(self, path: Path) -> List[str]:
        """Load label file."""
        labels = []
        with open(path, 'r') as f:
            for line in f:
                parts = line.strip().split(' ', 1)
                if len(parts) >= 2:
                    labels.append(parts[1])
                else:
                    labels.append(line.strip())
        return labels

    @property
    def is_available(self) -> bool:
        """Check if TPU is available."""
        return _check_tpu_available()

    def _call_coral_classify(self, image_path: str, model_name: str, top_k: int = 5, threshold: float = 0.0) -> Optional[Dict]:
        """
        Call coral-venv to run image classification.

        Args:
            image_path: Path to image file
            model_name: Model filename (e.g., 'mobilenet_v2_edgetpu.tflite')
            top_k: Number of top predictions
            threshold: Minimum confidence threshold

        Returns:
            Result dict or None if failed
        """
        if not _check_tpu_available():
            return None

        # Python code to run in coral-venv
        code = f'''
import sys
import json
import time
import numpy as np
from PIL import Image
from pathlib import Path
sys.path.insert(0, "{CORAL_TPU_SRC}")

from pycoral.utils import edgetpu
from pycoral.utils.dataset import read_label_file
from pycoral.adapters import common, classify

MODELS_DIR = "{MODELS_DIR}"
model_path = f"{{MODELS_DIR}}/{model_name}"
labels_path = f"{{MODELS_DIR}}/imagenet_labels.txt"

# Load model
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

# Load labels
labels = read_label_file(labels_path) if Path(labels_path).exists() else []

# Load and preprocess image
image = Image.open("{image_path}")
_, height, width, _ = interpreter.get_input_details()[0]["shape"]
image = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

# Run inference
common.set_input(interpreter, np.array(image))
start = time.perf_counter()
interpreter.invoke()
latency_ms = (time.perf_counter() - start) * 1000

# Get results
classes = classify.get_classes(interpreter, {top_k}, {threshold})
predictions = []
for c in classes:
    pred = {{"class_id": int(c.id), "score": float(c.score)}}
    if labels and int(c.id) < len(labels):
        pred["label"] = labels[int(c.id)]
    predictions.append(pred)

print(json.dumps({{"predictions": predictions, "latency_ms": latency_ms}}))
'''
        try:
            result = subprocess.run(
                [str(CORAL_VENV_PYTHON), "-c", code],
                capture_output=True, text=True, timeout=15,
                env={**os.environ, "PYTHONPATH": str(CORAL_TPU_SRC)}
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                if result.stderr:
                    logger.warning(f"TPU classify stderr: {result.stderr[:300]}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("TPU classify timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"TPU classify invalid JSON: {e}")
            return None
        except Exception as e:
            logger.warning(f"TPU classify failed: {e}")
            return None

    def _call_coral_detect(self, image_path: str, model_name: str, threshold: float = 0.5) -> Optional[Dict]:
        """
        Call coral-venv to run object detection (SSD models).

        Args:
            image_path: Path to image file
            model_name: Model filename
            threshold: Minimum confidence threshold

        Returns:
            Result dict with detections or None if failed
        """
        if not _check_tpu_available():
            return None

        code = f'''
import sys
import json
import time
import numpy as np
from PIL import Image
from pathlib import Path
sys.path.insert(0, "{CORAL_TPU_SRC}")

from pycoral.utils import edgetpu
from pycoral.utils.dataset import read_label_file
from pycoral.adapters import common, detect

MODELS_DIR = "{MODELS_DIR}"
model_path = f"{{MODELS_DIR}}/{model_name}"
labels_path = f"{{MODELS_DIR}}/coco_labels.txt"

# Load model
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

# Load labels
labels = read_label_file(labels_path) if Path(labels_path).exists() else []

# Load image
image = Image.open("{image_path}")
orig_width, orig_height = image.size
_, height, width, _ = interpreter.get_input_details()[0]["shape"]
image_resized = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

# Run inference
common.set_input(interpreter, np.array(image_resized))
start = time.perf_counter()
interpreter.invoke()
latency_ms = (time.perf_counter() - start) * 1000

# Get detections
objs = detect.get_objects(interpreter, {threshold})
detections = []
for obj in objs:
    bbox = obj.bbox
    det = {{
        "class_id": obj.id,
        "score": float(obj.score),
        "bbox": {{
            "x": int(bbox.xmin * orig_width / width),
            "y": int(bbox.ymin * orig_height / height),
            "width": int((bbox.xmax - bbox.xmin) * orig_width / width),
            "height": int((bbox.ymax - bbox.ymin) * orig_height / height)
        }}
    }}
    if labels and obj.id < len(labels):
        det["label"] = labels[obj.id]
    detections.append(det)

print(json.dumps({{"detections": detections, "latency_ms": latency_ms}}))
'''
        try:
            result = subprocess.run(
                [str(CORAL_VENV_PYTHON), "-c", code],
                capture_output=True, text=True, timeout=15,
                env={**os.environ, "PYTHONPATH": str(CORAL_TPU_SRC)}
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                if result.stderr:
                    logger.warning(f"TPU detect stderr: {result.stderr[:300]}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("TPU detect timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"TPU detect invalid JSON: {e}")
            return None
        except Exception as e:
            logger.warning(f"TPU detect failed: {e}")
            return None

    def _call_coral_embedding(self, image_path: str, model_name: str) -> Optional[Dict]:
        """
        Call coral-venv to extract visual embedding from image.

        Args:
            image_path: Path to image file
            model_name: Model filename

        Returns:
            Result dict with embedding or None if failed
        """
        if not _check_tpu_available():
            return None

        code = f'''
import sys
import json
import time
import numpy as np
from PIL import Image
sys.path.insert(0, "{CORAL_TPU_SRC}")

from pycoral.utils import edgetpu
from pycoral.adapters import common

MODELS_DIR = "{MODELS_DIR}"
model_path = f"{{MODELS_DIR}}/{model_name}"

# Load model
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

# Load and preprocess image
image = Image.open("{image_path}")
_, height, width, _ = interpreter.get_input_details()[0]["shape"]
image = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

# Run inference
common.set_input(interpreter, np.array(image))
start = time.perf_counter()
interpreter.invoke()
latency_ms = (time.perf_counter() - start) * 1000

# Get output tensor (embeddings from classification model)
output_details = interpreter.get_output_details()
embedding = interpreter.get_tensor(output_details[0]["index"]).flatten()

print(json.dumps({{"embedding": embedding.tolist(), "latency_ms": latency_ms, "dimensions": len(embedding)}}))
'''
        try:
            result = subprocess.run(
                [str(CORAL_VENV_PYTHON), "-c", code],
                capture_output=True, text=True, timeout=15,
                env={**os.environ, "PYTHONPATH": str(CORAL_TPU_SRC)}
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                if result.stderr:
                    logger.warning(f"TPU embedding stderr: {result.stderr[:300]}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("TPU embedding timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"TPU embedding invalid JSON: {e}")
            return None
        except Exception as e:
            logger.warning(f"TPU embedding failed: {e}")
            return None

    def _save_temp_image(self, frame: np.ndarray) -> Optional[str]:
        """Save numpy array frame to temporary file for coral-venv processing."""
        try:
            # Convert BGR (OpenCV) to RGB
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame

            fd, path = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
            cv2.imwrite(path, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
            return path
        except Exception as e:
            logger.error(f"Failed to save temp image: {e}")
            return None

    def detect_faces(self, frame: np.ndarray, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Detect faces using Edge TPU.

        Args:
            frame: BGR image from OpenCV
            threshold: Minimum confidence threshold

        Returns:
            List of detected faces with bounding boxes and confidence
        """
        if not self.is_available:
            return []

        temp_path = self._save_temp_image(frame)
        if not temp_path:
            return []

        try:
            result = self._call_coral_detect(temp_path, FACE_MODEL, threshold)
            if result and "detections" in result:
                return [
                    {
                        "confidence": d["score"],
                        "bbox": d["bbox"],
                        "latency_ms": result.get("latency_ms", 0)
                    }
                    for d in result["detections"]
                ]
            return []
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def detect_objects(self, frame: np.ndarray, threshold: float = 0.4) -> List[Dict[str, Any]]:
        """
        Detect objects using Edge TPU with COCO model.

        Args:
            frame: BGR image from OpenCV
            threshold: Minimum confidence threshold

        Returns:
            List of detected objects with labels, boxes, and confidence
        """
        if not self.is_available:
            return []

        temp_path = self._save_temp_image(frame)
        if not temp_path:
            return []

        try:
            result = self._call_coral_detect(temp_path, OBJECT_MODEL, threshold)
            if result and "detections" in result:
                return [
                    {
                        "label": d.get("label", f"class_{d['class_id']}"),
                        "class_id": d["class_id"],
                        "confidence": d["score"],
                        "bbox": d["bbox"],
                        "latency_ms": result.get("latency_ms", 0)
                    }
                    for d in result["detections"]
                ]
            return []
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def classify_scene(self, frame: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Classify scene/image content using Edge TPU.

        Args:
            frame: BGR image from OpenCV
            top_k: Number of top predictions to return

        Returns:
            List of top classifications with labels and confidence
        """
        if not self.is_available:
            return []

        temp_path = self._save_temp_image(frame)
        if not temp_path:
            return []

        try:
            result = self._call_coral_classify(temp_path, SCENE_MODEL, top_k)
            if result and "predictions" in result:
                return [
                    {
                        "label": p.get("label", f"class_{p['class_id']}"),
                        "class_id": p["class_id"],
                        "confidence": p["score"],
                        "latency_ms": result.get("latency_ms", 0)
                    }
                    for p in result["predictions"]
                ]
            return []
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_visual_embedding(self, frame: np.ndarray) -> Optional[Tuple[np.ndarray, float]]:
        """
        Extract visual feature embedding from image.

        Args:
            frame: BGR image from OpenCV

        Returns:
            Tuple of (embedding array, latency_ms) or None
        """
        if not self.is_available:
            return None

        temp_path = self._save_temp_image(frame)
        if not temp_path:
            return None

        try:
            result = self._call_coral_embedding(temp_path, SCENE_MODEL)
            if result and "embedding" in result:
                embedding = np.array(result["embedding"], dtype=np.float32)
                return embedding, result.get("latency_ms", 0)
            return None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get TPU inference statistics."""
        if not self.is_available:
            return {"available": False}

        # Read stats from shared file
        stats_file = Path("/tmp/xrg-coral-tpu-stats.json")
        try:
            if stats_file.exists():
                import json
                return json.loads(stats_file.read_text())
        except Exception:
            pass

        return {"available": True, "total_inferences": 0}


# Singleton instance for easy import
_tpu_visual: Optional[TPUVisualInference] = None

def get_tpu_visual() -> TPUVisualInference:
    """Get or create singleton TPU visual inference instance."""
    global _tpu_visual
    if _tpu_visual is None:
        _tpu_visual = TPUVisualInference()
    return _tpu_visual


if __name__ == "__main__":
    # Quick test
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


    parser = argparse.ArgumentParser(description="TPU Visual Inference Test")
    parser.add_argument("--image", type=str, help="Image file to process")
    parser.add_argument("--camera", action="store_true", help="Use camera")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    tpu = TPUVisualInference(lazy_load=False)
    print(f"TPU Available: {tpu.is_available}")

    if args.image:
        frame = cv2.imread(args.image)
        if frame is not None:
            print(f"\nProcessing: {args.image}")

            faces = tpu.detect_faces(frame)
            print(f"Faces: {len(faces)}")
            for f in faces:
                print(f"  - confidence: {f['confidence']:.2f}, bbox: {f['bbox']}")

            objects = tpu.detect_objects(frame)
            print(f"Objects: {len(objects)}")
            for o in objects[:5]:
                print(f"  - {o['label']}: {o['confidence']:.2f}")

            scene = tpu.classify_scene(frame)
            print(f"Scene: {scene[0]['label'] if scene else 'unknown'}")

            embedding = tpu.get_visual_embedding(frame)
            if embedding:
                emb, latency = embedding
                print(f"Embedding: {len(emb)} dimensions, {latency:.1f}ms")

            stats = tpu.get_stats()
            print(f"Stats: {stats}")

    elif args.camera:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("Camera frame captured, running inference...")

                faces = tpu.detect_faces(frame)
                print(f"Faces detected: {len(faces)}")

                objects = tpu.detect_objects(frame)
                print(f"Objects detected: {len(objects)}")
                for o in objects[:5]:
                    print(f"  - {o['label']}: {o['confidence']:.2f}")
            cap.release()
    else:
        print("Use --image <path> or --camera to test inference")
        print("\nQuick availability check:")
        print(f"  coral-venv exists: {CORAL_VENV_PYTHON.exists()}")
        print(f"  TPU available: {tpu.is_available}")
