#!/usr/bin/env python3
"""
TPU Warm Service - Hybrid TPU + CPU inference for fast hook calls.

Architecture:
- REAL TPU: Image/pose/detection/segmentation/audio via Coral Edge TPU (~2-30ms)
- CPU: Text embeddings via SentenceTransformer (~30ms)
- Heuristics: Fast fallback when models unavailable (~0.1ms)

Endpoints:
- POST /score           - Text importance scoring (CPU)
- POST /classify        - Text intent classification (CPU)
- POST /image_classify  - Image classification (TPU)
- POST /image_score     - Image importance scoring (TPU)
- POST /image_embed     - Visual embeddings (TPU)
- POST /pose_estimate   - Human pose estimation (TPU) - 17 keypoints
- POST /detect_objects  - Object detection (TPU) - 90 COCO classes
- POST /segment_image   - Semantic segmentation (TPU) - 21 VOC classes
- POST /classify_audio  - Audio classification (TPU) - 520+ sounds
- GET  /health          - Service health + stats
- GET  /status          - TPU and CPU model status
- GET  /list_models     - List all available TPU models
- POST /reload          - Reload models

Usage:
    # Start service
    python3 tpu_warm_service.py

    # Text scoring (CPU)
    curl -s http://localhost:8780/score -d '{"text":"content","context":"action"}'

    # Image classification (TPU)
    curl -s http://localhost:8780/image_classify -d '{"image_path":"/path/to/image.jpg"}'

    # Pose estimation (TPU)
    curl -s http://localhost:8780/pose_estimate -d '{"image_path":"/path/to/image.jpg"}'

    # Object detection (TPU)
    curl -s http://localhost:8780/detect_objects -d '{"image_path":"/path/to/image.jpg"}'

    # Health check
    curl -s http://localhost:8780/health
"""

import os
import sys
import json
import time
import signal
import logging
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading

# Add coral-tpu-mcp to path for TPU engine
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", "/mnt/agentic-system"))
CORAL_TPU_SRC = AGENTIC_PATH / "mcp-servers/coral-tpu-mcp/src"
if str(CORAL_TPU_SRC) not in sys.path:
    sys.path.insert(0, str(CORAL_TPU_SRC))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TPU-Warm - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_warm_service")

# Service configuration
PORT = int(os.environ.get("TPU_WARM_PORT", 8780))
HOST = os.environ.get("TPU_WARM_HOST", "127.0.0.1")
MODELS_DIR = AGENTIC_PATH / "models/coral"

# CPU Text Model State (SentenceTransformer)
_text_model = None
_text_model_loaded = False
_text_model_load_time = None

# TPU Image Model State (Coral Edge TPU)
_tpu_engine = None
_tpu_available = False
_tpu_load_time = None
_tpu_default_model = "mobilenet_v2_edgetpu.tflite"

# Extended TPU model configurations
TPU_MODELS = {
    # Image Classification
    "mobilenet_v2": {
        "file": "mobilenet_v2_edgetpu.tflite",
        "labels": "imagenet_labels.txt",
        "input_size": (224, 224),
        "category": "classification"
    },
    # Object Detection
    "coco_detection": {
        "file": "ssdlite_mobiledet_coco_edgetpu.tflite",
        "labels": "coco_labels.txt",
        "input_size": (320, 320),
        "category": "detection"
    },
    # Pose Estimation
    "movenet": {
        "file": "movenet_single_pose_lightning_edgetpu.tflite",
        "labels": None,
        "input_size": (192, 192),
        "category": "pose"
    },
    "posenet_353": {
        "file": "posenet_mobilenet_v1_075_353_481_quant_decoder_edgetpu.tflite",
        "labels": None,
        "input_size": (353, 481),
        "category": "pose"
    },
    # Segmentation
    "deeplabv3_pascal": {
        "file": "deeplabv3_pascal_edgetpu.tflite",
        "labels": "pascal_voc_labels.txt",
        "input_size": (513, 513),
        "category": "segmentation"
    },
    # Audio
    "yamnet": {
        "file": "yamnet_edgetpu.tflite",
        "labels": "yamnet_class_map.csv",
        "input_size": None,
        "category": "audio"
    }
}

# COCO keypoint names (17 keypoints)
POSE_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

# Pascal VOC class names (21 classes)
PASCAL_VOC_CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow",
    "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor"
]

# Request statistics (thread-safe)
_request_count = 0
_tpu_request_count = 0
_total_latency_ms = 0
_tpu_total_latency_ms = 0
_stats_lock = threading.Lock()

# Source category tracking for XRG visualization
# Categories: direct (API calls), hooked (hook system), logged (logging), warming (internal warm-up)
_source_stats = {
    "direct": {"count": 0, "latency_ms": 0.0},
    "hooked": {"count": 0, "latency_ms": 0.0},
    "logged": {"count": 0, "latency_ms": 0.0},
    "warming": {"count": 0, "latency_ms": 0.0}
}

