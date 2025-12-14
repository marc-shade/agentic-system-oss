#!/usr/bin/env python3
"""
TPU Importance Scoring Module
=============================

Uses TPU Warm Service for fast importance scoring (~30ms vs 7000ms cold start).

ARCHITECTURE: Calls local HTTP service (tpu-warm on port 8767) which keeps
the SentenceTransformer model warm in memory. Falls back to fast heuristics
if service unavailable - NEVER blocks on model loading.

Features:
- Fast inference via warm service (~30ms)
- Never blocks on model loading (critical for hooks)
- Graceful fallback to heuristics when service unavailable
- Score importance of text content
- Intent classification
- Anomaly detection

Usage:
    from tpu_importance import score_importance, is_tpu_available

    # Always fast - uses warm service or heuristics
    score = score_importance("User discovered critical bug in auth system")
    if score > 0.7:
        store_as_high_priority(memory)
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple

# Configure logging - minimal output
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("tpu_importance")

# TPU Warm Service endpoint
TPU_WARM_HOST = os.environ.get("TPU_WARM_HOST", "127.0.0.1")
TPU_WARM_PORT = int(os.environ.get("TPU_WARM_PORT", 8780))
TPU_WARM_URL = f"http://{TPU_WARM_HOST}:{TPU_WARM_PORT}"
TPU_WARM_TIMEOUT = 0.3  # 300ms max - hooks must be fast

# Service availability - cached after first check
_SERVICE_CHECKED = False
_SERVICE_AVAILABLE = False


def _check_service_available() -> bool:
    """Check if TPU Warm Service is available (fast check)."""
    global _SERVICE_CHECKED, _SERVICE_AVAILABLE

    if _SERVICE_CHECKED:
        return _SERVICE_AVAILABLE

    _SERVICE_CHECKED = True

    try:
        req = urllib.request.Request(f"{TPU_WARM_URL}/health")
        with urllib.request.urlopen(req, timeout=0.2) as resp:
            data = json.loads(resp.read().decode())
            _SERVICE_AVAILABLE = data.get("status") == "healthy"
            if _SERVICE_AVAILABLE:
                logger.info("TPU Warm Service available")
            return _SERVICE_AVAILABLE
    except Exception:
        _SERVICE_AVAILABLE = False
        return False


def is_tpu_available() -> bool:
    """Check if TPU scoring is available (via warm service)."""
    return _check_service_available()


def _call_warm_service(endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call TPU Warm Service endpoint.

    Args:
        endpoint: API endpoint (/score, /classify, etc.)
        data: Request data dict

    Returns:
        Response dict or None if failed
    """
    try:
        req = urllib.request.Request(
            f"{TPU_WARM_URL}{endpoint}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=TPU_WARM_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError:
        return None
    except Exception as e:
        logger.debug(f"Warm service call failed: {e}")
        return None


def _heuristic_importance(text: str, context: str) -> float:
    """
    Fast heuristic scoring (~0.1ms) when warm service unavailable.

    Uses keyword matching and text features for instant scoring.
    """
    score = 0.3  # Base score
    text_lower = text.lower()

    # High importance keywords (critical for system)
    high_keywords = [
        "error", "critical", "fail", "security", "bug", "fix",
        "important", "urgent", "breaking", "production", "crash",
        "vulnerability", "exploit", "emergency", "data loss"
    ]
    for kw in high_keywords:
        if kw in text_lower:
            score += 0.12

    # Medium importance keywords
    med_keywords = [
        "update", "change", "modify", "create", "delete", "config",
        "warning", "issue", "problem", "todo", "fixme", "hack"
    ]
    for kw in med_keywords:
        if kw in text_lower:
            score += 0.06

    # Context-specific boosts
    context_boosts = {
        "action": 0.1,    # Actions are generally important
        "memory": 0.05,   # Memories baseline
        "event": 0.08,    # Events notable
        "session": 0.05,  # Session events
        "tool": 0.07      # Tool usage
    }
    score += context_boosts.get(context, 0)

    # Length factor (more detail = potentially more important)
    if len(text) > 300:
        score += 0.08
    elif len(text) > 150:
        score += 0.04

    # Cap at 1.0
    return min(1.0, max(0.0, score))


def score_importance(text: str, context: str = "memory", source: str = "hooked") -> float:
    """
    Score the importance of text content.

    Uses TPU Warm Service when available (~30ms), falls back to
    instant heuristics (~0.1ms) when unavailable.

    Args:
        text: Content to score
        context: Context type (memory, action, event, session, tool)
        source: Call source for XRG tracking (direct, hooked, logged, warming)

    Returns:
        Importance score from 0.0 (low) to 1.0 (critical)
    """
    if not text:
        return 0.0

    # Try warm service first (fast if available)
    if _check_service_available():
        result = _call_warm_service("/score", {
            "text": text,
            "context": context,
            "source": source
        })
        if result and "importance_score" in result:
            return float(result["importance_score"])

    # Fallback to instant heuristics
    return _heuristic_importance(text, context)


def score_action_outcome(tool_name: str, outcome: str, success: bool = True) -> float:
    """
    Score importance of an action outcome for learning.

    Args:
        tool_name: Name of tool used
        outcome: Description of outcome
        success: Whether action succeeded

    Returns:
        Importance score 0.0-1.0
    """
    # Build description
    status = "succeeded" if success else "failed"
    description = f"{tool_name} {status}: {outcome}"

    # Failures are often more important to learn from
    base_score = score_importance(description, "action")

    if not success:
        base_score = min(1.0, base_score + 0.2)  # Boost failures

    return base_score


def classify_intent(text: str) -> Dict[str, Any]:
    """
    Classify user intent for command routing.

    Uses TPU Warm Service for semantic classification when available,
    falls back to keyword matching.

    Args:
        text: User input text to classify

    Returns:
        Dict with intent, confidence, method
    """
    if not text:
        return {"intent": "general", "confidence": 0.0, "method": "empty"}

    # Try warm service first
    if _check_service_available():
        result = _call_warm_service("/classify", {"text": text})
        if result and "intent" in result:
            return result

    # Fallback to keyword classification
    text_lower = text.lower()

    intent_keywords = {
        "code": ["write", "implement", "function", "class", "method", "code", "program"],
        "debug": ["fix", "bug", "error", "debug", "issue", "crash", "fail"],
        "research": ["find", "search", "look", "what is", "how does", "explain"],
        "system": ["config", "setup", "install", "service", "systemctl", "docker"],
        "file": ["read", "write", "edit", "create", "delete", "file", "directory"]
    }

    best_intent = "general"
    best_count = 0

    for intent, keywords in intent_keywords.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_intent = intent

    confidence = min(1.0, best_count * 0.2) if best_count > 0 else 0.3

    return {
        "intent": best_intent,
        "confidence": confidence,
        "method": "heuristic"
    }


def detect_anomaly(text: str, baseline_context: str = None) -> Tuple[bool, float]:
    """
    Detect if content is anomalous/unusual.

    Args:
        text: Content to analyze
        baseline_context: Optional baseline for comparison

    Returns:
        Tuple of (is_anomaly, confidence)
    """
    # Simple heuristic - look for unusual patterns
    anomaly_indicators = [
        "unexpected", "unusual", "strange", "weird", "never seen",
        "first time", "anomaly", "outlier", "abnormal"
    ]

    text_lower = text.lower()
    matches = sum(1 for ind in anomaly_indicators if ind in text_lower)

    if matches >= 2:
        return (True, min(1.0, matches * 0.3))
    elif matches == 1:
        return (True, 0.4)
    else:
        return (False, 0.1)


def embed_text(text: str) -> Optional[list]:
    """
    Generate text embedding using TPU Warm Service.

    Note: Embeddings require warm service - no heuristic fallback.

    Args:
        text: Text to embed

    Returns:
        Embedding vector or None if service unavailable
    """
    if not _check_service_available():
        return None

    # Embedding would need to be added to warm service
    # For now, return None to indicate unavailable
    return None


# =============================================================================
# TPU IMAGE FUNCTIONS (Real Coral Edge TPU)
# =============================================================================

def classify_image(image_path: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Classify image using real Coral Edge TPU (~2ms inference).

    Uses TPU Warm Service which keeps TPU model warm in memory.

    Args:
        image_path: Path to image file
        top_k: Number of top predictions to return

    Returns:
        Dict with predictions, latency_ms, device
    """
    if not _check_service_available():
        return {
            "predictions": [],
            "method": "unavailable",
            "error": "Service unavailable"
        }

    result = _call_warm_service("/image_classify", {
        "image_path": image_path,
        "top_k": top_k
    })

    if result:
        return result

    return {
        "predictions": [],
        "method": "error",
        "error": "Service call failed"
    }


def score_image_importance(image_path: str) -> float:
    """
    Score image importance using TPU classification results.

    Uses real TPU when available, returns neutral score on failure.

    Args:
        image_path: Path to image file

    Returns:
        Importance score from 0.0 (low) to 1.0 (critical)
    """
    if not _check_service_available():
        return 0.3  # Neutral score when unavailable

    result = _call_warm_service("/image_score", {
        "image_path": image_path
    })

    if result and "importance_score" in result:
        return float(result["importance_score"])

    return 0.3  # Neutral score on error


def get_visual_embedding(image_path: str) -> Optional[list]:
    """
    Extract visual embeddings from image using TPU.

    Args:
        image_path: Path to image file

    Returns:
        Embedding vector or None if unavailable
    """
    if not _check_service_available():
        return None

    result = _call_warm_service("/image_embed", {
        "image_path": image_path
    })

    if result and "embedding" in result:
        return result["embedding"]

    return None


def is_tpu_image_available() -> bool:
    """Check if TPU image classification is available."""
    if not _check_service_available():
        return False

    try:
        req = urllib.request.Request(f"{TPU_WARM_URL}/status")
        with urllib.request.urlopen(req, timeout=0.3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("tpu", {}).get("available", False)
    except Exception:
        return False


# =============================================================================
# POSE ESTIMATION (Real Coral Edge TPU)
# =============================================================================

def estimate_pose(image_path: str, model: str = "movenet") -> Dict[str, Any]:
    """
    Estimate human pose from image using TPU (~30ms inference).

    Returns 17 COCO keypoints: nose, eyes, ears, shoulders, elbows,
    wrists, hips, knees, ankles.

    Args:
        image_path: Path to image file
        model: Pose model - "movenet" (fast) or "posenet_353" (accurate)

    Returns:
        Dict with keypoints list, each containing name, x, y, confidence
    """
    if not _check_service_available():
        return {
            "keypoints": [],
            "method": "unavailable",
            "error": "Service unavailable"
        }

    result = _call_warm_service("/pose_estimate", {
        "image_path": image_path,
        "model": model
    })

    if result:
        return result

    return {
        "keypoints": [],
        "method": "error",
        "error": "Service call failed"
    }


# =============================================================================
# OBJECT DETECTION (Real Coral Edge TPU)
# =============================================================================

def detect_objects(image_path: str, threshold: float = 0.4, max_detections: int = 10) -> Dict[str, Any]:
    """
    Detect objects in image using TPU SSD model (~30ms inference).

    Detects 90 COCO classes: person, bicycle, car, motorcycle, airplane,
    bus, train, truck, boat, traffic light, fire hydrant, stop sign, etc.

    Args:
        image_path: Path to image file
        threshold: Minimum confidence threshold (0.0-1.0)
        max_detections: Maximum number of detections to return

    Returns:
        Dict with detections list, each containing label, class_id,
        confidence, bbox (xmin, ymin, xmax, ymax)
    """
    if not _check_service_available():
        return {
            "detections": [],
            "method": "unavailable",
            "error": "Service unavailable"
        }

    result = _call_warm_service("/detect_objects", {
        "image_path": image_path,
        "threshold": threshold,
        "max_detections": max_detections
    })

    if result:
        return result

    return {
        "detections": [],
        "method": "error",
        "error": "Service call failed"
    }


# =============================================================================
# SEMANTIC SEGMENTATION (Real Coral Edge TPU)
# =============================================================================

def segment_image(image_path: str, return_mask: bool = False) -> Dict[str, Any]:
    """
    Perform semantic segmentation using DeepLab v3 TPU model (~50ms inference).

    Segments 21 Pascal VOC classes: background, aeroplane, bicycle, bird,
    boat, bottle, bus, car, cat, chair, cow, diningtable, dog, horse,
    motorbike, person, pottedplant, sheep, sofa, train, tvmonitor.

    Args:
        image_path: Path to image file
        return_mask: If True, include full segmentation mask in response

    Returns:
        Dict with class_distribution (percentage per class),
        optionally segmentation_mask
    """
    if not _check_service_available():
        return {
            "class_distribution": {},
            "method": "unavailable",
            "error": "Service unavailable"
        }

    result = _call_warm_service("/segment_image", {
        "image_path": image_path,
        "return_mask": return_mask
    })

    if result:
        return result

    return {
        "class_distribution": {},
        "method": "error",
        "error": "Service call failed"
    }


# =============================================================================
# AUDIO CLASSIFICATION (Real Coral Edge TPU)
# =============================================================================

def classify_audio(audio_path: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Classify audio/sounds using YamNet TPU model (~50ms inference).

    Recognizes 520+ sound classes including speech, music, animals,
    vehicles, nature sounds, household sounds, and more.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        top_k: Number of top predictions to return

    Returns:
        Dict with predictions list, each containing label, class_id, confidence

    Note: Requires librosa for audio processing.
    """
    if not _check_service_available():
        return {
            "predictions": [],
            "method": "unavailable",
            "error": "Service unavailable"
        }

    result = _call_warm_service("/classify_audio", {
        "audio_path": audio_path,
        "top_k": top_k
    })

    if result:
        return result

    return {
        "predictions": [],
        "method": "error",
        "error": "Service call failed"
    }


# =============================================================================
# MODEL MANAGEMENT
# =============================================================================

def list_models() -> Dict[str, Any]:
    """
    List all available TPU models grouped by category.

    Returns:
        Dict with models_by_category and summary (total, installed, loaded)
    """
    if not _check_service_available():
        return {
            "models_by_category": {},
            "summary": {"total_models": 0, "installed": 0, "loaded": 0, "tpu_available": False}
        }

    try:
        req = urllib.request.Request(f"{TPU_WARM_URL}/list_models")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {
            "models_by_category": {},
            "summary": {"error": str(e)}
        }


# Convenience function for quick checks
def get_service_status() -> Dict[str, Any]:
    """Get TPU Warm Service status."""
    if not _check_service_available():
        return {
            "available": False,
            "service_url": TPU_WARM_URL,
            "fallback": "heuristics"
        }

    try:
        req = urllib.request.Request(f"{TPU_WARM_URL}/health")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            data = json.loads(resp.read().decode())
            data["available"] = True
            data["service_url"] = TPU_WARM_URL
            return data
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "service_url": TPU_WARM_URL,
            "fallback": "heuristics"
        }


# CLI interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TPU Hybrid Importance Scoring (CPU text + TPU images)")
    parser.add_argument("--text", "-t", help="Text to score (CPU)")
    parser.add_argument("--image", "-i", help="Image path to classify (TPU)")
    parser.add_argument("--context", "-c", default="general", help="Context type for text")
    parser.add_argument("--status", "-s", action="store_true", help="Show service status")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of top predictions for image")

    args = parser.parse_args()

    if args.status:
        status = get_service_status()
        print(json.dumps(status, indent=2))
    elif args.image:
        # TPU image classification
        print(f"Classifying image: {args.image}")
        result = classify_image(args.image, args.top_k)
        print(json.dumps({
            "image": args.image,
            "tpu_available": is_tpu_image_available(),
            "classification": result,
            "importance_score": score_image_importance(args.image)
        }, indent=2))
    elif args.text:
        # CPU text scoring
        score = score_importance(args.text, args.context)
        intent = classify_intent(args.text)
        print(json.dumps({
            "text": args.text[:100],
            "importance_score": score,
            "intent": intent,
            "service_available": is_tpu_available()
        }, indent=2))
    else:
        # Quick status test
        print("=== TPU Hybrid Service Status ===")
        print(f"Service available: {is_tpu_available()}")
        print(f"TPU image available: {is_tpu_image_available()}")
        print(f"Text test score: {score_importance('test content', 'action')}")
        print("\nUsage:")
        print("  --text 'your text'      Score text importance (CPU)")
        print("  --image /path/to/img    Classify image (TPU)")
        print("  --status                Show detailed status")
