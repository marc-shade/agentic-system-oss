"""
Pollinations.ai Provider
========================

FREE image generation with no API key required.
Uses Flux model by default.

Endpoint: https://image.pollinations.ai/prompt/{prompt}

Parameters:
- width: Image width (default: 1024)
- height: Image height (default: 1024)
- seed: Random seed for reproducibility
- nologo: Remove Pollinations watermark
- model: Model to use (flux, turbo, etc.)
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from urllib.parse import quote, urlencode

import aiohttp

from .base import (
    ImageProvider,
    GenerationResult,
    ProviderModel,
    ProviderStatus,
    ImageFormat,
    detect_image_format,
)


class PollinationsProvider(ImageProvider):
    """Pollinations.ai - Free image generation."""

    name = "pollinations"
    display_name = "Pollinations.ai (FREE)"
    requires_api_key = False
    free_tier = True

    BASE_URL = "https://image.pollinations.ai/prompt"

    # Available models
    MODELS = {
        "flux": ProviderModel(
            id="flux",
            name="Flux",
            description="Black Forest Labs Flux model - high quality, good prompt adherence",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=8000,
        ),
        "flux-realism": ProviderModel(
            id="flux-realism",
            name="Flux Realism",
            description="Flux fine-tuned for photorealistic images",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=10000,
        ),
        "flux-anime": ProviderModel(
            id="flux-anime",
            name="Flux Anime",
            description="Flux fine-tuned for anime style",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=8000,
        ),
        "flux-3d": ProviderModel(
            id="flux-3d",
            name="Flux 3D",
            description="Flux fine-tuned for 3D renders",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=8000,
        ),
        "turbo": ProviderModel(
            id="turbo",
            name="Turbo",
            description="Fast generation, lower quality",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=3000,
        ),
    }

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
        """Generate an image using Pollinations.ai."""
        start_time = time.time()
        model_id = model or "flux"

        # Build URL with parameters
        encoded_prompt = quote(prompt)
        params = {
            "width": min(width, 1440),
            "height": min(height, 1440),
            "nologo": "true",
        }

        if seed is not None:
            params["seed"] = seed

        if model_id and model_id != "flux":
            params["model"] = model_id

        # Construct URL
        url = f"{self.BASE_URL}/{encoded_prompt}?{urlencode(params)}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        generation_time = int((time.time() - start_time) * 1000)

                        # Detect actual image format from bytes
                        img_format = detect_image_format(image_bytes)

                        self._record_request(0.0)

                        return GenerationResult(
                            success=True,
                            provider=self.name,
                            model=model_id,
                            prompt=prompt,
                            image_base64=self._encode_image(image_bytes),
                            image_url=url,
                            image_format=img_format,
                            mime_type=img_format.mime_type,
                            width=params["width"],
                            height=params["height"],
                            seed=seed,
                            generation_time_ms=generation_time,
                            cost=0.0,
                        )
                    else:
                        error_text = await response.text()
                        self._last_error = f"HTTP {response.status}: {error_text}"
                        return GenerationResult(
                            success=False,
                            provider=self.name,
                            model=model_id,
                            prompt=prompt,
                            error=self._last_error,
                        )

        except asyncio.TimeoutError:
            self._last_error = "Request timed out (120s)"
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model_id,
                prompt=prompt,
                error=self._last_error,
            )
        except Exception as e:
            self._last_error = str(e)
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model_id,
                prompt=prompt,
                error=self._last_error,
            )

    async def list_models(self) -> List[ProviderModel]:
        """List available Pollinations models."""
        return list(self.MODELS.values())

    async def check_health(self) -> Dict[str, Any]:
        """Check Pollinations.ai availability."""
        base_health = await super().check_health()

        # Quick test with a simple prompt
        try:
            async with aiohttp.ClientSession() as session:
                test_url = f"{self.BASE_URL}/test?width=64&height=64&nologo=true"
                async with session.head(test_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    base_health["api_reachable"] = response.status in (200, 302)
        except Exception as e:
            base_health["api_reachable"] = False
            base_health["health_check_error"] = str(e)

        return base_health
