"""
Together AI Provider
====================

Very affordable image generation.
Flux Schnell: ~$0.003 per image

API: https://api.together.xyz/v1/images/generations
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
import os

import aiohttp

from .base import (
    ImageProvider,
    GenerationResult,
    ProviderModel,
)


class TogetherProvider(ImageProvider):
    """Together AI image generation."""

    name = "together"
    display_name = "Together AI"
    requires_api_key = True
    free_tier = False  # Pay per use but very cheap

    BASE_URL = "https://api.together.xyz/v1/images/generations"

    MODELS = {
        "flux-schnell": ProviderModel(
            id="black-forest-labs/FLUX.1-schnell-Free",
            name="Flux.1 Schnell (Free)",
            description="Fast Flux model - FREE tier available",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=3000,
        ),
        "flux-schnell-paid": ProviderModel(
            id="black-forest-labs/FLUX.1-schnell",
            name="Flux.1 Schnell",
            description="Fast Flux model (~$0.003/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.003,
            average_generation_time_ms=2000,
        ),
        "flux-dev": ProviderModel(
            id="black-forest-labs/FLUX.1-dev",
            name="Flux.1 Dev",
            description="Higher quality Flux (~$0.025/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.025,
            average_generation_time_ms=5000,
        ),
        "flux-pro": ProviderModel(
            id="black-forest-labs/FLUX.1-pro",
            name="Flux.1 Pro",
            description="Best quality Flux (~$0.05/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.05,
            average_generation_time_ms=8000,
        ),
        "sd3": ProviderModel(
            id="stabilityai/stable-diffusion-3-medium",
            name="Stable Diffusion 3",
            description="SD3 Medium (~$0.002/image)",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.002,
            average_generation_time_ms=4000,
        ),
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        api_key = api_key or os.getenv("TOGETHER_API_KEY")
        super().__init__(api_key, config)

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
        """Generate image using Together AI."""
        if not self.api_key:
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model or "flux-schnell",
                prompt=prompt,
                error="Together AI API key required. Set TOGETHER_API_KEY env var.",
            )

        start_time = time.time()

        model_key = model or "flux-schnell"
        model_info = self.MODELS.get(model_key)
        model_id = model_info.id if model_info else self.MODELS["flux-schnell"].id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "prompt": prompt,
            "width": min(width, model_info.max_width if model_info else 1024),
            "height": min(height, model_info.max_height if model_info else 1024),
            "n": 1,
            "response_format": "b64_json",
        }

        if negative_prompt and model_info and model_info.supports_negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if seed is not None:
            payload["seed"] = seed

        if "flux" not in model_id.lower():
            payload["steps"] = num_inference_steps

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        generation_time = int((time.time() - start_time) * 1000)

                        image_data = data.get("data", [{}])[0]
                        image_b64 = image_data.get("b64_json", "")

                        cost = model_info.cost_per_image if model_info else 0.0
                        self._record_request(cost)

                        return GenerationResult(
                            success=True,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            image_base64=image_b64,
                            width=payload["width"],
                            height=payload["height"],
                            seed=seed,
                            generation_time_ms=generation_time,
                            cost=cost,
                        )
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        except:
                            error_msg = await response.text()
                        self._last_error = f"HTTP {response.status}: {error_msg}"
                        return GenerationResult(
                            success=False,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            error=self._last_error,
                        )

        except asyncio.TimeoutError:
            self._last_error = "Request timed out"
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model_key,
                prompt=prompt,
                error=self._last_error,
            )
        except Exception as e:
            self._last_error = str(e)
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model_key,
                prompt=prompt,
                error=self._last_error,
            )

    async def list_models(self) -> List[ProviderModel]:
        """List available Together AI models."""
        return list(self.MODELS.values())
