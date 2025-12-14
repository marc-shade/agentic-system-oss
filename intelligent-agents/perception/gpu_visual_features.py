#!/usr/bin/env python3
"""
GPU Visual Feature Extraction - LVR Phase 3+

Offloads visual feature extraction to GPU node (completeu-server)
for richer CLIP-style embeddings than Edge TPU can provide.

Architecture:
    Edge TPU (macpro51)         GPU Node (completeu-server)
    ─────────────────────       ───────────────────────────
    Fast detection (15ms)       Deep features (50-100ms)
    1001-dim ImageNet logits    768/1024-dim CLIP embeddings
    Real-time processing        Memory consolidation

Use Cases:
    - TPU: Real-time perception, fast similarity
    - GPU: Deep semantic features, cross-modal alignment

Available Models on completeu-server:
    - moondream: 1B vision-language model with CLIP backbone
    - bge-m3: Multilingual embeddings (for text-image alignment)

Usage:
    from gpu_visual_features import GPUVisualFeatureExtractor

    # Initialize client
    extractor = GPUVisualFeatureExtractor()

    # Get rich visual embeddings
    features = extractor.extract_features("/path/to/image.jpg")

    # Get vision-language description
    description = extractor.describe_image("/path/to/image.jpg")

    # Batch processing for memory consolidation
    all_features = extractor.batch_extract([img1, img2, img3])
"""

import base64
import json
import logging
import requests
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger("gpu_visual_features")

# GPU node configuration
GPU_NODE_HOST = "completeu-server.local"
GPU_NODE_PORT = 11434
OLLAMA_API_BASE = f"http://{GPU_NODE_HOST}:{GPU_NODE_PORT}/api"

# Model configurations
VISION_MODEL = "moondream:latest"  # Vision-language model with CLIP
EMBED_MODEL = "bge-m3:latest"  # For text embeddings (cross-modal alignment)

# Timeouts
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 60.0  # Vision processing can take time


@dataclass
class VisualFeatures:
    """Container for extracted visual features."""
    description: str  # Natural language description
    embedding: Optional[np.ndarray]  # Feature vector if available
    objects: List[str]  # Detected objects
    scene: str  # Scene description
    confidence: float  # Overall confidence
    latency_ms: float  # Processing time
    model: str  # Model used


