"""
Diffusion Latent Hacker
=======================

Mathematical hacking for diffusion models via exposed constraint surfaces.

Based on Richard Aragon's paper:
"Mathematical Hacking: Synthetic Internal Variables via Exposed Constraint Surfaces"

Core insight: Diffusion models expose constraint surfaces (noised latents, scheduler alphas,
model predictions) that enable reconstruction and manipulation of hidden internal variables
without modifying model weights.

Key equation (DDPM diffusion):
    x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon

Noise recovery (inversion):
    epsilon = (x_t - sqrt(alpha_t) * x_0) / sqrt(1 - alpha_t)

This module implements:
- Noise recovery from generated images
- Style latent creation and caching
- Cross-model latent transfer
- Style interpolation in latent space
"""

import base64
import hashlib
import io
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("latent-hacker")


# DDPM noise schedule parameters (standard values)
DDPM_BETA_START = 0.0001
DDPM_BETA_END = 0.02
DDPM_NUM_TIMESTEPS = 1000


def compute_alpha_schedule(
    num_timesteps: int = DDPM_NUM_TIMESTEPS,
    beta_start: float = DDPM_BETA_START,
    beta_end: float = DDPM_BETA_END,
    schedule_type: str = "linear"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute diffusion schedule alphas.

    Returns:
        betas: Beta values for each timestep
        alphas: Alpha values (1 - beta)
        alpha_bar: Cumulative product of alphas (sqrt used in diffusion eq)
    """
    if schedule_type == "linear":
        betas = np.linspace(beta_start, beta_end, num_timesteps)
    elif schedule_type == "cosine":
        # Cosine schedule (Improved DDPM)
        s = 0.008
        steps = np.linspace(0, num_timesteps, num_timesteps + 1)
        f_t = np.cos((steps / num_timesteps + s) / (1 + s) * np.pi / 2) ** 2
        alpha_bar = f_t / f_t[0]
        betas = 1 - alpha_bar[1:] / alpha_bar[:-1]
        betas = np.clip(betas, 0.0001, 0.999)
    elif schedule_type == "scaled_linear":
        # Scaled linear (stable diffusion style)
        betas = np.linspace(beta_start**0.5, beta_end**0.5, num_timesteps) ** 2
    else:
        betas = np.linspace(beta_start, beta_end, num_timesteps)

    alphas = 1.0 - betas
    alpha_bar = np.cumprod(alphas)

    return betas, alphas, alpha_bar


@dataclass
class LatentState:
    """
    Captured latent state from a diffusion generation.

    Contains recovered noise and metadata for style transfer/manipulation.
    """
    # Core latent data
    noise_recovered: np.ndarray  # Recovered epsilon from image
    image_hash: str  # SHA256 of source image for verification

    # Diffusion parameters
    timestep: int  # t where we captured (typically 50-200)
    alpha_t: float  # sqrt(alpha_bar_t) coefficient
    schedule_type: str = "linear"

    # Model info
    model_id: str = "unknown"
    provider: str = "unknown"

    # Style fingerprint (optional, from TPU visual intelligence)
    style_fingerprint: Optional[np.ndarray] = None
    fingerprint_model: Optional[str] = None

    # Generation parameters
    generation_params: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    name: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excluding large arrays)."""
        return {
            "image_hash": self.image_hash,
            "timestep": self.timestep,
            "alpha_t": self.alpha_t,
            "schedule_type": self.schedule_type,
            "model_id": self.model_id,
            "provider": self.provider,
            "has_style_fingerprint": self.style_fingerprint is not None,
            "fingerprint_model": self.fingerprint_model,
            "generation_params": self.generation_params,
            "created_at": self.created_at.isoformat(),
            "name": self.name,
            "description": self.description,
            "noise_shape": list(self.noise_recovered.shape),
        }


@dataclass
class StyleTransferResult:
    """Result of applying style latent to new generation."""
    guided_prompt: str
    guided_seed: int
    guidance_strength: float
    source_style: str
    original_prompt: str
    params: Dict[str, Any]


class DiffusionLatentHacker:
    """
    Core mathematical hacking implementation for diffusion models.

    Exploits exposed constraint surfaces in diffusion models:
    - Noised latents (x_t)
    - Scheduler alphas (sqrt(alpha_bar_t))
    - Timestep indices
    - Transition functions

    Enables:
    - External override of model dynamics
    - Sidecar control independent of vendor APIs
    - Custom inference-time steering without weight modification
    - Latent transfer between incompatible models
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        schedule_type: str = "linear",
        num_timesteps: int = DDPM_NUM_TIMESTEPS,
    ):
        """
        Initialize latent hacker.

        Args:
            cache_dir: Directory for caching latent states
            schedule_type: Noise schedule type (linear, cosine, scaled_linear)
            num_timesteps: Number of diffusion timesteps
        """
        self.cache_dir = cache_dir or Path.home() / ".claude" / "latent_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.schedule_type = schedule_type
        self.num_timesteps = num_timesteps

        # Compute noise schedule
        self.betas, self.alphas, self.alpha_bar = compute_alpha_schedule(
            num_timesteps=num_timesteps,
            schedule_type=schedule_type
        )

        # In-memory cache for fast access
        self._latent_cache: Dict[str, LatentState] = {}

        # Load existing cache from disk
        self._load_cache_index()

        logger.info(f"DiffusionLatentHacker initialized (schedule={schedule_type}, T={num_timesteps})")

    def _load_cache_index(self):
        """Load cache index from disk."""
        index_path = self.cache_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    index = json.load(f)
                logger.info(f"Loaded {len(index)} cached latent states")
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")

    def _save_cache_index(self):
        """Save cache index to disk."""
        index = {name: latent.to_dict() for name, latent in self._latent_cache.items()}
        index_path = self.cache_dir / "index.json"
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2, default=str)

    def get_alpha_at_timestep(self, timestep: int) -> Tuple[float, float]:
        """
        Get alpha values at specific timestep.

        Returns:
            sqrt_alpha: sqrt(alpha_bar_t) - coefficient for clean image
            sqrt_one_minus_alpha: sqrt(1 - alpha_bar_t) - coefficient for noise
        """
        t = min(max(timestep, 0), self.num_timesteps - 1)
        alpha_bar_t = self.alpha_bar[t]
        sqrt_alpha = np.sqrt(alpha_bar_t)
        sqrt_one_minus_alpha = np.sqrt(1.0 - alpha_bar_t)
        return sqrt_alpha, sqrt_one_minus_alpha

    def recover_noise_from_image(
        self,
        image: np.ndarray,
        x0_estimate: Optional[np.ndarray] = None,
        timestep: int = 50,
        alpha_t: Optional[float] = None
    ) -> np.ndarray:
        """
        Recover noise epsilon from generated image using diffusion equation.

        Mathematical basis (Aragon's key equation):
            x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon

        Inverting:
            epsilon = (x_t - sqrt(alpha_t) * x_0) / sqrt(1 - alpha_t)

        For late timesteps (low noise), x_t approx x_0, so we can use image as x_0.

        Args:
            image: Generated image as numpy array (H, W, 3) or (H, W, 4) uint8
            x0_estimate: Clean image estimate (if None, uses image itself)
            timestep: Which diffusion step to assume (higher = more noise)
            alpha_t: Override sqrt(alpha_bar_t) coefficient

        Returns:
            Recovered noise epsilon as numpy array
        """
        # Ensure float format
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0

        # Handle RGBA
        if image.ndim == 3 and image.shape[2] == 4:
            image = image[:, :, :3]

        # Get alpha coefficient
        if alpha_t is None:
            sqrt_alpha, sqrt_one_minus_alpha = self.get_alpha_at_timestep(timestep)
        else:
            sqrt_alpha = alpha_t
            sqrt_one_minus_alpha = np.sqrt(1.0 - alpha_t**2)

        # Use image as x_0 estimate if not provided
        if x0_estimate is None:
            x0_estimate = image
        elif x0_estimate.dtype == np.uint8:
            x0_estimate = x0_estimate.astype(np.float32) / 255.0

        # Normalize to diffusion range [-1, 1]
        x_t = image * 2.0 - 1.0
        x_0 = x0_estimate * 2.0 - 1.0

        # Recover noise: epsilon = (x_t - sqrt(alpha_t) * x_0) / sqrt(1 - alpha_t)
        # Add small epsilon to avoid division by zero for very early timesteps
        epsilon = (x_t - sqrt_alpha * x_0) / (sqrt_one_minus_alpha + 1e-8)

        return epsilon

    def apply_noise_to_image(
        self,
        image: np.ndarray,
        noise: np.ndarray,
        timestep: int = 50,
        alpha_t: Optional[float] = None
    ) -> np.ndarray:
        """
        Apply noise to image using diffusion forward process.

        x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon

        Args:
            image: Clean image (H, W, 3) uint8 or float
            noise: Noise to apply (same shape as image)
            timestep: Target timestep
            alpha_t: Override alpha coefficient

        Returns:
            Noised image as uint8 array
        """
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0

        if alpha_t is None:
            sqrt_alpha, sqrt_one_minus_alpha = self.get_alpha_at_timestep(timestep)
        else:
            sqrt_alpha = alpha_t
            sqrt_one_minus_alpha = np.sqrt(1.0 - alpha_t**2)

        # Normalize to [-1, 1]
        x_0 = image * 2.0 - 1.0

        # Forward diffusion
        x_t = sqrt_alpha * x_0 + sqrt_one_minus_alpha * noise

        # Back to [0, 1] then uint8
        x_t = (x_t + 1.0) / 2.0
        x_t = np.clip(x_t, 0, 1)
        return (x_t * 255).astype(np.uint8)

    def create_style_latent(
        self,
        image: np.ndarray,
        name: str,
        model_id: str = "unknown",
        provider: str = "unknown",
        generation_params: Optional[Dict[str, Any]] = None,
        timestep: int = 50,
        description: Optional[str] = None,
        style_fingerprint: Optional[np.ndarray] = None,
        fingerprint_model: Optional[str] = None,
    ) -> LatentState:
        """
        Create a reusable style latent from a reference image.

        This captures the "style essence" that can guide future generations.

        Args:
            image: Reference image as numpy array
            name: Unique name for this style
            model_id: ID of model that generated the image
            provider: Provider name (huggingface, together, etc.)
            generation_params: Original generation parameters
            timestep: Diffusion timestep for noise recovery
            description: Human-readable description
            style_fingerprint: Optional visual embedding from TPU
            fingerprint_model: Model used for fingerprinting

        Returns:
            LatentState object (also cached for reuse)
        """
        # Recover noise from image
        noise = self.recover_noise_from_image(image, timestep=timestep)

        # Compute image hash for verification
        if image.dtype == np.uint8:
            image_bytes = image.tobytes()
        else:
            image_bytes = (image * 255).astype(np.uint8).tobytes()
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]

        # Get alpha at timestep
        sqrt_alpha, _ = self.get_alpha_at_timestep(timestep)

        # Create latent state
        latent = LatentState(
            noise_recovered=noise,
            image_hash=image_hash,
            timestep=timestep,
            alpha_t=float(sqrt_alpha),
            schedule_type=self.schedule_type,
            model_id=model_id,
            provider=provider,
            style_fingerprint=style_fingerprint,
            fingerprint_model=fingerprint_model,
            generation_params=generation_params or {},
            name=name,
            description=description,
        )

        # Cache in memory
        self._latent_cache[name] = latent

        # Persist to disk
        self._save_latent(name, latent)
        self._save_cache_index()

        logger.info(f"Created style latent '{name}' from {model_id} (hash={image_hash})")
        return latent

    def apply_style_latent(
        self,
        target_prompt: str,
        style_name: str,
        strength: float = 0.7,
        extract_style_cues: bool = True,
    ) -> StyleTransferResult:
        """
        Apply a cached style latent to guide new generation.

        This is "sidecar control" - we don't modify the model, we provide
        guided parameters (seed, prompt modifications) based on recovered latents.

        Args:
            target_prompt: New prompt for generation
            style_name: Name of cached style latent
            strength: Blend strength (0=no style, 1=full style)
            extract_style_cues: Add style keywords from original prompt

        Returns:
            StyleTransferResult with guided parameters
        """
        if style_name not in self._latent_cache:
            # Try loading from disk
            latent = self._load_latent(style_name)
            if latent is None:
                raise ValueError(f"Style '{style_name}' not found in cache")
        else:
            latent = self._latent_cache[style_name]

        # Generate DETERMINISTIC random noise based on style + prompt
        # This ensures same style + same prompt always yields same result
        deterministic_seed_str = f"{style_name}:{target_prompt}:{strength}"
        deterministic_seed = int(hashlib.sha256(deterministic_seed_str.encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(deterministic_seed)
        random_noise = rng.randn(*latent.noise_recovered.shape)

        guided_noise = (
            strength * latent.noise_recovered +
            (1 - strength) * random_noise
        )

        # Convert noise to deterministic seed
        # Hash the noise sum to get a reproducible seed
        noise_hash = hashlib.sha256(guided_noise.tobytes()).hexdigest()
        guided_seed = int(noise_hash[:8], 16) % (2**31)

        # Build guided prompt
        guided_prompt = target_prompt
        if extract_style_cues and latent.generation_params.get("prompt"):
            original_prompt = latent.generation_params["prompt"]
            # Extract last few words as style descriptors
            words = original_prompt.split()
            if len(words) > 3:
                style_cues = " ".join(words[-3:])
                guided_prompt = f"{target_prompt}, in the style of {style_cues}"

        # Build result parameters
        params = {
            "seed": guided_seed,
            "model": latent.model_id,
            "_latent_guided": True,
            "_style_source": style_name,
            "_guidance_strength": strength,
        }

        # Copy relevant generation params
        for key in ["negative_prompt", "guidance_scale", "num_inference_steps"]:
            if key in latent.generation_params:
                params[key] = latent.generation_params[key]

        return StyleTransferResult(
            guided_prompt=guided_prompt,
            guided_seed=guided_seed,
            guidance_strength=strength,
            source_style=style_name,
            original_prompt=target_prompt,
            params=params,
        )

    def cross_model_transfer(
        self,
        source_image: np.ndarray,
        source_model: str,
        target_model: str,
        target_prompt: str,
        strength: float = 0.8,
    ) -> StyleTransferResult:
        """
        Transfer latent style from one model to another.

        This enables "capability arbitrage" - generate high-quality in one model,
        apply style to faster/cheaper model.

        Example: Flux.1-dev quality -> SDXL-turbo speed

        Args:
            source_image: Image from source model
            source_model: Source model ID
            target_model: Target model ID
            target_prompt: Prompt for target generation
            strength: Style transfer strength

        Returns:
            StyleTransferResult for target model
        """
        # Create temporary style latent
        temp_name = f"_transfer_{hashlib.sha256(source_image.tobytes()).hexdigest()[:8]}"

        latent = self.create_style_latent(
            image=source_image,
            name=temp_name,
            model_id=source_model,
            generation_params={"prompt": target_prompt},
            timestep=50,
        )

        # Apply to target
        result = self.apply_style_latent(
            target_prompt=target_prompt,
            style_name=temp_name,
            strength=strength,
            extract_style_cues=False,
        )

        # Update params for target model
        result.params["model"] = target_model
        result.params["_cross_model_transfer"] = True
        result.params["_source_model"] = source_model

        return result

    def interpolate_styles(
        self,
        style_a: str,
        style_b: str,
        alpha: float = 0.5,
        target_prompt: str = "",
    ) -> StyleTransferResult:
        """
        Blend two cached styles via latent interpolation.

        This creates novel styles by navigating the constraint surface
        between two known points.

        Args:
            style_a: First style name
            style_b: Second style name
            alpha: Blend factor (0=all A, 1=all B)
            target_prompt: Prompt for generation

        Returns:
            StyleTransferResult with blended style
        """
        # Load both latents
        if style_a not in self._latent_cache:
            self._load_latent(style_a)
        if style_b not in self._latent_cache:
            self._load_latent(style_b)

        if style_a not in self._latent_cache or style_b not in self._latent_cache:
            raise ValueError(f"Styles not found: {style_a}, {style_b}")

        latent_a = self._latent_cache[style_a]
        latent_b = self._latent_cache[style_b]

        # Check shape compatibility
        if latent_a.noise_recovered.shape != latent_b.noise_recovered.shape:
            raise ValueError(
                f"Shape mismatch: {latent_a.noise_recovered.shape} vs "
                f"{latent_b.noise_recovered.shape}"
            )

        # Interpolate noise in latent space
        blended_noise = (1 - alpha) * latent_a.noise_recovered + alpha * latent_b.noise_recovered

        # Create blended latent
        blend_name = f"_blend_{style_a}_{style_b}_{int(alpha*100)}"
        blended = LatentState(
            noise_recovered=blended_noise,
            image_hash=f"blend_{latent_a.image_hash}_{latent_b.image_hash}",
            timestep=latent_a.timestep,
            alpha_t=(1 - alpha) * latent_a.alpha_t + alpha * latent_b.alpha_t,
            schedule_type=latent_a.schedule_type,
            model_id=latent_a.model_id,
            provider=latent_a.provider,
            generation_params={"prompt": target_prompt},
            name=blend_name,
            description=f"Blend of {style_a} and {style_b} at alpha={alpha}",
        )

        self._latent_cache[blend_name] = blended

        # Generate result
        return self.apply_style_latent(
            target_prompt=target_prompt,
            style_name=blend_name,
            strength=0.9,
            extract_style_cues=False,
        )

    def compute_style_similarity(
        self,
        style_a: str,
        style_b: str,
    ) -> float:
        """
        Compute similarity between two style latents.

        Uses cosine similarity in noise space.

        Args:
            style_a: First style name
            style_b: Second style name

        Returns:
            Similarity score (0-1, higher = more similar)
        """
        if style_a not in self._latent_cache:
            self._load_latent(style_a)
        if style_b not in self._latent_cache:
            self._load_latent(style_b)

        latent_a = self._latent_cache[style_a]
        latent_b = self._latent_cache[style_b]

        # Flatten and compute cosine similarity
        a_flat = latent_a.noise_recovered.flatten()
        b_flat = latent_b.noise_recovered.flatten()

        # Cosine similarity
        dot = np.dot(a_flat, b_flat)
        norm_a = np.linalg.norm(a_flat)
        norm_b = np.linalg.norm(b_flat)

        similarity = dot / (norm_a * norm_b + 1e-8)

        # Convert from [-1, 1] to [0, 1]
        return (similarity + 1) / 2

    def list_cached_styles(self) -> List[Dict[str, Any]]:
        """List all cached style latents."""
        # Refresh from disk
        self._scan_cache_dir()
        return [latent.to_dict() for latent in self._latent_cache.values()]

    def delete_style(self, name: str) -> bool:
        """Delete a cached style latent."""
        if name in self._latent_cache:
            del self._latent_cache[name]

        latent_path = self.cache_dir / f"{name}.latent"
        if latent_path.exists():
            latent_path.unlink()
            self._save_cache_index()
            return True
        return False

    def _save_latent(self, name: str, latent: LatentState):
        """Persist latent to disk."""
        path = self.cache_dir / f"{name}.latent"
        with open(path, 'wb') as f:
            pickle.dump(latent, f)
        logger.debug(f"Saved latent: {path}")

    def _load_latent(self, name: str) -> Optional[LatentState]:
        """Load latent from disk."""
        path = self.cache_dir / f"{name}.latent"
        if not path.exists():
            return None
        try:
            with open(path, 'rb') as f:
                latent = pickle.load(f)
            self._latent_cache[name] = latent
            return latent
        except Exception as e:
            logger.warning(f"Failed to load latent {name}: {e}")
            return None

    def _scan_cache_dir(self):
        """Scan cache directory for latent files."""
        for path in self.cache_dir.glob("*.latent"):
            name = path.stem
            if name not in self._latent_cache:
                self._load_latent(name)


def image_from_base64(b64_string: str) -> np.ndarray:
    """Convert base64 image to numpy array."""
    from PIL import Image
    image_bytes = base64.b64decode(b64_string)
    image = Image.open(io.BytesIO(image_bytes))
    return np.array(image)


def image_to_base64(image: np.ndarray, format: str = "PNG") -> str:
    """Convert numpy array to base64 string."""
    from PIL import Image
    if image.dtype != np.uint8:
        image = (np.clip(image, 0, 1) * 255).astype(np.uint8)
    pil_image = Image.fromarray(image)
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
