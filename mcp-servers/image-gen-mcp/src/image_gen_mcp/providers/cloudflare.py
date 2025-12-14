"""
Cloudflare Workers AI Provider
==============================

10,000 Neurons/day FREE tier.
Fast edge-based inference.

Models:
- @cf/stabilityai/stable-diffusion-xl-base-1.0
- @cf/bytedance/stable-diffusion-xl-lightning
- @cf/black-forest-labs/flux-1-schnell
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
    ProviderStatus,
)


class CloudflareProvider(ImageProvider):
    """Cloudflare Workers AI image generation."""

    name = "cloudflare"
    display_name = "Cloudflare Workers AI"
    requires_api_key = True
    free_tier = True  # 10K neurons/day

    # Model costs in neurons (approximate)
    MODELS = {
        "sdxl": ProviderModel(
            id="@cf/stabilityai/stable-diffusion-xl-base-1.0",
            name="Stable Diffusion XL",
            description="High quality SDXL model",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,  # Free tier
            average_generation_time_ms=5000,
        ),
        "sdxl-lightning": ProviderModel(
            id="@cf/bytedance/stable-diffusion-xl-lightning",
            name="SDXL Lightning",
            description="Fast 4-step SDXL variant by ByteDance",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=2000,
        ),
        "flux-schnell": ProviderModel(
            id="@cf/black-forest-labs/flux-1-schnell",
            name="Flux 1 Schnell",
            description="Fast Flux model by Black Forest Labs",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=3000,
        ),
        "dreamshaper": ProviderModel(
            id="@cf/lykon/dreamshaper-8-lcm",
            name="DreamShaper 8 LCM",
            description="Photorealistic fine-tuned model",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=2500,
        ),
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        # Try environment variable if no key provided
        api_key = api_key or os.getenv("CLOUDFLARE_API_TOKEN")
        super().__init__(api_key, config)
        self.account_id = (config or {}).get("account_id") or os.getenv("CLOUDFLARE_ACCOUNT_ID")

    @property
    def status(self) -> ProviderStatus:
        if not self.api_key or not self.account_id:
            return ProviderStatus.UNCONFIGURED
        return self._status

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
        """Generate image using Cloudflare Workers AI."""
        if not self.api_key or not self.account_id:
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model or "sdxl",
                prompt=prompt,
                error="Cloudflare API token and account ID required. Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID env vars.",
            )

        start_time = time.time()

        # Get model ID
        model_key = model or "sdxl"
        model_info = self.MODELS.get(model_key)
        model_id = model_info.id if model_info else self.MODELS["sdxl"].id

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model_id}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "width": min(width, 1024),
            "height": min(height, 1024),
        }

        if negative_prompt and model_info and model_info.supports_negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if seed is not None:
            payload["seed"] = seed

        if "flux" not in model_id.lower():
            payload["num_steps"] = min(num_inference_steps, 20)
            payload["guidance"] = guidance_scale

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        # Cloudflare returns raw image bytes
                        image_bytes = await response.read()
                        generation_time = int((time.time() - start_time) * 1000)

                        self._record_request(0.0)

                        return GenerationResult(
                            success=True,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            image_base64=self._encode_image(image_bytes),
                            width=payload["width"],
                            height=payload["height"],
                            seed=seed,
                            generation_time_ms=generation_time,
                            cost=0.0,
                        )
                    else:
                        error_data = await response.json()
                        error_msg = error_data.get("errors", [{"message": "Unknown error"}])[0].get("message")
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
        """List available Cloudflare models."""
        return list(self.MODELS.values())
