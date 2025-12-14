"""
Hugging Face Inference API Provider
===================================

Free tier with rate limits.
Wide variety of models available.

API: https://api-inference.huggingface.co/models/{model_id}
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


class HuggingFaceProvider(ImageProvider):
    """Hugging Face Inference API image generation."""

    name = "huggingface"
    display_name = "Hugging Face"
    requires_api_key = True
    free_tier = True

    BASE_URL = "https://api-inference.huggingface.co/models"

    MODELS = {
        "sdxl": ProviderModel(
            id="stabilityai/stable-diffusion-xl-base-1.0",
            name="Stable Diffusion XL",
            description="Stability AI's SDXL base model",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=15000,
        ),
        "sdxl-turbo": ProviderModel(
            id="stabilityai/sdxl-turbo",
            name="SDXL Turbo",
            description="Fast distilled SDXL (1-4 steps)",
            max_width=512,
            max_height=512,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=5000,
        ),
        "flux-dev": ProviderModel(
            id="black-forest-labs/FLUX.1-dev",
            name="Flux.1 Dev",
            description="Black Forest Labs Flux development model",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=20000,
        ),
        "flux-schnell": ProviderModel(
            id="black-forest-labs/FLUX.1-schnell",
            name="Flux.1 Schnell",
            description="Fast Flux model (4 steps)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=8000,
        ),
        "playground-v2.5": ProviderModel(
            id="playgroundai/playground-v2.5-1024px-aesthetic",
            name="Playground v2.5",
            description="Aesthetic-focused model, great for art",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=12000,
        ),
        "realvisxl": ProviderModel(
            id="SG161222/RealVisXL_V4.0",
            name="RealVisXL V4",
            description="Photorealistic SDXL fine-tune",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=15000,
        ),
        "pixel-art": ProviderModel(
            id="nerijs/pixel-art-xl",
            name="Pixel Art XL",
            description="SDXL fine-tuned for pixel art",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.0,
            average_generation_time_ms=12000,
        ),
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        api_key = api_key or os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN")
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
        """Generate image using Hugging Face Inference API."""
        if not self.api_key:
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model or "sdxl",
                prompt=prompt,
                error="Hugging Face API token required. Set HUGGINGFACE_API_TOKEN or HF_TOKEN env var.",
            )

        start_time = time.time()

        # Get model
        model_key = model or "sdxl"
        model_info = self.MODELS.get(model_key)
        model_id = model_info.id if model_info else self.MODELS["sdxl"].id

        url = f"{self.BASE_URL}/{model_id}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "width": min(width, model_info.max_width if model_info else 1024),
                "height": min(height, model_info.max_height if model_info else 1024),
            }
        }

        if negative_prompt and model_info and model_info.supports_negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt

        if seed is not None:
            payload["parameters"]["seed"] = seed

        if "flux" not in model_id.lower() and "turbo" not in model_id.lower():
            payload["parameters"]["num_inference_steps"] = num_inference_steps
            payload["parameters"]["guidance_scale"] = guidance_scale

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        generation_time = int((time.time() - start_time) * 1000)

                        self._record_request(0.0)

                        return GenerationResult(
                            success=True,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            image_base64=self._encode_image(image_bytes),
                            width=payload["parameters"]["width"],
                            height=payload["parameters"]["height"],
                            seed=seed,
                            generation_time_ms=generation_time,
                            cost=0.0,
                        )
                    elif response.status == 503:
                        # Model loading
                        error_data = await response.json()
                        estimated_time = error_data.get("estimated_time", 60)
                        self._last_error = f"Model loading, estimated {estimated_time}s wait"
                        return GenerationResult(
                            success=False,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            error=self._last_error,
                        )
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", "Unknown error")
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
            self._last_error = "Request timed out (120s)"
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
        """List available Hugging Face models."""
        return list(self.MODELS.values())
