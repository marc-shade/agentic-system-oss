#!/usr/bin/env python3
"""
Visual Intelligence - Unified Vision Understanding for Cluster AGI

This module provides a unified interface for visual scene understanding,
orchestrating multiple backends (Claude API, Ollama vision models) with
automatic failover and caching.

Architecture:
1. Try Claude API (most reliable, highest quality)
2. Fall back to Ollama vision models (local, faster for bulk)
3. Cache results to avoid redundant API calls
4. Store all analyses in cluster database for awareness

Features:
- Multi-backend vision analysis with automatic failover
- Result caching to reduce API costs
- Cluster-wide visual awareness aggregation
- Integration with memory system for persistent learning
"""
import platform

import json
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib

# Try to import TPU for fast preprocessing
try:
    from tpu_visual_inference import TPUVisualInference
    _HAS_TPU = True
except ImportError:
    _HAS_TPU = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visual_intelligence")

# Configuration
STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
CACHE_TTL_MINUTES = 30  # Don't re-analyze same image within 30 min


class VisualIntelligence:
    """
    Unified visual understanding with multi-backend support
    """

    def __init__(self, prefer_local: bool = False, use_tpu_preprocessing: bool = True):
        """
        Initialize visual intelligence

        Args:
            prefer_local: If True, try Ollama first before Claude
            use_tpu_preprocessing: If True, use TPU for fast preprocessing before LLM
        """
        self.prefer_local = prefer_local
        self.use_tpu_preprocessing = use_tpu_preprocessing
        self._claude_analyzer = None
        self._ollama_reasoner = None
        self._tpu = None
        self._init_backends()
        self._ensure_tables()

    def _init_backends(self):
        """Initialize available backends"""
        # TPU preprocessing backend (fast detection before LLM analysis)
        if self.use_tpu_preprocessing and _HAS_TPU:
            try:
                self._tpu = TPUVisualInference()
                if self._tpu.is_available:
                    logger.info("TPU preprocessing backend available (~15ms inference)")
                else:
                    self._tpu = None
                    logger.info("TPU preprocessing unavailable (hardware not found)")
            except Exception as e:
                logger.warning(f"TPU initialization failed: {e}")
                self._tpu = None

        # Claude backend
        try:
            from claude_visual_analyzer import ClaudeVisualAnalyzer
            self._claude_analyzer = ClaudeVisualAnalyzer()
            if self._claude_analyzer.api_key:
                logger.info("Claude visual backend available")
            else:
                self._claude_analyzer = None
                logger.info("Claude backend unavailable (no API key)")
        except ImportError:
            logger.info("Claude visual analyzer not available")

        # Ollama backend
        try:
            from visual_reasoning import VisualReasoner
            self._ollama_reasoner = VisualReasoner()
            if self._ollama_reasoner.available_model:
                logger.info(f"Ollama visual backend available ({self._ollama_reasoner.available_model})")
            else:
                self._ollama_reasoner = None
                logger.info("Ollama backend unavailable (no vision model)")
        except ImportError:
            logger.info("Ollama visual reasoner not available")

    def _tpu_preprocess(self, image_path: str) -> Dict[str, Any]:
        """
        Run fast TPU preprocessing on image before LLM analysis.

        Returns detection results that can augment LLM context.
        """
        if not self._tpu:
            return {}

        try:
            import cv2
            frame = cv2.imread(image_path)
            if frame is None:
                return {}

            result = {
                "tpu_preprocessing": True,
                "detections": {}
            }

            # Fast face detection (~15ms)
            faces = self._tpu.detect_faces(frame, threshold=0.5)
            if faces:
                result["detections"]["faces"] = {
                    "count": len(faces),
                    "details": [
                        {"confidence": f["confidence"], "bbox": f["bbox"]}
                        for f in faces[:5]  # Top 5 faces
                    ]
                }

            # Fast object detection (~20ms)
            objects = self._tpu.detect_objects(frame, threshold=0.4)
            if objects:
                result["detections"]["objects"] = [
                    {"label": o["label"], "confidence": o["confidence"]}
                    for o in objects[:10]  # Top 10 objects
                ]

            # Scene classification (~15ms)
            scene = self._tpu.classify_scene(frame, top_k=3)
            if scene:
                result["detections"]["scene"] = {
                    "top_label": scene[0]["label"],
                    "confidence": scene[0]["confidence"],
                    "alternatives": [
                        {"label": s["label"], "confidence": s["confidence"]}
                        for s in scene[1:3]
                    ]
                }

            # Get TPU stats
            stats = self._tpu.get_stats()
            result["tpu_stats"] = {
                "total_inferences": stats.get("total_inferences", 0),
                "avg_latency_ms": stats.get("avg_latency_ms", 0)
            }

            logger.debug(f"TPU preprocessing complete: {len(faces)} faces, {len(objects)} objects")
            return result

        except Exception as e:
            logger.warning(f"TPU preprocessing failed: {e}")
            return {}

    def _build_tpu_context(self, tpu_result: Dict[str, Any]) -> str:
        """Build context string from TPU detection results for LLM."""
        if not tpu_result or not tpu_result.get("detections"):
            return ""

        parts = ["[TPU Pre-analysis]"]
        detections = tpu_result["detections"]

        if "faces" in detections:
            face_info = detections["faces"]
            parts.append(f"Faces detected: {face_info['count']}")

        if "objects" in detections:
            objects = detections["objects"]
            obj_labels = [f"{o['label']} ({o['confidence']:.0%})" for o in objects[:5]]
            parts.append(f"Objects: {', '.join(obj_labels)}")

        if "scene" in detections:
            scene_info = detections["scene"]
            parts.append(f"Scene type: {scene_info['top_label']} ({scene_info['confidence']:.0%})")

        return " | ".join(parts)

    def _ensure_tables(self):
        """Ensure database tables exist"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visual_intelligence_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT UNIQUE,
                    image_path TEXT,
                    analysis_json TEXT,
                    backend TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visual_awareness_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    node_id TEXT,
                    scene TEXT,
                    people TEXT,
                    activity TEXT,
                    lighting TEXT,
                    mood TEXT,
                    person_present INTEGER,
                    summary TEXT,
                    backend TEXT,
                    significance REAL DEFAULT 0.5
                )
            ''')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to ensure tables: {e}")

    def _get_image_hash(self, image_path: str) -> str:
        """Get hash of image for caching"""
        try:
            with open(image_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return hashlib.md5(image_path.encode()).hexdigest()

    def _check_cache(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Check if we have a cached analysis"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT analysis_json FROM visual_intelligence_cache
                WHERE image_hash = ? AND expires_at > ?
            ''', (image_hash, datetime.now().isoformat()))

            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
        return None

    def _store_cache(self, image_hash: str, image_path: str,
                     analysis: Dict[str, Any], backend: str):
        """Store analysis in cache"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            expires = (datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)).isoformat()

            cursor.execute('''
                INSERT OR REPLACE INTO visual_intelligence_cache
                (image_hash, image_path, analysis_json, backend, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (image_hash, image_path, json.dumps(analysis), backend, expires))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Cache store failed: {e}")

    def analyze(self, image_path: str, context: str = "",
                force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analyze an image using best available backend

        Args:
            image_path: Path to image file
            context: Optional context about the image
            force_refresh: Skip cache and re-analyze

        Returns:
            Analysis result with scene understanding
        """
        # Check cache first
        image_hash = self._get_image_hash(image_path)
        if not force_refresh:
            cached = self._check_cache(image_hash)
            if cached:
                cached["from_cache"] = True
                return cached

        # Run TPU preprocessing for fast detection (~50ms total)
        tpu_result = {}
        if self._tpu:
            logger.info(f"Running TPU preprocessing for {image_path}")
            tpu_result = self._tpu_preprocess(image_path)
            if tpu_result:
                logger.info(f"TPU detected: {len(tpu_result.get('detections', {}).get('objects', []))} objects")

        # Augment context with TPU detection results
        augmented_context = context
        if tpu_result:
            tpu_context = self._build_tpu_context(tpu_result)
            if tpu_context:
                augmented_context = f"{tpu_context}\n{context}" if context else tpu_context

        # Determine backend order
        if self.prefer_local:
            backends = [
                ("ollama", self._ollama_reasoner),
                ("claude", self._claude_analyzer)
            ]
        else:
            backends = [
                ("claude", self._claude_analyzer),
                ("ollama", self._ollama_reasoner)
            ]

        # Try each backend
        for backend_name, backend in backends:
            if backend is None:
                continue

            try:
                logger.info(f"Trying {backend_name} backend for {image_path}")
                result = backend.analyze_image(image_path, augmented_context)

                if result.get("success"):
                    result["backend"] = backend_name
                    result["from_cache"] = False

                    # Include TPU preprocessing results
                    if tpu_result:
                        result["tpu_preprocessing"] = tpu_result

                    # Store in cache
                    self._store_cache(image_hash, image_path, result, backend_name)

                    # Log to awareness
                    self._log_awareness(result)

                    return result
                else:
                    logger.warning(f"{backend_name} failed: {result.get('error')}")

            except Exception as e:
                logger.error(f"{backend_name} error: {e}")

        return {
            "error": "All backends failed",
            "success": False,
            "backends_tried": [b[0] for b in backends if b[1] is not None]
        }

    def _log_awareness(self, analysis: Dict[str, Any]):
        """Log analysis to awareness log"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Calculate significance
            significance = 0.3  # Base
            if analysis.get("person_present") or "person" in analysis.get("people", "").lower():
                significance += 0.4
            if analysis.get("activity"):
                significance += 0.2

            cursor.execute('''
                INSERT INTO visual_awareness_log
                (timestamp, node_id, scene, people, activity, lighting, mood,
                 person_present, summary, backend, significance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.get("timestamp", datetime.now().isoformat()),
                analysis.get("node_id"),
                analysis.get("scene"),
                analysis.get("people"),
                analysis.get("activity"),
                analysis.get("lighting"),
                analysis.get("mood"),
                1 if analysis.get("person_present") else 0,
                analysis.get("summary"),
                analysis.get("backend"),
                significance
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Awareness log failed: {e}")

    def get_cluster_awareness(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Get current visual awareness of the cluster

        Args:
            minutes: Look back period

        Returns:
            Cluster visual awareness summary
        """
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

            # Get latest per node
            cursor.execute('''
                SELECT node_id, timestamp, scene, people, lighting, mood,
                       person_present, summary, backend
                FROM visual_awareness_log
                WHERE timestamp > ? AND id IN (
                    SELECT MAX(id) FROM visual_awareness_log
                    WHERE timestamp > ?
                    GROUP BY node_id
                )
            ''', (cutoff, cutoff))

            nodes = {}
            for row in cursor.fetchall():
                if row[0]:  # node_id not null
                    nodes[row[0]] = {
                        "timestamp": row[1],
                        "scene": row[2],
                        "people": row[3],
                        "lighting": row[4],
                        "mood": row[5],
                        "person_present": bool(row[6]),
                        "summary": row[7],
                        "backend": row[8]
                    }

            conn.close()

            # Summarize
            person_locations = [n for n, d in nodes.items() if d.get("person_present")]

            return {
                "timestamp": datetime.now().isoformat(),
                "lookback_minutes": minutes,
                "nodes_reporting": list(nodes.keys()),
                "nodes_count": len(nodes),
                "person_detected_at": person_locations,
                "user_status": "present" if person_locations else "absent",
                "nodes": nodes,
                "summary": self._build_summary(nodes, person_locations)
            }

        except Exception as e:
            logger.error(f"Awareness query failed: {e}")
            return {"error": str(e)}

    def _build_summary(self, nodes: Dict, person_locations: List[str]) -> str:
        """Build human-readable awareness summary"""
        if not nodes:
            return "No visual observations available"

        parts = []

        # User location
        if not person_locations:
            parts.append("User not detected")
        elif len(person_locations) == 1:
            loc = person_locations[0]
            scene = nodes[loc].get("summary", nodes[loc].get("scene", ""))
            parts.append(f"User at {loc}: {scene}")
        else:
            parts.append(f"User detected at: {', '.join(person_locations)}")

        # Lighting summary
        lighting = [d.get("lighting", "unknown") for d in nodes.values()]
        dark_count = sum(1 for l in lighting if l and "dark" in l.lower())
        if dark_count > len(nodes) // 2:
            parts.append("Most areas are dark")

        return ". ".join(parts)

    def get_available_backends(self) -> Dict[str, bool]:
        """Return which backends are available"""
        return {
            "tpu_preprocessing": self._tpu is not None,
            "claude": self._claude_analyzer is not None,
            "ollama": self._ollama_reasoner is not None
        }


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


    parser = argparse.ArgumentParser(description="Visual Intelligence")
    parser.add_argument("--image", help="Analyze specific image")
    parser.add_argument("--context", default="", help="Context for analysis")
    parser.add_argument("--awareness", action="store_true", help="Show cluster awareness")
    parser.add_argument("--minutes", type=int, default=60, help="Lookback minutes")
    parser.add_argument("--prefer-local", action="store_true", help="Prefer Ollama over Claude")
    parser.add_argument("--backends", action="store_true", help="Show available backends")

    args = parser.parse_args()

    vi = VisualIntelligence(prefer_local=args.prefer_local)

    if args.backends:
        print("Available backends:")
        for name, available in vi.get_available_backends().items():
            status = "✓" if available else "✗"
            print(f"  {status} {name}")

    elif args.awareness:
        awareness = vi.get_cluster_awareness(args.minutes)
        print(json.dumps(awareness, indent=2))

    elif args.image:
        print(f"Analyzing: {args.image}")
        result = vi.analyze(args.image, args.context)
        print(json.dumps(result, indent=2))

    else:
        print("Visual Intelligence - Multi-backend Vision Understanding")
        print("\nBackends:")
        for name, available in vi.get_available_backends().items():
            status = "✓" if available else "✗"
            print(f"  {status} {name}")
        print("\nUsage:")
        print("  --image FILE     Analyze an image")
        print("  --awareness      Show cluster visual awareness")
        print("  --backends       Show available backends")


if __name__ == "__main__":
    main()
