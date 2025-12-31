"""
Latent-Guided Provider Wrapper
==============================

Transparent wrapper for image generation providers that adds latent guidance.

This is the "sidecar control" pattern - we intercept generation requests
and apply latent steering without modifying the underlying provider.

Usage:
    base_provider = HuggingFaceProvider()
    latent_hacker = DiffusionLatentHacker()
    guided = LatentGuidedProvider(base_provider, latent_hacker)

    # Capture style from generation
    result = await guided.generate(
        prompt="A serene Japanese garden, watercolor style",
        capture_style_as="watercolor_japan"
    )

    # Apply style to new generation
    result = await guided.generate(
        prompt="A futuristic cityscape",
        apply_style="watercolor_japan",
        style_strength=0.8
    )
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from .providers.base import (
    ImageProvider,
    GenerationResult,
    ProviderModel,
    ProviderStatus,
)
from .latent_hacker import (
    DiffusionLatentHacker,
    LatentState,
    StyleTransferResult,
    image_from_base64,
)

logger = logging.getLogger("latent-guided-provider")


class LatentGuidedProvider(ImageProvider):
    """
    Wrapper that adds latent guidance capabilities to any image provider.

    Transparently intercepts generation requests and applies latent steering
    based on cached style latents.

    Features:
    - Style capture: Extract and cache latent from any generation
    - Style application: Apply cached style to new generations
    - Cross-model transfer: Use style from one model with another
    - Style interpolation: Blend multiple cached styles
    """

    def __init__(
        self,
        base_provider: ImageProvider,
        latent_hacker: Optional[DiffusionLatentHacker] = None,
    ):
        """
        Initialize latent-guided provider.

        Args:
            base_provider: Underlying image generation provider
            latent_hacker: DiffusionLatentHacker instance (creates new if None)
        """
        self.base_provider = base_provider
        self.latent_hacker = latent_hacker or DiffusionLatentHacker()

        # Inherit base provider properties
        self.name = f"{base_provider.name}_latent_guided"
        self.display_name = f"{base_provider.display_name} (Latent Guided)"
        self.requires_api_key = base_provider.requires_api_key
        self.free_tier = base_provider.free_tier
        self.api_key = base_provider.api_key
        self.config = base_provider.config

        # Track guided generations
        self._guided_count = 0
        self._capture_count = 0

        logger.info(f"LatentGuidedProvider wrapping {base_provider.name}")

    @property
    def status(self) -> ProviderStatus:
        """Get status from base provider."""
        return self.base_provider.status

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
        # Latent guidance parameters
        apply_style: Optional[str] = None,
        style_strength: float = 0.7,
        capture_style_as: Optional[str] = None,
        capture_timestep: int = 50,
        **kwargs
    ) -> GenerationResult:
        """
        Generate image with optional latent guidance.

        Standard Parameters:
            prompt: Text prompt for generation
            negative_prompt: Negative prompt (if supported)
            width, height: Image dimensions
            seed: Random seed (may be overridden by latent guidance)
            model: Model to use
            num_inference_steps: Diffusion steps
            guidance_scale: Classifier-free guidance scale

        Latent Guidance Parameters:
            apply_style: Name of cached style to apply
            style_strength: How strongly to apply style (0-1)
            capture_style_as: Capture result as named style
            capture_timestep: Diffusion timestep for capture (default 50)

        Returns:
            GenerationResult (extended with latent guidance metadata)
        """
        original_prompt = prompt
        original_seed = seed
        latent_metadata = {}

        # Apply latent guidance if requested
        if apply_style:
            try:
                transfer = self.latent_hacker.apply_style_latent(
                    target_prompt=prompt,
                    style_name=apply_style,
                    strength=style_strength,
                    extract_style_cues=True,
                )
                # Override parameters with guided values
                prompt = transfer.guided_prompt
                seed = transfer.guided_seed

                # Apply any additional params from latent
                if "negative_prompt" in transfer.params and negative_prompt is None:
                    negative_prompt = transfer.params["negative_prompt"]

                latent_metadata = {
                    "_latent_guided": True,
                    "_style_source": apply_style,
                    "_guidance_strength": style_strength,
                    "_original_prompt": original_prompt,
                }

                self._guided_count += 1
                logger.info(f"Applied style '{apply_style}' with strength {style_strength}")

            except ValueError as e:
                logger.warning(f"Failed to apply style '{apply_style}': {e}")
                # Continue with unguided generation

        # Call base provider
        result = await self.base_provider.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            model=model,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            **kwargs
        )

        # Capture style if requested and generation succeeded
        if capture_style_as and result.success and result.image_base64:
            try:
                # Decode image
                image = image_from_base64(result.image_base64)

                # Create style latent
                self.latent_hacker.create_style_latent(
                    image=image,
                    name=capture_style_as,
                    model_id=result.model,
                    provider=result.provider,
                    generation_params={
                        "prompt": original_prompt,
                        "negative_prompt": negative_prompt,
                        "seed": result.seed or original_seed,
                        "guidance_scale": guidance_scale,
                        "num_inference_steps": num_inference_steps,
                    },
                    timestep=capture_timestep,
                )

                latent_metadata["_style_captured"] = capture_style_as
                self._capture_count += 1
                logger.info(f"Captured style as '{capture_style_as}'")

            except Exception as e:
                logger.warning(f"Failed to capture style: {e}")

        # Attach latent metadata to result
        if latent_metadata:
            # Store in result for inspection
            result._latent_metadata = latent_metadata

        return result

    async def generate_with_style_transfer(
        self,
        source_image_base64: str,
        source_model: str,
        target_prompt: str,
        target_model: Optional[str] = None,
        strength: float = 0.8,
        **kwargs
    ) -> GenerationResult:
        """
        Generate with cross-model style transfer.

        Takes a source image (from any model) and applies its style
        to a new generation using the target model.

        Args:
            source_image_base64: Base64 encoded source image
            source_model: Model that created source image
            target_prompt: Prompt for new generation
            target_model: Model to use for new generation (defaults to base)
            strength: Transfer strength (0-1)
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult with transferred style
        """
        # Decode source image
        source_image = image_from_base64(source_image_base64)

        # Get transfer parameters
        transfer = self.latent_hacker.cross_model_transfer(
            source_image=source_image,
            source_model=source_model,
            target_model=target_model or self.base_provider.name,
            target_prompt=target_prompt,
            strength=strength,
        )

        # Generate with transfer parameters
        result = await self.generate(
            prompt=transfer.guided_prompt,
            seed=transfer.guided_seed,
            model=target_model,
            **kwargs
        )

        # Add transfer metadata
        result._latent_metadata = {
            "_cross_model_transfer": True,
            "_source_model": source_model,
            "_target_model": target_model,
            "_transfer_strength": strength,
        }

        return result

    async def generate_interpolated(
        self,
        style_a: str,
        style_b: str,
        alpha: float,
        prompt: str,
        **kwargs
    ) -> GenerationResult:
        """
        Generate with interpolated style blend.

        Blends two cached styles at the specified ratio.

        Args:
            style_a: First style name
            style_b: Second style name
            alpha: Blend factor (0=all A, 1=all B)
            prompt: Generation prompt
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult with blended style
        """
        # Get interpolated parameters
        transfer = self.latent_hacker.interpolate_styles(
            style_a=style_a,
            style_b=style_b,
            alpha=alpha,
            target_prompt=prompt,
        )

        # Generate
        result = await self.generate(
            prompt=transfer.guided_prompt,
            seed=transfer.guided_seed,
            **kwargs
        )

        # Add interpolation metadata
        result._latent_metadata = {
            "_interpolated": True,
            "_style_a": style_a,
            "_style_b": style_b,
            "_alpha": alpha,
        }

        return result

    def list_cached_styles(self) -> List[Dict[str, Any]]:
        """List all cached style latents."""
        return self.latent_hacker.list_cached_styles()

    def get_style_similarity(self, style_a: str, style_b: str) -> float:
        """Get similarity between two cached styles."""
        return self.latent_hacker.compute_style_similarity(style_a, style_b)

    def delete_style(self, name: str) -> bool:
        """Delete a cached style."""
        return self.latent_hacker.delete_style(name)

    async def list_models(self) -> List[ProviderModel]:
        """List available models from base provider."""
        return await self.base_provider.list_models()

    async def check_health(self) -> Dict[str, Any]:
        """Check health including latent guidance stats."""
        base_health = await self.base_provider.check_health()
        base_health.update({
            "latent_guidance": {
                "enabled": True,
                "cached_styles": len(self.latent_hacker._latent_cache),
                "guided_generations": self._guided_count,
                "style_captures": self._capture_count,
            }
        })
        return base_health


class MultiProviderLatentRouter:
    """
    Routes latent-guided generations across multiple providers.

    Enables cross-model latent transfer and provider fallback
    with latent guidance.
    """

    def __init__(
        self,
        providers: Dict[str, ImageProvider],
        latent_hacker: Optional[DiffusionLatentHacker] = None,
    ):
        """
        Initialize multi-provider router.

        Args:
            providers: Dict of provider_name -> ImageProvider
            latent_hacker: Shared DiffusionLatentHacker instance
        """
        self.latent_hacker = latent_hacker or DiffusionLatentHacker()

        # Wrap all providers with latent guidance
        self.guided_providers = {
            name: LatentGuidedProvider(provider, self.latent_hacker)
            for name, provider in providers.items()
        }

        logger.info(f"MultiProviderLatentRouter initialized with {len(providers)} providers")

    def get_provider(self, name: str) -> Optional[LatentGuidedProvider]:
        """Get a specific latent-guided provider."""
        return self.guided_providers.get(name)

    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate with automatic provider selection and fallback.

        Args:
            prompt: Generation prompt
            provider: Preferred provider (tries first)
            fallback_providers: Providers to try if primary fails
            **kwargs: Generation parameters (including latent guidance)

        Returns:
            GenerationResult from first successful provider
        """
        providers_to_try = []

        if provider and provider in self.guided_providers:
            providers_to_try.append(provider)

        if fallback_providers:
            providers_to_try.extend([
                p for p in fallback_providers
                if p in self.guided_providers and p != provider
            ])

        # Add remaining providers as last resort
        for name in self.guided_providers:
            if name not in providers_to_try:
                providers_to_try.append(name)

        last_error = None
        for provider_name in providers_to_try:
            guided_provider = self.guided_providers[provider_name]

            if guided_provider.status != ProviderStatus.AVAILABLE:
                continue

            try:
                result = await guided_provider.generate(prompt=prompt, **kwargs)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Provider {provider_name} failed: {e}")

        # All providers failed
        return GenerationResult(
            success=False,
            provider="multi_provider_router",
            model="",
            prompt=prompt,
            error=f"All providers failed. Last error: {last_error}",
        )

    async def cross_provider_transfer(
        self,
        source_result: GenerationResult,
        target_provider: str,
        target_prompt: str,
        strength: float = 0.8,
        **kwargs
    ) -> GenerationResult:
        """
        Transfer style from one provider's result to another provider.

        Args:
            source_result: GenerationResult from source provider
            target_provider: Name of target provider
            target_prompt: Prompt for target generation
            strength: Transfer strength
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult from target provider with transferred style
        """
        if target_provider not in self.guided_providers:
            raise ValueError(f"Unknown provider: {target_provider}")

        if not source_result.success or not source_result.image_base64:
            raise ValueError("Source result must be successful with image data")

        guided_provider = self.guided_providers[target_provider]

        return await guided_provider.generate_with_style_transfer(
            source_image_base64=source_result.image_base64,
            source_model=f"{source_result.provider}/{source_result.model}",
            target_prompt=target_prompt,
            strength=strength,
            **kwargs
        )