# XRG stats file for real-time monitoring
XRG_STATS_FILE = Path("/tmp/xrg-coral-tpu-stats.json")
_last_xrg_sync = 0


def sync_xrg_stats():
    """Sync current stats to XRG stats file for real-time monitoring."""
    global _last_xrg_sync

    # Rate limit to once per second
    now = time.time()
    if now - _last_xrg_sync < 1.0:
        return
    _last_xrg_sync = now

    try:
        with _stats_lock:
            total = _request_count + _tpu_request_count
            avg_latency = (_total_latency_ms + _tpu_total_latency_ms) / max(1, total)

            # Build by_source from tracked categories
            by_source = {}
            for category, stats in _source_stats.items():
                if stats["count"] > 0:
                    by_source[category] = {
                        "count": stats["count"],
                        "total_latency_ms": stats["latency_ms"],
                        "avg_latency_ms": round(stats["latency_ms"] / max(1, stats["count"]), 2),
                        "category": category
                    }

            # Extract category counts
            by_category = {
                "direct": _source_stats["direct"]["count"],
                "hooked": _source_stats["hooked"]["count"],
                "logged": _source_stats["logged"]["count"],
                "warming": _source_stats["warming"]["count"]
            }

        xrg_stats = {
            "total_inferences": total,
            "total_latency_ms": _total_latency_ms + _tpu_total_latency_ms,
            "avg_latency_ms": round(avg_latency, 2),
            "by_model": {},
            "by_source": by_source,
            "by_category": by_category,
            "tpu_available": _tpu_available,
            "loaded_models": [],
            "timestamp": now
        }

        with open(XRG_STATS_FILE, 'w') as f:
            json.dump(xrg_stats, f)

    except Exception as e:
        logger.debug(f"Failed to sync XRG stats: {e}")


def load_text_model():
    """Load the SentenceTransformer model for text embeddings (CPU, ~7s)."""
    global _text_model, _text_model_loaded, _text_model_load_time

    if _text_model_loaded:
        return True

    try:
        start = time.perf_counter()
        logger.info("Loading SentenceTransformer model (CPU text embeddings)...")

        from sentence_transformers import SentenceTransformer
        _text_model = SentenceTransformer('all-MiniLM-L6-v2')

        load_time = (time.perf_counter() - start) * 1000
        _text_model_load_time = load_time
        _text_model_loaded = True

        logger.info(f"CPU text model loaded in {load_time:.0f}ms")
        return True

    except Exception as e:
        logger.error(f"Failed to load CPU text model: {e}")
        return False


def load_tpu_model():
    """Load TPU engine and default model for image classification (~0.5s)."""
    global _tpu_engine, _tpu_available, _tpu_load_time

    if _tpu_available and _tpu_engine is not None:
        return True

    try:
        start = time.perf_counter()
        logger.info("Initializing Coral Edge TPU...")

        # Import TPU engine from coral-tpu-mcp
        from coral_tpu_mcp.tpu_engine import get_engine

        _tpu_engine = get_engine()

        if not _tpu_engine.is_available:
            logger.warning("Edge TPU not detected - image scoring will use heuristics")
            _tpu_available = False
            return False

        # Pre-load default model for fast inference
        _tpu_engine.load_model(_tpu_default_model, "imagenet_labels.txt")

        load_time = (time.perf_counter() - start) * 1000
        _tpu_load_time = load_time
        _tpu_available = True

        logger.info(f"TPU initialized in {load_time:.0f}ms - real hardware acceleration ready!")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize TPU: {e}")
        _tpu_available = False
        return False


def load_all_models():
    """Load both CPU text model and TPU image model."""
    text_ok = load_text_model()
    tpu_ok = load_tpu_model()
    return text_ok or tpu_ok  # At least one should work


def score_importance_fast(text: str, context: str = "general") -> Dict[str, Any]:
    """
    Score text importance using CPU warm model (~30ms vs 7000ms cold).

    Returns dict with importance_score, method, latency_ms
    Thread-safe for concurrent Claude Code sessions.
    """
    global _request_count, _total_latency_ms

    start = time.perf_counter()
    with _stats_lock:
        _request_count += 1

    if not _text_model_loaded:
        # Heuristic fallback
        score = _heuristic_score(text, context)
        latency = (time.perf_counter() - start) * 1000
        return {
            "importance_score": score,
            "method": "heuristic",
            "latency_ms": latency,
            "model_loaded": False,
            "device": "cpu_heuristic"
        }

    try:
        # Semantic scoring with warm CPU model
        embedding = _text_model.encode(text, convert_to_numpy=True)

        # Context-specific reference embeddings
        context_refs = {
            "action": "critical system operation modification change",
            "memory": "important learning insight knowledge",
            "event": "significant occurrence milestone achievement",
            "general": "noteworthy relevant meaningful"
        }

        ref_text = context_refs.get(context, context_refs["general"])
        ref_embedding = _text_model.encode(ref_text, convert_to_numpy=True)

        # Cosine similarity
        import numpy as np
        similarity = np.dot(embedding, ref_embedding) / (
            np.linalg.norm(embedding) * np.linalg.norm(ref_embedding)
        )

        # Normalize to 0-1 range
        score = float(max(0.0, min(1.0, (similarity + 1) / 2)))

        latency = (time.perf_counter() - start) * 1000
        with _stats_lock:
            _total_latency_ms += latency

        return {
            "importance_score": score,
            "method": "semantic",
            "latency_ms": latency,
            "model_loaded": True,
            "device": "cpu"
        }

    except Exception as e:
        logger.warning(f"Semantic scoring failed: {e}, using heuristic")
        score = _heuristic_score(text, context)
        latency = (time.perf_counter() - start) * 1000
        return {
            "importance_score": score,
            "method": "heuristic_fallback",
            "latency_ms": latency,
            "error": str(e),
            "device": "cpu_heuristic"
        }


