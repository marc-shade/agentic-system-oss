#!/usr/bin/env python3
"""
TPU Cluster Client - Access macpro51's Coral TPU from any cluster node.

This client provides a simple interface to use the shared TPU service
over the network, similar to how Ollama is accessed.

Usage:
    from tpu_cluster_client import TPUClient

    # Auto-discover via Avahi or use explicit host
    client = TPUClient()  # Auto-discovers via Avahi
    client = TPUClient(host="macpro51.local", port=8780)  # Explicit

    # Text scoring (uses CPU SentenceTransformer on TPU node)
    score = client.score_text("implement new authentication system")

    # Text intent classification
    intent = client.classify_intent("fix the bug in login")

    # Image classification (uses real Coral TPU!)
    result = client.classify_image("/path/to/image.jpg")

    # Object detection
    objects = client.detect_objects("/path/to/image.jpg")

    # Pose estimation
    pose = client.estimate_pose("/path/to/person.jpg")

    # Audio classification
    sounds = client.classify_audio("/path/to/audio.wav")
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tpu_cluster_client")


class TPUClient:
    """
    Client for accessing the cluster's shared Coral TPU service.

    Auto-discovers the TPU service via Avahi/mDNS or uses explicit host.
    Falls back to localhost if running on the TPU host node (macpro51).
    """

    def __init__(self, host: Optional[str] = None, port: int = 8780, timeout: float = 5.0):
        """
        Initialize TPU client.

        Args:
            host: TPU service host (auto-discovers via Avahi if None)
            port: TPU service port (default 8780)
            timeout: Request timeout in seconds
        """
        self.port = port
        self.timeout = timeout
        self._discovered_host = None

        if host:
            self.host = host
        else:
            self.host = self._discover_tpu_service()

        self.base_url = f"http://{self.host}:{self.port}"
        logger.info(f"TPU Client initialized: {self.base_url}")

    def _discover_tpu_service(self) -> str:
        """
        Discover TPU service via Avahi/mDNS.

        Returns:
            Discovered host or fallback to localhost
        """
        # Check if we're on the TPU host
        hostname = os.uname().nodename
        if hostname == "macpro51":
            logger.info("Running on TPU host - using localhost")
            return "127.0.0.1"

        # Try Avahi discovery
        try:
            result = subprocess.run(
                ["avahi-browse", "-rpt", "_tpu-inference._tcp"],
                capture_output=True, text=True, timeout=3
            )

            for line in result.stdout.split('\n'):
                if line.startswith('=') and 'IPv4' in line:
                    parts = line.split(';')
                    if len(parts) >= 8:
                        ip = parts[7]
                        if ip and not ip.startswith('fe80'):  # Skip IPv6 link-local
                            logger.info(f"Discovered TPU service at {ip}")
                            self._discovered_host = ip
                            return ip
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try known hostnames
        for hostname in ["macpro51.local", "macpro51", "192.168.2.50"]:
            try:
                url = f"http://{hostname}:{self.port}/health"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=1) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("status") == "healthy":
                        logger.info(f"Found TPU service at {hostname}")
                        return hostname
            except Exception:
                continue

        # Fallback to localhost (will fail if not on TPU host)
        logger.warning("Could not discover TPU service - trying localhost")
        return "127.0.0.1"

    def _request(self, endpoint: str, data: Optional[Dict] = None,
                 method: str = "POST") -> Optional[Dict]:
        """Make HTTP request to TPU service."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                req = urllib.request.Request(url)
            else:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode() if data else None,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def health(self) -> Dict[str, Any]:
        """Check TPU service health."""
        result = self._request("/health", method="GET")
        return result or {"status": "unavailable"}

    def status(self) -> Dict[str, Any]:
        """Get detailed TPU service status."""
        result = self._request("/status", method="GET")
        return result or {"status": "unavailable"}

    def list_models(self) -> Dict[str, Any]:
        """List available TPU models."""
        result = self._request("/list_models", method="GET")
        return result or {"models_by_category": {}}

    # === TEXT OPERATIONS (CPU on TPU node) ===

    def score_text(self, text: str, context: str = "action") -> float:
        """
        Score importance of text content.

        Args:
            text: Text to score
            context: Context type (action, memory, event)

        Returns:
            Importance score 0.0-1.0
        """
        result = self._request("/score", {
            "text": text[:500],
            "context": context
        })

        if result and "importance_score" in result:
            return float(result["importance_score"])
        return 0.5

    def classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Classify user intent from text.

        Args:
            text: Text to classify

        Returns:
            Dict with intent, confidence, method
        """
        result = self._request("/classify", {"text": text[:300]})

        if result and "intent" in result:
            return result
        return {"intent": "general", "confidence": 0.5, "method": "error"}

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate text embedding vector.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None
        """
        result = self._request("/embed", {"text": text[:1000]})

        if result and "embedding" in result:
            return result["embedding"]
        return None

    # === IMAGE OPERATIONS (Real Coral TPU) ===

    def classify_image(self, image_path: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Classify image using Coral TPU (~2ms inference).

        Args:
            image_path: Path to image file
            top_k: Number of top predictions

        Returns:
            Dict with predictions, latency_ms, device
        """
        # For remote nodes, we need to send the image data
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}

        # Check if we're on the TPU host (can use path directly)
        if self.host in ["127.0.0.1", "localhost", "macpro51", "macpro51.local"]:
            result = self._request("/image_classify", {
                "image_path": image_path,
                "top_k": top_k
            })
        else:
            # Send image as base64 for remote nodes
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            result = self._request("/image_classify", {
                "image_data": image_data,
                "top_k": top_k
            })

        return result or {"predictions": [], "error": "Request failed"}

    def detect_objects(self, image_path: str, threshold: float = 0.4,
                       max_detections: int = 10) -> Dict[str, Any]:
        """
        Detect objects in image using TPU SSD model (~30ms).

        Args:
            image_path: Path to image file
            threshold: Confidence threshold
            max_detections: Max detections to return

        Returns:
            Dict with detections list
        """
        result = self._request("/detect_objects", {
            "image_path": image_path,
            "threshold": threshold,
            "max_detections": max_detections
        })

        return result or {"detections": [], "error": "Request failed"}

    def estimate_pose(self, image_path: str, model: str = "movenet") -> Dict[str, Any]:
        """
        Estimate human pose from image using TPU (~30ms).

        Args:
            image_path: Path to image file
            model: Pose model (movenet or posenet_353)

        Returns:
            Dict with 17 keypoints
        """
        result = self._request("/pose_estimate", {
            "image_path": image_path,
            "model": model
        })

        return result or {"keypoints": [], "error": "Request failed"}

    def segment_image(self, image_path: str, return_mask: bool = False) -> Dict[str, Any]:
        """
        Semantic segmentation using DeepLab v3 TPU (~50ms).

        Args:
            image_path: Path to image file
            return_mask: Include full segmentation mask

        Returns:
            Dict with class_distribution
        """
        result = self._request("/segment_image", {
            "image_path": image_path,
            "return_mask": return_mask
        })

        return result or {"class_distribution": {}, "error": "Request failed"}

    def classify_audio(self, audio_path: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Classify audio/sounds using YamNet TPU (~50ms).

        Args:
            audio_path: Path to audio file
            top_k: Number of top predictions

        Returns:
            Dict with 520+ sound class predictions
        """
        result = self._request("/classify_audio", {
            "audio_path": audio_path,
            "top_k": top_k
        })

        return result or {"predictions": [], "error": "Request failed"}


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TPU Cluster Client")
    parser.add_argument("--host", help="TPU service host (auto-discovers if not set)")
    parser.add_argument("--port", type=int, default=8780, help="TPU service port")
    parser.add_argument("--health", action="store_true", help="Check service health")
    parser.add_argument("--status", action="store_true", help="Get detailed status")
    parser.add_argument("--models", action="store_true", help="List available models")
    parser.add_argument("--score", help="Score text importance")
    parser.add_argument("--classify", help="Classify text intent")
    parser.add_argument("--image", help="Classify image")
    parser.add_argument("--detect", help="Detect objects in image")
    parser.add_argument("--pose", help="Estimate pose in image")
    parser.add_argument("--audio", help="Classify audio")

    args = parser.parse_args()

    client = TPUClient(host=args.host, port=args.port)

    if args.health:
        print(json.dumps(client.health(), indent=2))
    elif args.status:
        print(json.dumps(client.status(), indent=2))
    elif args.models:
        print(json.dumps(client.list_models(), indent=2))
    elif args.score:
        score = client.score_text(args.score)
        print(f"Importance score: {score}")
    elif args.classify:
        intent = client.classify_intent(args.classify)
        print(json.dumps(intent, indent=2))
    elif args.image:
        result = client.classify_image(args.image)
        print(json.dumps(result, indent=2))
    elif args.detect:
        result = client.detect_objects(args.detect)
        print(json.dumps(result, indent=2))
    elif args.pose:
        result = client.estimate_pose(args.pose)
        print(json.dumps(result, indent=2))
    elif args.audio:
        result = client.classify_audio(args.audio)
        print(json.dumps(result, indent=2))
    else:
        print("TPU Cluster Client")
        print(f"Service: {client.base_url}")
        print(f"Health: {client.health().get('status')}")
        print("\nUse --help for options")
