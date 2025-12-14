#!/usr/bin/env python3
"""
SAM3 Remote Client - Access SAM3 inference from any cluster node.

Usage:
    from sam3_client import SAM3Client

    client = SAM3Client("completeu-server")  # or IP address
    result = client.segment("path/to/image.jpg", "a dog")
    print(f"Found {result['segments_found']} segments")
"""

import base64
import io
import os
from pathlib import Path
from typing import Optional, Union, List
import json

try:
    import requests
except ImportError:
    os.system("pip install requests")
    import requests

try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Default node addresses
NODE_ADDRESSES = {
    "completeu-server": "192.168.1.186",
    "mac-studio": "192.168.1.239",
    "macbook-air": "192.168.1.151",
    "macpro51": "192.168.1.73"
}

DEFAULT_PORT = 8400


class SAM3Client:
    """Client for remote SAM3 inference."""

    def __init__(self, host: str = "completeu-server", port: int = DEFAULT_PORT, timeout: int = 60):
        """
        Initialize SAM3 client.

        Args:
            host: Hostname or IP (can use node names like "completeu-server")
            port: Server port (default 8400)
            timeout: Request timeout in seconds
        """
        # Resolve node name to IP if needed
        if host in NODE_ADDRESSES:
            host = NODE_ADDRESSES[host]

        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def health(self) -> dict:
        """Check server health."""
        resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def status(self) -> dict:
        """Get detailed server status."""
        resp = requests.get(f"{self.base_url}/status", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def is_available(self) -> bool:
        """Check if server is available and model is loaded."""
        try:
            health = self.health()
            return health.get("model_loaded", False)
        except Exception:
            return False

    def segment(
        self,
        image: Union[str, Path, bytes, "Image.Image"],
        prompt: str,
        threshold: float = 0.5,
        return_mask: bool = True
    ) -> dict:
        """
        Segment image with text prompt.

        Args:
            image: Image path, bytes, or PIL Image
            prompt: Text prompt describing what to segment (e.g., "a cat", "the red car")
            threshold: Confidence threshold (0-1)
            return_mask: Whether to return segmentation masks

        Returns:
            Dict with segments_found, masks, bboxes, confidence_scores, inference_time_ms
        """
        # Convert image to base64
        image_base64 = self._image_to_base64(image)

        payload = {
            "image_base64": image_base64,
            "prompt": prompt,
            "threshold": threshold,
            "return_mask": return_mask
        }

        resp = requests.post(
            f"{self.base_url}/segment",
            json=payload,
            timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def segment_multiple(
        self,
        image: Union[str, Path, bytes],
        prompts: List[str],
        threshold: float = 0.5
    ) -> List[dict]:
        """
        Segment image with multiple text prompts.

        Args:
            image: Image path, bytes, or PIL Image
            prompts: List of text prompts
            threshold: Confidence threshold

        Returns:
            List of segmentation results, one per prompt
        """
        image_base64 = self._image_to_base64(image)

        results = []
        for prompt in prompts:
            payload = {
                "image_base64": image_base64,
                "prompt": prompt,
                "threshold": threshold,
                "return_mask": True
            }
            resp = requests.post(
                f"{self.base_url}/segment",
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            results.append(resp.json())

        return results

    def get_embedding(self, image: Union[str, Path, bytes]) -> dict:
        """
        Get image embedding from SAM3 encoder.

        Args:
            image: Image path, bytes, or PIL Image

        Returns:
            Dict with embedding preview and dimensions
        """
        image_base64 = self._image_to_base64(image)

        resp = requests.post(
            f"{self.base_url}/embed",
            data={"image_base64": image_base64},
            timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def decode_mask(self, mask_base64: str) -> "np.ndarray":
        """Decode base64 mask to numpy array."""
        if not HAS_PIL:
            raise ImportError("PIL required for mask decoding")

        mask_data = base64.b64decode(mask_base64)
        mask_img = Image.open(io.BytesIO(mask_data))
        return np.array(mask_img)

    def _image_to_base64(self, image: Union[str, Path, bytes, "Image.Image"]) -> str:
        """Convert various image formats to base64."""
        if isinstance(image, (str, Path)):
            # File path
            with open(image, "rb") as f:
                return base64.b64encode(f.read()).decode()
        elif isinstance(image, bytes):
            return base64.b64encode(image).decode()
        elif HAS_PIL and isinstance(image, Image.Image):
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode()
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")


def find_available_server(ports: List[int] = None) -> Optional[SAM3Client]:
    """Find an available SAM3 server in the cluster."""
    ports = ports or [DEFAULT_PORT]

    for node, ip in NODE_ADDRESSES.items():
        for port in ports:
            try:
                client = SAM3Client(ip, port, timeout=5)
                if client.is_available():
                    print(f"Found SAM3 server at {node} ({ip}:{port})")
                    return client
            except Exception:
                continue

    return None


# Convenience function
def segment(image_path: str, prompt: str, server: str = "completeu-server") -> dict:
    """Quick segmentation with default server."""
    client = SAM3Client(server)
    return client.segment(image_path, prompt)


if __name__ == "__main__":
    # Test connectivity
    import sys

    server = sys.argv[1] if len(sys.argv) > 1 else "completeu-server"
    print(f"Testing SAM3 server at {server}...")

    client = SAM3Client(server)

    try:
        status = client.status()
        print(f"Server status: {json.dumps(status, indent=2)}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