# =============================================================================
# TPU IMAGE CLASSIFICATION FUNCTIONS (Real Coral Edge TPU)
# =============================================================================

def _load_image_for_tpu(image_path: str) -> Optional[Any]:
    """Load and preprocess image for TPU inference."""
    try:
        from PIL import Image
        from pycoral.adapters import common

        img = Image.open(image_path).convert('RGB')

        # Get model input size
        interpreter = _tpu_engine.interpreters[_tpu_default_model]
        input_details = interpreter.get_input_details()[0]
        input_shape = input_details['shape']  # e.g., [1, 224, 224, 3]
        height, width = input_shape[1], input_shape[2]

        # Resize to model's expected input
        img = img.resize((width, height), Image.Resampling.LANCZOS)

        return img

    except Exception as e:
        logger.error(f"Failed to load image {image_path}: {e}")
        return None


def classify_image_tpu(image_path: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Classify image using real Coral Edge TPU (~2ms inference).

    Args:
        image_path: Path to image file
        top_k: Number of top predictions to return

    Returns:
        Dict with predictions, latency_ms, device
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()
    with _stats_lock:
        _tpu_request_count += 1

    if not _tpu_available or _tpu_engine is None:
        latency = (time.perf_counter() - start) * 1000
        return {
            "predictions": [],
            "method": "unavailable",
            "latency_ms": latency,
            "device": "none",
            "error": "TPU not available"
        }

    try:
        # Load and preprocess image
        img = _load_image_for_tpu(image_path)
        if img is None:
            return {
                "predictions": [],
                "method": "error",
                "latency_ms": (time.perf_counter() - start) * 1000,
                "error": "Failed to load image"
            }

        import numpy as np
        input_data = np.asarray(img)

        # Run TPU inference
        result = _tpu_engine.classify(_tpu_default_model, input_data, top_k=top_k)

        latency = (time.perf_counter() - start) * 1000
        with _stats_lock:
            _tpu_total_latency_ms += latency

        return {
            "predictions": result.predictions,
            "method": "tpu",
            "latency_ms": latency,
            "tpu_latency_ms": result.latency_ms,  # Just the TPU inference time
            "device": "coral_edge_tpu",
            "model": result.model_name
        }

    except Exception as e:
        logger.error(f"TPU classification failed: {e}")
        return {
            "predictions": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e),
            "device": "coral_edge_tpu"
        }


def score_image_importance(image_path: str) -> Dict[str, Any]:
    """
    Score image importance using TPU classification results.

    High-importance images contain:
    - People, faces, screens (work context)
    - Error messages, warnings
    - Code, documents

    Args:
        image_path: Path to image file

    Returns:
        Dict with importance_score (0.0-1.0), predictions, latency_ms
    """
    # First classify the image
    result = classify_image_tpu(image_path, top_k=10)

    if result.get("method") == "error" or not result.get("predictions"):
        return {
            "importance_score": 0.3,  # Default neutral score
            "method": "heuristic_fallback",
            "latency_ms": result.get("latency_ms", 0),
            "reason": "Classification failed or no predictions"
        }

    # Important class patterns (ImageNet labels)
    high_importance = [
        "monitor", "screen", "laptop", "computer", "keyboard",
        "notebook", "desktop", "display", "person", "face",
        "document", "book", "letter", "envelope", "paper"
    ]
    medium_importance = [
        "phone", "remote", "mouse", "printer", "scanner",
        "desk", "chair", "table", "office", "workspace"
    ]

    score = 0.3  # Base score
    predictions = result.get("predictions", [])

    for pred in predictions:
        label = pred.get("label", "").lower()
        pred_score = pred.get("score", 0)

        for kw in high_importance:
            if kw in label:
                score += 0.15 * pred_score
                break

        for kw in medium_importance:
            if kw in label:
                score += 0.08 * pred_score
                break

    score = min(1.0, max(0.0, score))

    return {
        "importance_score": score,
        "method": "tpu_classification",
        "latency_ms": result.get("latency_ms", 0),
        "device": result.get("device", "coral_edge_tpu"),
        "top_predictions": predictions[:3]
    }


