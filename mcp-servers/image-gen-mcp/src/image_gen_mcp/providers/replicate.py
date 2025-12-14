"""
Replicate Provider
==================

50 free generations per month, then pay-per-use.
High quality, reliable infrastructure.

API: https://api.replicate.com/v1/predictions
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


class ReplicateProvider(ImageProvider):
    """Replicate image generation."""

    name = "replicate"
    display_name = "Replicate"
    requires_api_key = True
    free_tier = True  # 50/month free

    BASE_URL = "https://api.replicate.com/v1"

    MODELS = {
        "flux-schnell": ProviderModel(
            id="black-forest-labs/flux-schnell",
            name="Flux Schnell",
            description="Fast Flux model ($0.003/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.003,
            average_generation_time_ms=3000,
        ),
        "flux-dev": ProviderModel(
            id="black-forest-labs/flux-dev",
            name="Flux Dev",
            description="Higher quality Flux ($0.025/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.025,
            average_generation_time_ms=8000,
        ),
        "flux-pro": ProviderModel(
            id="black-forest-labs/flux-1.1-pro",
            name="Flux 1.1 Pro",
            description="Best Flux model ($0.04/image)",
            max_width=1440,
            max_height=1440,
            supports_negative_prompt=False,
            supports_seed=True,
            cost_per_image=0.04,
            average_generation_time_ms=10000,
        ),
        "sdxl": ProviderModel(
            id="stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            name="Stable Diffusion XL",
            description="Stability AI SDXL",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.004,
            average_generation_time_ms=5000,
        ),
        "playground-v2.5": ProviderModel(
            id="playgroundai/playground-v2.5-1024px-aesthetic:a45f82a1382bed5c7aeb861dac7c7d191b0fdf74d8d57c4a0e6ed7d4d0bf7d24",
            name="Playground v2.5",
            description="Aesthetic model great for art",
            max_width=1024,
            max_height=1024,
            supports_negative_prompt=True,
            supports_seed=True,
            cost_per_image=0.003,
            average_generation_time_ms=6000,
        ),
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
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
        """Generate image using Replicate."""
        if not self.api_key:
            return GenerationResult(
                success=False,
                provider=self.name,
                model=model or "flux-schnell",
                prompt=prompt,
                error="Replicate API token required. Set REPLICATE_API_TOKEN env var.",
            )

        start_time = time.time()

        model_key = model or "flux-schnell"
        model_info = self.MODELS.get(model_key)
        model_id = model_info.id if model_info else self.MODELS["flux-schnell"].id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",  # Wait for result synchronously
        }

        # Replicate uses different input formats per model
        if "flux" in model_key:
            input_data = {
                "prompt": prompt,
                "aspect_ratio": self._get_aspect_ratio(width, height),
                "output_format": "png",
            }
            if seed is not None:
                input_data["seed"] = seed
        else:
            input_data = {
                "prompt": prompt,
                "width": min(width, model_info.max_width if model_info else 1024),
                "height": min(height, model_info.max_height if model_info else 1024),
            }
            if negative_prompt and model_info and model_info.supports_negative_prompt:
                input_data["negative_prompt"] = negative_prompt
            if seed is not None:
                input_data["seed"] = seed
            input_data["num_inference_steps"] = num_inference_steps
            input_data["guidance_scale"] = guidance_scale

        payload = {
            "version": model_id.split(":")[-1] if ":" in model_id else None,
            "input": input_data,
        }

        # For versioned models
        if ":" in model_id:
            url = f"{self.BASE_URL}/predictions"
        else:
            # For official models (like flux)
            url = f"{self.BASE_URL}/models/{model_id}/predictions"
            del payload["version"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status in (200, 201):
                        data = await response.json()

                        # Check if completed or need to poll
                        if data.get("status") == "succeeded":
                            output = data.get("output")
                            image_url = output[0] if isinstance(output, list) else output

                            # Download the image
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    image_bytes = await img_response.read()
                                    generation_time = int((time.time() - start_time) * 1000)

                                    cost = model_info.cost_per_image if model_info else 0.0
                                    self._record_request(cost)

                                    return GenerationResult(
                                        success=True,
                                        provider=self.name,
                                        model=model_key,
                                        prompt=prompt,
                                        image_base64=self._encode_image(image_bytes),
                                        image_url=image_url,
                                        width=width,
                                        height=height,
                                        seed=seed,
                                        generation_time_ms=generation_time,
                                        cost=cost,
                                    )

                        # Need to poll for result
                        prediction_id = data.get("id")
                        if prediction_id:
                            return await self._poll_prediction(
                                session, headers, prediction_id, prompt, model_key, model_info, seed, width, height, start_time
                            )

                        self._last_error = "No prediction ID returned"
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
                            error_msg = error_data.get("detail", "Unknown error")
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

    async def _poll_prediction(
        self, session, headers, prediction_id, prompt, model_key, model_info, seed, width, height, start_time
    ) -> GenerationResult:
        """Poll for prediction completion."""
        poll_url = f"{self.BASE_URL}/predictions/{prediction_id}"

        for _ in range(60):  # Max 60 polls (2 minutes)
            await asyncio.sleep(2)

            async with session.get(poll_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")

                    if status == "succeeded":
                        output = data.get("output")
                        image_url = output[0] if isinstance(output, list) else output

                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                image_bytes = await img_response.read()
                                generation_time = int((time.time() - start_time) * 1000)

                                cost = model_info.cost_per_image if model_info else 0.0
                                self._record_request(cost)

                                return GenerationResult(
                                    success=True,
                                    provider=self.name,
                                    model=model_key,
                                    prompt=prompt,
                                    image_base64=self._encode_image(image_bytes),
                                    image_url=image_url,
                                    width=width,
                                    height=height,
                                    seed=seed,
                                    generation_time_ms=generation_time,
                                    cost=cost,
                                )

                    elif status == "failed":
                        error = data.get("error", "Generation failed")
                        self._last_error = error
                        return GenerationResult(
                            success=False,
                            provider=self.name,
                            model=model_key,
                            prompt=prompt,
                            error=error,
                        )

        self._last_error = "Polling timeout"
        return GenerationResult(
            success=False,
            provider=self.name,
            model=model_key,
            prompt=prompt,
            error=self._last_error,
        )

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Convert dimensions to aspect ratio string for Flux."""
        ratio = width / height
        if ratio > 1.7:
            return "16:9"
        elif ratio > 1.4:
            return "3:2"
        elif ratio > 1.2:
            return "4:3"
        elif ratio > 0.8:
            return "1:1"
        elif ratio > 0.7:
            return "3:4"
        elif ratio > 0.6:
            return "2:3"
        else:
            return "9:16"

    async def list_models(self) -> List[ProviderModel]:
        """List available Replicate models."""
        return list(self.MODELS.values())
