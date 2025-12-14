"""Base provider interface for image generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import base64
import io


class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    UNKNOWN = "unknown"

    @property
    def extension(self) -> str:
        """Get file extension for this format."""
        return {
            ImageFormat.JPEG: ".jpg",
            ImageFormat.PNG: ".png",
            ImageFormat.WEBP: ".webp",
            ImageFormat.GIF: ".gif",
            ImageFormat.UNKNOWN: ".bin",
        }[self]

    @property
    def mime_type(self) -> str:
        """Get MIME type for this format."""
        return {
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.PNG: "image/png",
            ImageFormat.WEBP: "image/webp",
            ImageFormat.GIF: "image/gif",
            ImageFormat.UNKNOWN: "application/octet-stream",
        }[self]


def detect_image_format(data: bytes) -> ImageFormat:
    """Detect image format from magic bytes."""
    if len(data) < 4:
        return ImageFormat.UNKNOWN

    # JPEG: FFD8FF
    if data[:3] == b'\xff\xd8\xff':
        return ImageFormat.JPEG
    # PNG: 89504E47 0D0A1A0A
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return ImageFormat.PNG
    # WebP: RIFF....WEBP
    if data[:4] == b'RIFF' and len(data) >= 12 and data[8:12] == b'WEBP':
        return ImageFormat.WEBP
    # GIF: GIF87a or GIF89a
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return ImageFormat.GIF

    return ImageFormat.UNKNOWN


def convert_to_png(data: bytes) -> bytes:
    """Convert image data to PNG format using Pillow."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    except Exception:
        # Return original if conversion fails
        return data


class ProviderStatus(Enum):
    """Provider availability status."""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"
    DISABLED = "disabled"


@dataclass
class GenerationResult:
    """Result of an image generation request."""
    success: bool
    provider: str
    model: str
    prompt: str

    # Image data (one of these will be set)
    image_base64: Optional[str] = None
    image_path: Optional[Path] = None
    image_url: Optional[str] = None

    # Format info
    image_format: ImageFormat = ImageFormat.PNG
    mime_type: str = "image/png"

    # Metadata
    width: int = 0
    height: int = 0
    seed: Optional[int] = None
    generation_time_ms: int = 0
    cost: float = 0.0

    # Error info
    error: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "image_base64": self.image_base64[:100] + "..." if self.image_base64 else None,
            "image_path": str(self.image_path) if self.image_path else None,
            "image_url": self.image_url,
            "image_format": self.image_format.value,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "generation_time_ms": self.generation_time_ms,
            "cost": self.cost,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProviderModel:
    """Information about an available model."""
    id: str
    name: str
    description: str
    max_width: int = 1024
    max_height: int = 1024
    supports_negative_prompt: bool = True
    supports_seed: bool = True
    supports_img2img: bool = False
    cost_per_image: float = 0.0
    average_generation_time_ms: int = 5000


class ImageProvider(ABC):
    """Abstract base class for image generation providers."""

    name: str = "base"
    display_name: str = "Base Provider"
    requires_api_key: bool = False
    free_tier: bool = False

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        self.api_key = api_key
        self.config = config or {}
        self._status = ProviderStatus.AVAILABLE
        self._last_error: Optional[str] = None
        self._request_count = 0
        self._total_cost = 0.0

    @property
    def status(self) -> ProviderStatus:
        """Get current provider status."""
        if self.requires_api_key and not self.api_key:
            return ProviderStatus.UNCONFIGURED
        return self._status

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        model: Optional[str] = None,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        **kwargs
    ) -> GenerationResult:
        """Generate an image from a text prompt."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ProviderModel]:
        """List available models for this provider."""
        pass

    async def check_health(self) -> Dict[str, Any]:
        """Check provider health and availability."""
        return {
            "provider": self.name,
            "status": self.status.value,
            "configured": self.api_key is not None if self.requires_api_key else True,
            "request_count": self._request_count,
            "total_cost": self._total_cost,
            "last_error": self._last_error,
        }

    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64."""
        return base64.b64encode(image_bytes).decode("utf-8")

    def _record_request(self, cost: float = 0.0):
        """Record a request for tracking."""
        self._request_count += 1
        self._total_cost += cost