def get_visual_embedding(image_path: str) -> Dict[str, Any]:
    """
    Extract visual embeddings from image using TPU.

    Args:
        image_path: Path to image file

    Returns:
        Dict with embedding vector, latency_ms
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()

    if not _tpu_available or _tpu_engine is None:
        return {
            "embedding": None,
            "method": "unavailable",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": "TPU not available"
        }

    try:
        img = _load_image_for_tpu(image_path)
        if img is None:
            return {
                "embedding": None,
                "method": "error",
                "latency_ms": (time.perf_counter() - start) * 1000,
                "error": "Failed to load image"
            }

        import numpy as np
        input_data = np.asarray(img)

        # Get embeddings from TPU
        embedding, tpu_latency = _tpu_engine.get_embedding(_tpu_default_model, input_data)

        latency = (time.perf_counter() - start) * 1000
        with _stats_lock:
            _tpu_request_count += 1
            _tpu_total_latency_ms += latency

        return {
            "embedding": embedding.tolist(),  # Convert numpy to list for JSON
            "embedding_dim": len(embedding),
            "method": "tpu",
            "latency_ms": latency,
            "tpu_latency_ms": tpu_latency,
            "device": "coral_edge_tpu"
        }

    except Exception as e:
        logger.error(f"TPU embedding extraction failed: {e}")
        return {
            "embedding": None,
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


# =============================================================================
# POSE ESTIMATION (TPU)
# =============================================================================

def estimate_pose_tpu(image_path: str, model: str = "movenet") -> Dict[str, Any]:
    """
    Estimate human pose from image using TPU.

    Returns 17 body keypoints with coordinates and confidence scores.
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()

    if not _tpu_available or _tpu_engine is None:
        return {
            "keypoints": [],
            "method": "unavailable",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": "TPU not available"
        }

    model_config = TPU_MODELS.get(model, TPU_MODELS["movenet"])
    model_file = model_config["file"]

    # Check if model exists and load
    model_path = MODELS_DIR / model_file
    if not model_path.exists():
        return {
            "keypoints": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": f"Model not found: {model_file}"
        }

    try:
        # Load model if needed
        if model_file not in _tpu_engine.interpreters:
            _tpu_engine.load_model(model_file)

        # Load and preprocess image
        from PIL import Image
        import numpy as np

        img = Image.open(image_path).convert('RGB')
        original_size = img.size

        input_size = model_config["input_size"]
        img_resized = img.resize(input_size, Image.Resampling.LANCZOS)
        input_data = np.asarray(img_resized, dtype=np.uint8)

        # Run inference
        from pycoral.adapters import common
        interpreter = _tpu_engine.interpreters[model_file]
        common.set_input(interpreter, input_data)
        interpreter.invoke()

        latency = (time.perf_counter() - start) * 1000

        # Get output
        output_details = interpreter.get_output_details()
        output = interpreter.get_tensor(output_details[0]["index"])

        # Parse keypoints (MoveNet format: [1, 1, 17, 3] = [y, x, score])
        keypoints = []
        if model == "movenet" and len(output.shape) == 4:
            poses = output[0, 0]  # [17, 3]
            for i, kp_name in enumerate(POSE_KEYPOINTS):
                y, x, score = poses[i]
                keypoints.append({
                    "name": kp_name,
                    "x": float(x) * original_size[0],
                    "y": float(y) * original_size[1],
                    "confidence": float(score)
                })
        else:
            # PoseNet format
            if len(output_details) >= 2:
                heatmaps = interpreter.get_tensor(output_details[0]["index"])
                for i, kp_name in enumerate(POSE_KEYPOINTS):
                    if i < heatmaps.shape[-1]:
                        hm = heatmaps[0, :, :, i]
                        max_idx = np.unravel_index(np.argmax(hm), hm.shape)
                        score = float(hm[max_idx])
                        y = (max_idx[0] / hm.shape[0]) * original_size[1]
                        x = (max_idx[1] / hm.shape[1]) * original_size[0]
                        keypoints.append({
                            "name": kp_name,
                            "x": float(x),
                            "y": float(y),
                            "confidence": score
                        })

        with _stats_lock:
            _tpu_request_count += 1
            _tpu_total_latency_ms += latency

        return {
            "keypoints": keypoints,
            "num_keypoints": len(keypoints),
            "model": model,
            "latency_ms": latency,
            "image_size": original_size,
            "device": "coral_edge_tpu"
        }

    except Exception as e:
        logger.error(f"Pose estimation failed: {e}")
        return {
            "keypoints": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


# =============================================================================
# OBJECT DETECTION (TPU)
# =============================================================================

def detect_objects_tpu(image_path: str, threshold: float = 0.4, max_detections: int = 10) -> Dict[str, Any]:
    """
    Detect objects in image using TPU SSD model.

    Returns bounding boxes for 90 COCO classes.
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()

    if not _tpu_available or _tpu_engine is None:
        return {
            "detections": [],
            "method": "unavailable",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": "TPU not available"
        }

    model_config = TPU_MODELS["coco_detection"]
    model_file = model_config["file"]

    model_path = MODELS_DIR / model_file
    if not model_path.exists():
        return {
            "detections": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": f"Model not found: {model_file}"
        }

    try:
        # Load model
        if model_file not in _tpu_engine.interpreters:
            _tpu_engine.load_model(model_file, model_config["labels"])

        from PIL import Image
        import numpy as np
        from pycoral.adapters import common, detect

        img = Image.open(image_path).convert('RGB')
        original_size = img.size

        input_size = model_config["input_size"]
        img_resized = img.resize(input_size, Image.Resampling.LANCZOS)
        input_data = np.asarray(img_resized, dtype=np.uint8)

        interpreter = _tpu_engine.interpreters[model_file]
        common.set_input(interpreter, input_data)
        interpreter.invoke()

        latency = (time.perf_counter() - start) * 1000

        # Get detections
        try:
            objs = detect.get_objects(interpreter, threshold)
        except:
            # Manual parsing fallback
            output_details = interpreter.get_output_details()
            boxes = interpreter.get_tensor(output_details[0]["index"])[0]
            classes = interpreter.get_tensor(output_details[1]["index"])[0]
            scores = interpreter.get_tensor(output_details[2]["index"])[0]
            count = int(interpreter.get_tensor(output_details[3]["index"])[0])

            objs = []
            for i in range(min(count, len(scores))):
                if scores[i] >= threshold:
                    objs.append({
                        "id": int(classes[i]),
                        "score": float(scores[i]),
                        "bbox": boxes[i]
                    })

        # Load labels
        labels = _tpu_engine.labels.get(model_file, [])

        detections = []
        for obj in objs[:max_detections]:
            if hasattr(obj, 'score'):
                obj_id = obj.id
                obj_score = obj.score
                bbox = {
                    "xmin": int(obj.bbox.xmin * original_size[0]),
                    "ymin": int(obj.bbox.ymin * original_size[1]),
                    "xmax": int(obj.bbox.xmax * original_size[0]),
                    "ymax": int(obj.bbox.ymax * original_size[1])
                }
            else:
                obj_id = obj["id"]
                obj_score = obj["score"]
                ymin, xmin, ymax, xmax = obj["bbox"]
                bbox = {
                    "xmin": int(xmin * original_size[0]),
                    "ymin": int(ymin * original_size[1]),
                    "xmax": int(xmax * original_size[0]),
                    "ymax": int(ymax * original_size[1])
                }

            label = labels[obj_id] if obj_id < len(labels) else f"class_{obj_id}"
            detections.append({
                "label": label,
                "class_id": obj_id,
                "confidence": float(obj_score),
                "bbox": bbox
            })

        with _stats_lock:
            _tpu_request_count += 1
            _tpu_total_latency_ms += latency

        return {
            "detections": detections,
            "num_detections": len(detections),
            "latency_ms": latency,
            "image_size": original_size,
            "threshold": threshold,
            "device": "coral_edge_tpu"
        }

    except Exception as e:
        logger.error(f"Object detection failed: {e}")
        return {
            "detections": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


# =============================================================================
# SEMANTIC SEGMENTATION (TPU)
# =============================================================================

def segment_image_tpu(image_path: str, return_mask: bool = False) -> Dict[str, Any]:
    """
    Perform semantic segmentation using DeepLab v3 TPU model.

    Returns class distribution for 21 Pascal VOC classes.
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()

    if not _tpu_available or _tpu_engine is None:
        return {
            "class_distribution": {},
            "method": "unavailable",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": "TPU not available"
        }

    model_config = TPU_MODELS["deeplabv3_pascal"]
    model_file = model_config["file"]

    model_path = MODELS_DIR / model_file
    if not model_path.exists():
        return {
            "class_distribution": {},
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": f"Model not found: {model_file}"
        }

    try:
        if model_file not in _tpu_engine.interpreters:
            _tpu_engine.load_model(model_file, model_config["labels"])

        from PIL import Image
        import numpy as np
        from pycoral.adapters import common

        img = Image.open(image_path).convert('RGB')
        original_size = img.size

        input_size = model_config["input_size"]
        img_resized = img.resize(input_size, Image.Resampling.LANCZOS)
        input_data = np.asarray(img_resized, dtype=np.uint8)

        interpreter = _tpu_engine.interpreters[model_file]
        common.set_input(interpreter, input_data)
        interpreter.invoke()

        latency = (time.perf_counter() - start) * 1000

        # Get segmentation output
        output_details = interpreter.get_output_details()
        seg_output = interpreter.get_tensor(output_details[0]["index"])

        # Get class per pixel
        if len(seg_output.shape) == 4:
            seg_map = np.argmax(seg_output[0], axis=-1)
        else:
            seg_map = seg_output[0] if len(seg_output.shape) == 3 else seg_output

        # Count pixels per class
        unique, counts = np.unique(seg_map, return_counts=True)
        total_pixels = seg_map.size

        class_distribution = {}
        for cls_id, count in zip(unique, counts):
            cls_id = int(cls_id)
            label = PASCAL_VOC_CLASSES[cls_id] if cls_id < len(PASCAL_VOC_CLASSES) else f"class_{cls_id}"
            percentage = float(count) / total_pixels * 100
            if percentage > 0.5:  # Only include >0.5% coverage
                class_distribution[label] = {
                    "class_id": cls_id,
                    "pixel_count": int(count),
                    "percentage": round(percentage, 2)
                }

        with _stats_lock:
            _tpu_request_count += 1
            _tpu_total_latency_ms += latency

        result = {
            "class_distribution": class_distribution,
            "num_classes_detected": len(class_distribution),
            "latency_ms": latency,
            "image_size": original_size,
            "segmentation_size": list(seg_map.shape),
            "device": "coral_edge_tpu"
        }

        if return_mask:
            result["segmentation_mask"] = seg_map.tolist()

        return result

    except Exception as e:
        logger.error(f"Segmentation failed: {e}")
        return {
            "class_distribution": {},
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


# =============================================================================
# AUDIO CLASSIFICATION (TPU)
# =============================================================================

def classify_audio_tpu(audio_path: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Classify audio/sounds using YamNet TPU model.

    Recognizes 520+ sound classes (speech, music, dogs, cars, etc.)
    """
    global _tpu_request_count, _tpu_total_latency_ms

    start = time.perf_counter()

    if not _tpu_available or _tpu_engine is None:
        return {
            "predictions": [],
            "method": "unavailable",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": "TPU not available"
        }

    model_config = TPU_MODELS["yamnet"]
    model_file = model_config["file"]

    model_path = MODELS_DIR / model_file
    if not model_path.exists():
        return {
            "predictions": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": f"Model not found: {model_file}"
        }

    try:
        import librosa
        import numpy as np
        from pycoral.adapters import common

        if model_file not in _tpu_engine.interpreters:
            _tpu_engine.load_model(model_file)

        # Load audio
        audio_data, sr = librosa.load(audio_path, sr=16000, mono=True)

        # YamNet expects 0.975s windows
        window_length = int(0.975 * sr)
        if len(audio_data) < window_length:
            audio_data = np.pad(audio_data, (0, window_length - len(audio_data)))

        window = audio_data[:window_length]

        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=window, sr=sr, n_fft=1024, hop_length=160, n_mels=96
        )
        log_mel = librosa.power_to_db(mel_spec, ref=np.max)
        log_mel_norm = (log_mel - np.mean(log_mel)) / (np.std(log_mel) + 1e-8)

        interpreter = _tpu_engine.interpreters[model_file]
        input_details = interpreter.get_input_details()
        expected_shape = input_details[0]["shape"]

        # Reshape for model
        if len(expected_shape) == 3:
            target_frames = expected_shape[1]
            target_mels = expected_shape[2]
            features = log_mel_norm.T
            if features.shape[0] != target_frames:
                indices = np.linspace(0, features.shape[0]-1, target_frames).astype(int)
                features = features[indices]
            features = features.reshape(1, target_frames, target_mels).astype(np.float32)
            if input_details[0]["dtype"] == np.uint8:
                features = ((features - features.min()) / (features.max() - features.min() + 1e-8) * 255).astype(np.uint8)
        else:
            features = log_mel_norm.flatten().astype(np.float32)
            features = features[:np.prod(expected_shape[1:])].reshape(expected_shape)

        common.set_input(interpreter, features)
        interpreter.invoke()

        latency = (time.perf_counter() - start) * 1000

        # Get predictions
        output_details = interpreter.get_output_details()
        scores = interpreter.get_tensor(output_details[0]["index"]).flatten()

        # Load YamNet labels
        labels = []
        labels_path = MODELS_DIR / model_config["labels"]
        if labels_path.exists():
            import csv
            with open(labels_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        labels.append(row[2])
                    elif len(row) >= 1:
                        labels.append(row[0])

        # Top-k predictions
        top_indices = np.argsort(scores)[-top_k:][::-1]
        predictions = []
        for idx in top_indices:
            label = labels[idx] if idx < len(labels) else f"sound_class_{idx}"
            predictions.append({
                "label": label,
                "class_id": int(idx),
                "confidence": float(scores[idx])
            })

        with _stats_lock:
            _tpu_request_count += 1
            _tpu_total_latency_ms += latency

        return {
            "predictions": predictions,
            "audio_duration_sec": len(audio_data) / sr,
            "latency_ms": latency,
            "num_classes": len(labels) if labels else len(scores),
            "device": "coral_edge_tpu"
        }

    except ImportError as e:
        return {
            "predictions": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": f"Missing audio library: {e}. Install librosa."
        }
    except Exception as e:
        logger.error(f"Audio classification failed: {e}")
        return {
            "predictions": [],
            "method": "error",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


# =============================================================================
# LIST MODELS
# =============================================================================

def list_available_models() -> Dict[str, Any]:
    """List all available TPU models grouped by category."""
    by_category = {}

    for name, config in TPU_MODELS.items():
        category = config.get("category", "other")
        if category not in by_category:
            by_category[category] = []

        model_path = MODELS_DIR / config["file"]
        exists = model_path.exists()
        loaded = _tpu_engine and config["file"] in _tpu_engine.interpreters

        by_category[category].append({
            "name": name,
            "file": config["file"],
            "input_size": config["input_size"],
            "installed": exists,
            "loaded": loaded
        })

    total = len(TPU_MODELS)
    installed = sum(1 for cfg in TPU_MODELS.values() if (MODELS_DIR / cfg["file"]).exists())
    loaded = len(_tpu_engine.interpreters) if _tpu_engine else 0

    return {
        "models_by_category": by_category,
        "summary": {
            "total_models": total,
            "installed": installed,
            "loaded": loaded,
            "tpu_available": _tpu_available
        }
    }


def _heuristic_score(text: str, context: str) -> float:
    """Fast heuristic scoring when model unavailable."""
    score = 0.3  # Base score

    text_lower = text.lower()

    # High importance keywords
    high_keywords = ["error", "critical", "fail", "security", "bug", "fix",
                     "important", "urgent", "breaking", "production"]
    for kw in high_keywords:
        if kw in text_lower:
            score += 0.15

    # Medium importance
    med_keywords = ["update", "change", "modify", "create", "delete", "config"]
    for kw in med_keywords:
        if kw in text_lower:
            score += 0.08

    # Length factor (longer = more detailed = potentially more important)
    if len(text) > 200:
        score += 0.1
    elif len(text) > 100:
        score += 0.05

    # Context boost
    context_boosts = {
        "action": 0.1,
        "memory": 0.05,
        "event": 0.08
    }
    score += context_boosts.get(context, 0)

    return min(1.0, max(0.0, score))


def classify_intent_fast(text: str) -> Dict[str, Any]:
    """Fast intent classification using CPU warm model."""
    start = time.perf_counter()

    if not _text_model_loaded:
        return {
            "intent": "general",
            "confidence": 0.5,
            "method": "heuristic",
            "latency_ms": (time.perf_counter() - start) * 1000,
            "device": "cpu_heuristic"
        }

    try:
        # Intent categories with reference phrases
        intents = {
            "code": "write code implement function class method",
            "debug": "fix bug error troubleshoot debug issue",
            "research": "search find information learn understand",
            "system": "configure setup install manage system",
            "question": "what how why explain describe",
            "task": "do create make build deploy"
        }

        text_embedding = _text_model.encode(text, convert_to_numpy=True)

        import numpy as np
        best_intent = "general"
        best_score = 0.0

        for intent, ref in intents.items():
            ref_embedding = _text_model.encode(ref, convert_to_numpy=True)
            similarity = np.dot(text_embedding, ref_embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(ref_embedding)
            )
            if similarity > best_score:
                best_score = similarity
                best_intent = intent

        latency = (time.perf_counter() - start) * 1000

        return {
            "intent": best_intent,
            "confidence": float(best_score),
            "method": "semantic",
            "latency_ms": latency
        }

    except Exception as e:
        return {
            "intent": "general",
            "confidence": 0.5,
            "method": "error",
            "error": str(e),
            "latency_ms": (time.perf_counter() - start) * 1000
        }


class TPUWarmHandler(BaseHTTPRequestHandler):
    """HTTP request handler for hybrid TPU + CPU warm service."""

    def log_message(self, format, *args):
        """Suppress default logging, use our logger."""
        pass

    def _send_json(self, data: Dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
        # Sync stats to XRG after each request
        sync_xrg_stats()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            # Combined health check for both CPU and TPU
            cpu_avg = _total_latency_ms / max(1, _request_count)
            tpu_avg = _tpu_total_latency_ms / max(1, _tpu_request_count)

            self._send_json({
                "status": "healthy",
                # CPU text model status
                "cpu_text_model_loaded": _text_model_loaded,
                "cpu_text_model_load_time_ms": _text_model_load_time,
                "cpu_request_count": _request_count,
                "cpu_avg_latency_ms": cpu_avg,
                # TPU image model status
                "tpu_available": _tpu_available,
                "tpu_load_time_ms": _tpu_load_time,
                "tpu_request_count": _tpu_request_count,
                "tpu_avg_latency_ms": tpu_avg,
                # Combined
                "request_count": _request_count + _tpu_request_count,
                "avg_latency_ms": cpu_avg,  # For backward compatibility
                "model_loaded": _text_model_loaded,  # For backward compatibility
                "uptime_seconds": time.time() - _start_time
            })

        elif self.path == "/status":
            tpu_models = []
            if _tpu_engine and _tpu_available:
                tpu_models = list(_tpu_engine.interpreters.keys())

            self._send_json({
                "service": "tpu-warm-hybrid",
                "port": PORT,
                # CPU text capabilities
                "cpu": {
                    "model": "all-MiniLM-L6-v2",
                    "loaded": _text_model_loaded,
                    "capabilities": ["text_scoring", "text_classify", "text_embedding"]
                },
                # TPU image capabilities
                "tpu": {
                    "device": "coral_edge_tpu",
                    "available": _tpu_available,
                    "loaded_models": tpu_models,
                    "capabilities": ["image_classify", "image_score", "image_embed"]
                },
                "ready": _text_model_loaded or _tpu_available
            })

        elif self.path == "/tpu_stats":
            # Detailed TPU statistics
            if _tpu_engine and _tpu_available:
                self._send_json(_tpu_engine.get_stats())
            else:
                self._send_json({"error": "TPU not available", "available": False})

        elif self.path == "/list_models":
            # List all available TPU models
            result = list_available_models()
            self._send_json(result)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        # CPU TEXT ENDPOINTS
        if self.path == "/score":
            text = data.get("text", "")
            context = data.get("context", "general")
            source = data.get("source", "direct")  # Track source: direct, hooked, logged, warming

            start_time = time.perf_counter()
            result = score_importance_fast(text, context)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Track by source category
            if source in _source_stats:
                with _stats_lock:
                    _source_stats[source]["count"] += 1
                    _source_stats[source]["latency_ms"] += latency_ms

            self._send_json(result)

        elif self.path == "/classify":
            text = data.get("text", "")
            result = classify_intent_fast(text)
            self._send_json(result)

        # TPU IMAGE ENDPOINTS
        elif self.path == "/image_classify":
            image_path = data.get("image_path", "")
            top_k = data.get("top_k", 5)
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = classify_image_tpu(image_path, top_k)
            self._send_json(result)

        elif self.path == "/image_score":
            image_path = data.get("image_path", "")
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = score_image_importance(image_path)
            self._send_json(result)

        elif self.path == "/image_embed":
            image_path = data.get("image_path", "")
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = get_visual_embedding(image_path)
            self._send_json(result)

        # POSE ESTIMATION (TPU)
        elif self.path == "/pose_estimate":
            image_path = data.get("image_path", "")
            model = data.get("model", "movenet")
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = estimate_pose_tpu(image_path, model)
            self._send_json(result)

        # OBJECT DETECTION (TPU)
        elif self.path == "/detect_objects":
            image_path = data.get("image_path", "")
            threshold = data.get("threshold", 0.4)
            max_detections = data.get("max_detections", 10)
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = detect_objects_tpu(image_path, threshold, max_detections)
            self._send_json(result)

        # SEMANTIC SEGMENTATION (TPU)
        elif self.path == "/segment_image":
            image_path = data.get("image_path", "")
            return_mask = data.get("return_mask", False)
            if not image_path:
                self._send_json({"error": "image_path required"}, 400)
                return
            result = segment_image_tpu(image_path, return_mask)
            self._send_json(result)

        # AUDIO CLASSIFICATION (TPU)
        elif self.path == "/classify_audio":
            audio_path = data.get("audio_path", "")
            top_k = data.get("top_k", 5)
            if not audio_path:
                self._send_json({"error": "audio_path required"}, 400)
                return
            result = classify_audio_tpu(audio_path, top_k)
            self._send_json(result)

        # MODEL MANAGEMENT
        elif self.path == "/reload":
            # Force reload all models
            global _text_model_loaded, _tpu_available
            _text_model_loaded = False
            _tpu_available = False
            text_ok = load_text_model()
            tpu_ok = load_tpu_model()
            self._send_json({
                "text_model_reloaded": text_ok,
                "tpu_reloaded": tpu_ok
            })

        elif self.path == "/reload_tpu":
            # Reload only TPU (uses global from /reload handler above)
            _tpu_available = False
            success = load_tpu_model()
            self._send_json({"tpu_reloaded": success, "tpu_available": _tpu_available})

        else:
            self._send_json({"error": "Unknown endpoint"}, 404)


_start_time = time.time()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Thread-per-request HTTP server for concurrent Claude Code sessions."""
    allow_reuse_address = True
    daemon_threads = True  # Clean up threads on shutdown


def run_server():
    """Run the HTTP server."""
    server = ThreadedHTTPServer((HOST, PORT), TPUWarmHandler)
    logger.info(f"TPU Warm Service started on {HOST}:{PORT}")

    # Handle graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("Shutting down...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    server.serve_forever()


def main():
    """Main entry point."""
    logger.info("Starting Hybrid TPU + CPU Warm Service...")
    logger.info(f"  CPU text: SentenceTransformer (all-MiniLM-L6-v2)")
    logger.info(f"  TPU image: Coral Edge TPU ({_tpu_default_model})")

    # Pre-load both models at startup
    load_all_models()

    # Start HTTP server
    run_server()


if __name__ == "__main__":
    main()