class GPUVisualFeatureExtractor:
    """
    GPU-based visual feature extraction via Ollama API.

    Connects to completeu-server to leverage moondream for
    rich visual understanding and CLIP-style embeddings.
    """

    def __init__(
        self,
        host: str = GPU_NODE_HOST,
        port: int = GPU_NODE_PORT,
        vision_model: str = VISION_MODEL,
        embed_model: str = EMBED_MODEL
    ):
        """
        Initialize GPU feature extractor.

        Args:
            host: GPU node hostname
            port: Ollama API port
            vision_model: Vision-language model name
            embed_model: Embedding model name
        """
        self.host = host
        self.port = port
        self.api_base = f"http://{host}:{port}/api"
        self.vision_model = vision_model
        self.embed_model = embed_model

        self._session = requests.Session()
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if GPU node is reachable."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Check GPU node connectivity."""
        try:
            resp = self._session.get(
                f"{self.api_base}/tags",
                timeout=CONNECT_TIMEOUT
            )
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"] for m in models]

                # Check if vision model is available
                vision_available = any(
                    self.vision_model.split(":")[0] in m
                    for m in model_names
                )

                if vision_available:
                    logger.info(f"GPU node available at {self.host}:{self.port}")
                    return True
                else:
                    logger.warning(f"Vision model {self.vision_model} not found")
                    return False
            return False
        except Exception as e:
            logger.warning(f"GPU node not reachable: {e}")
            return False

    def _encode_image(self, image_path: str) -> str:
        """Encode image as base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def describe_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail, including objects, scene, actions, and any text visible."
    ) -> Optional[Dict[str, Any]]:
        """
        Get natural language description of image.

        Args:
            image_path: Path to image file
            prompt: Description prompt

        Returns:
            Dict with description and metadata
        """
        if not self.is_available:
            logger.warning("GPU node not available")
            return None

        start_time = time.time()

        try:
            # Encode image
            image_b64 = self._encode_image(image_path)

            # Send to Ollama vision endpoint
            resp = self._session.post(
                f"{self.api_base}/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 256
                    }
                },
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )

            if resp.status_code != 200:
                logger.error(f"API error: {resp.status_code} - {resp.text}")
                return None

            result = resp.json()
            latency_ms = (time.time() - start_time) * 1000

            return {
                "description": result.get("response", ""),
                "model": self.vision_model,
                "latency_ms": latency_ms,
                "tokens": result.get("eval_count", 0),
                "image_path": image_path
            }

        except Exception as e:
            logger.error(f"Image description failed: {e}")
            return None

    def extract_features(
        self,
        image_path: str,
        include_description: bool = True
    ) -> Optional[VisualFeatures]:
        """
        Extract rich visual features from image.

        Uses vision-language model to understand image content
        and optionally generate embedding-style features.

        Args:
            image_path: Path to image file
            include_description: Generate text description

        Returns:
            VisualFeatures object with all extracted information
        """
        if not self.is_available:
            logger.warning("GPU node not available")
            return None

        start_time = time.time()

        try:
            # Multi-prompt extraction for structured features
            prompts = {
                "objects": "List the main objects in this image, separated by commas. Only list objects, nothing else.",
                "scene": "What type of scene or location is this? Answer in 2-3 words.",
                "description": "Describe this image concisely in one sentence."
            }

            results = {}

            for key, prompt in prompts.items():
                if key == "description" and not include_description:
                    continue

                resp = self._session.post(
                    f"{self.api_base}/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [self._encode_image(image_path)],
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 100
                        }
                    },
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                )

                if resp.status_code == 200:
                    results[key] = resp.json().get("response", "").strip()

            latency_ms = (time.time() - start_time) * 1000

            # Parse objects
            objects = []
            if "objects" in results:
                objects = [
                    o.strip()
                    for o in results["objects"].split(",")
                    if o.strip()
                ]

            return VisualFeatures(
                description=results.get("description", ""),
                embedding=None,  # Ollama doesn't expose CLIP embeddings directly
                objects=objects,
                scene=results.get("scene", "unknown"),
                confidence=0.8,  # Default confidence
                latency_ms=latency_ms,
                model=self.vision_model
            )

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get text embedding for cross-modal alignment.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if not self.is_available:
            return None

        try:
            resp = self._session.post(
                f"{self.api_base}/embeddings",
                json={
                    "model": self.embed_model,
                    "prompt": text
                },
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )

            if resp.status_code == 200:
                embedding = resp.json().get("embedding", [])
                return np.array(embedding, dtype=np.float32)

            return None

        except Exception as e:
            logger.error(f"Text embedding failed: {e}")
            return None

    def batch_extract(
        self,
        image_paths: List[str],
        max_workers: int = 3
    ) -> List[Tuple[str, Optional[VisualFeatures]]]:
        """
        Extract features from multiple images in parallel.

        Args:
            image_paths: List of image paths
            max_workers: Number of parallel workers

        Returns:
            List of (path, features) tuples
        """
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.extract_features, path): path
                for path in image_paths
            }

            for future in as_completed(futures):
                path = futures[future]
                try:
                    features = future.result()
                    results.append((path, features))
                except Exception as e:
                    logger.error(f"Batch extraction failed for {path}: {e}")
                    results.append((path, None))

        return results

    def create_cross_modal_embedding(
        self,
        image_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create cross-modal embedding by describing image then embedding text.

        This bridges visual content to text embedding space for
        hybrid text-image search.

        Args:
            image_path: Path to image

        Returns:
            Dict with description and its embedding
        """
        # First describe the image
        desc_result = self.describe_image(
            image_path,
            "Describe this image in one detailed paragraph, focusing on the main subject, colors, setting, and any notable features."
        )

        if not desc_result:
            return None

        description = desc_result["description"]

        # Then embed the description
        embedding = self.get_text_embedding(description)

        if embedding is None:
            return None

        return {
            "image_path": image_path,
            "description": description,
            "embedding": embedding,
            "embedding_dim": len(embedding),
            "model_vision": self.vision_model,
            "model_embed": self.embed_model
        }


def main():
    """Test GPU visual feature extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="GPU Visual Features")
    parser.add_argument("--image", help="Image path to process")
    parser.add_argument("--describe", action="store_true", help="Get description")
    parser.add_argument("--features", action="store_true", help="Extract features")
    parser.add_argument("--crossmodal", action="store_true", help="Cross-modal embedding")
    parser.add_argument("--check", action="store_true", help="Check availability")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    extractor = GPUVisualFeatureExtractor()

    if args.check:
        print(f"GPU Node: {GPU_NODE_HOST}:{GPU_NODE_PORT}")
        print(f"Available: {extractor.is_available}")
        return

    if not args.image:
        print("GPU Visual Feature Extraction")
        print("  --image PATH     Image to process")
        print("  --describe       Get natural language description")
        print("  --features       Extract structured features")
        print("  --crossmodal     Create cross-modal embedding")
        print("  --check          Check GPU node availability")
        return

    if not extractor.is_available:
        print("GPU node not available")
        return

    if args.describe:
        print(f"Describing: {args.image}")
        result = extractor.describe_image(args.image)
        if result:
            print(f"\nDescription: {result['description']}")
            print(f"Model: {result['model']}")
            print(f"Latency: {result['latency_ms']:.0f}ms")
        else:
            print("Failed to describe image")

    elif args.features:
        print(f"Extracting features: {args.image}")
        features = extractor.extract_features(args.image)
        if features:
            print(f"\nScene: {features.scene}")
            print(f"Objects: {', '.join(features.objects)}")
            print(f"Description: {features.description}")
            print(f"Latency: {features.latency_ms:.0f}ms")
        else:
            print("Failed to extract features")

    elif args.crossmodal:
        print(f"Creating cross-modal embedding: {args.image}")
        result = extractor.create_cross_modal_embedding(args.image)
        if result:
            print(f"\nDescription: {result['description'][:200]}...")
            print(f"Embedding dim: {result['embedding_dim']}")
            print(f"Vision model: {result['model_vision']}")
            print(f"Embed model: {result['model_embed']}")
        else:
            print("Failed to create cross-modal embedding")

    else:
        print("Specify --describe, --features, or --crossmodal")


if __name__ == "__main__":
    main()
