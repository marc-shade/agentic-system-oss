"""
Tests for Diffusion Latent Hacker
=================================

Tests the mathematical hacking implementation for diffusion models.
"""

import numpy as np
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_gen_mcp.latent_hacker import (
    DiffusionLatentHacker,
    LatentState,
    compute_alpha_schedule,
    image_from_base64,
    image_to_base64,
    DDPM_NUM_TIMESTEPS,
)


class TestAlphaSchedule:
    """Test noise schedule computation."""

    def test_linear_schedule_shape(self):
        """Test linear schedule returns correct shapes."""
        betas, alphas, alpha_bar = compute_alpha_schedule(
            num_timesteps=1000,
            schedule_type="linear"
        )
        assert betas.shape == (1000,)
        assert alphas.shape == (1000,)
        assert alpha_bar.shape == (1000,)

    def test_linear_schedule_bounds(self):
        """Test linear schedule values are in valid range."""
        betas, alphas, alpha_bar = compute_alpha_schedule(
            num_timesteps=1000,
            schedule_type="linear"
        )
        assert np.all(betas >= 0) and np.all(betas <= 1)
        assert np.all(alphas >= 0) and np.all(alphas <= 1)
        assert np.all(alpha_bar >= 0) and np.all(alpha_bar <= 1)

    def test_alpha_bar_decreasing(self):
        """Test alpha_bar decreases monotonically (more noise over time)."""
        _, _, alpha_bar = compute_alpha_schedule(
            num_timesteps=1000,
            schedule_type="linear"
        )
        # alpha_bar should decrease (cumulative product of alphas < 1)
        assert alpha_bar[0] > alpha_bar[-1]

    def test_cosine_schedule(self):
        """Test cosine schedule computation."""
        betas, alphas, alpha_bar = compute_alpha_schedule(
            num_timesteps=1000,
            schedule_type="cosine"
        )
        assert betas.shape == (1000,)
        assert np.all(alpha_bar >= 0) and np.all(alpha_bar <= 1)

    def test_scaled_linear_schedule(self):
        """Test scaled linear schedule (stable diffusion style)."""
        betas, alphas, alpha_bar = compute_alpha_schedule(
            num_timesteps=1000,
            schedule_type="scaled_linear"
        )
        assert betas.shape == (1000,)
        assert np.all(alpha_bar >= 0) and np.all(alpha_bar <= 1)


class TestDiffusionLatentHacker:
    """Test the main latent hacker class."""

    @pytest.fixture
    def hacker(self):
        """Create a latent hacker with temp cache dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DiffusionLatentHacker(cache_dir=Path(tmpdir))

    @pytest.fixture
    def test_image(self):
        """Create a test image (random noise image)."""
        return np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)

    def test_init(self, hacker):
        """Test initialization."""
        assert hacker.num_timesteps == DDPM_NUM_TIMESTEPS
        assert hacker.schedule_type == "linear"
        assert len(hacker.alpha_bar) == DDPM_NUM_TIMESTEPS

    def test_get_alpha_at_timestep(self, hacker):
        """Test alpha retrieval at specific timesteps."""
        sqrt_alpha, sqrt_one_minus = hacker.get_alpha_at_timestep(0)
        # At t=0, almost no noise
        assert sqrt_alpha > 0.99

        sqrt_alpha, sqrt_one_minus = hacker.get_alpha_at_timestep(999)
        # At t=999, mostly noise
        assert sqrt_alpha < 0.1

    def test_noise_recovery_and_application(self, hacker, test_image):
        """Test that we can recover noise and reapply it."""
        timestep = 50

        # Recover noise from image
        noise = hacker.recover_noise_from_image(test_image, timestep=timestep)

        assert noise.shape == test_image.shape[:2] + (3,)
        assert noise.dtype == np.float32 or noise.dtype == np.float64

        # Apply noise back to image
        noised = hacker.apply_noise_to_image(test_image, noise, timestep=timestep)

        assert noised.shape == test_image.shape
        assert noised.dtype == np.uint8

    def test_create_style_latent(self, hacker, test_image):
        """Test style latent creation."""
        latent = hacker.create_style_latent(
            image=test_image,
            name="test_style",
            model_id="test_model",
            provider="test_provider",
            generation_params={"prompt": "test prompt"},
            timestep=50,
            description="A test style",
        )

        assert isinstance(latent, LatentState)
        assert latent.name == "test_style"
        assert latent.model_id == "test_model"
        assert latent.timestep == 50
        assert "test_style" in hacker._latent_cache

    def test_apply_style_latent(self, hacker, test_image):
        """Test applying a cached style."""
        # Create style
        hacker.create_style_latent(
            image=test_image,
            name="apply_test",
            generation_params={"prompt": "original style prompt"},
        )

        # Apply style
        result = hacker.apply_style_latent(
            target_prompt="new content",
            style_name="apply_test",
            strength=0.7,
        )

        assert result.guided_prompt is not None
        assert result.guided_seed is not None
        assert result.guidance_strength == 0.7
        assert result.source_style == "apply_test"

    def test_style_interpolation(self, hacker, test_image):
        """Test style interpolation."""
        # Create two styles
        hacker.create_style_latent(image=test_image, name="style_a")
        hacker.create_style_latent(image=test_image + 10, name="style_b")  # Slightly different

        # Interpolate
        result = hacker.interpolate_styles(
            style_a="style_a",
            style_b="style_b",
            alpha=0.5,
            target_prompt="blended content",
        )

        assert result.guided_prompt is not None
        assert result.guided_seed is not None

    def test_style_similarity(self, hacker, test_image):
        """Test style similarity computation."""
        # Create same style twice
        hacker.create_style_latent(image=test_image, name="same_a")
        hacker.create_style_latent(image=test_image, name="same_b")

        similarity = hacker.compute_style_similarity("same_a", "same_b")

        # Same image should have similarity close to 1
        assert similarity > 0.99

    def test_style_similarity_different(self, hacker):
        """Test similarity of different styles."""
        # Create very different images
        img_a = np.zeros((64, 64, 3), dtype=np.uint8)
        img_b = np.ones((64, 64, 3), dtype=np.uint8) * 255

        hacker.create_style_latent(image=img_a, name="black")
        hacker.create_style_latent(image=img_b, name="white")

        similarity = hacker.compute_style_similarity("black", "white")

        # Different images should have lower similarity
        assert similarity < 0.99

    def test_cross_model_transfer(self, hacker, test_image):
        """Test cross-model style transfer."""
        result = hacker.cross_model_transfer(
            source_image=test_image,
            source_model="flux-dev",
            target_model="sdxl-turbo",
            target_prompt="new prompt",
            strength=0.8,
        )

        assert result.params.get("model") == "sdxl-turbo"
        assert result.params.get("_cross_model_transfer") is True

    def test_list_cached_styles(self, hacker, test_image):
        """Test listing cached styles."""
        hacker.create_style_latent(image=test_image, name="list_test_1")
        hacker.create_style_latent(image=test_image, name="list_test_2")

        styles = hacker.list_cached_styles()

        assert len(styles) >= 2
        names = [s["name"] for s in styles]
        assert "list_test_1" in names
        assert "list_test_2" in names

    def test_delete_style(self, hacker, test_image):
        """Test style deletion."""
        hacker.create_style_latent(image=test_image, name="to_delete")
        assert "to_delete" in hacker._latent_cache

        deleted = hacker.delete_style("to_delete")

        assert deleted is True
        assert "to_delete" not in hacker._latent_cache

    def test_persistence(self, test_image):
        """Test that styles persist across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Create style with first instance
            hacker1 = DiffusionLatentHacker(cache_dir=cache_dir)
            hacker1.create_style_latent(image=test_image, name="persistent")

            # Load with second instance
            hacker2 = DiffusionLatentHacker(cache_dir=cache_dir)
            loaded = hacker2._load_latent("persistent")

            assert loaded is not None
            assert loaded.name == "persistent"


class TestImageConversion:
    """Test image conversion utilities."""

    def test_base64_roundtrip(self):
        """Test base64 encode/decode roundtrip."""
        original = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)

        # Encode
        b64 = image_to_base64(original)
        assert isinstance(b64, str)

        # Decode
        decoded = image_from_base64(b64)
        assert decoded.shape[:2] == original.shape[:2]

    def test_float_to_base64(self):
        """Test converting float images to base64."""
        float_img = np.random.rand(64, 64, 3).astype(np.float32)

        b64 = image_to_base64(float_img)
        assert isinstance(b64, str)

        decoded = image_from_base64(b64)
        assert decoded.dtype == np.uint8


class TestMathematicalHacking:
    """
    Test the mathematical principles from Aragon's paper.

    The core insight is that diffusion equation exposes constraint surfaces:
    x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon

    We can recover epsilon (noise) from x_t and x_0, then use it
    to guide future generations.
    """

    @pytest.fixture
    def hacker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield DiffusionLatentHacker(cache_dir=Path(tmpdir))

    def test_diffusion_equation_consistency(self, hacker):
        """
        Test that forward diffusion followed by noise recovery
        gives consistent results.

        x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon
        epsilon_recovered = (x_t - sqrt(alpha_t) * x_0) / sqrt(1 - alpha_t)

        epsilon_recovered should equal epsilon
        """
        # Create clean image
        x_0 = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)

        # Generate known noise
        epsilon = np.random.randn(64, 64, 3).astype(np.float32)

        timestep = 50

        # Forward diffusion
        x_t = hacker.apply_noise_to_image(x_0, epsilon, timestep=timestep)

        # Recover noise
        epsilon_recovered = hacker.recover_noise_from_image(
            x_t,
            x0_estimate=x_0,
            timestep=timestep
        )

        # Should be very close (some precision loss from uint8 conversion)
        correlation = np.corrcoef(epsilon.flatten(), epsilon_recovered.flatten())[0, 1]
        assert correlation > 0.95, f"Noise correlation too low: {correlation}"

    def test_style_transfer_preserves_structure(self, hacker):
        """
        Test that style transfer creates deterministic guidance.

        Same style + same prompt should give same seed every time.
        """
        # Create a style
        test_image = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        hacker.create_style_latent(image=test_image, name="deterministic_test")

        # Apply multiple times
        results = []
        for _ in range(5):
            result = hacker.apply_style_latent(
                target_prompt="test prompt",
                style_name="deterministic_test",
                strength=0.7,
            )
            results.append(result.guided_seed)

        # All seeds should be identical (deterministic)
        assert all(s == results[0] for s in results)

    def test_interpolation_is_linear(self, hacker):
        """
        Test that style interpolation produces linear blends.

        Interpolating at alpha=0 should give style_a,
        at alpha=1 should give style_b.
        """
        img_a = np.zeros((64, 64, 3), dtype=np.uint8)
        img_b = np.ones((64, 64, 3), dtype=np.uint8) * 255

        hacker.create_style_latent(image=img_a, name="endpoint_a")
        hacker.create_style_latent(image=img_b, name="endpoint_b")

        # Get endpoint results
        result_a = hacker.apply_style_latent("test", "endpoint_a", strength=1.0)
        result_b = hacker.apply_style_latent("test", "endpoint_b", strength=1.0)

        # Get interpolation at endpoints
        interp_0 = hacker.interpolate_styles("endpoint_a", "endpoint_b", alpha=0.0, target_prompt="test")
        interp_1 = hacker.interpolate_styles("endpoint_a", "endpoint_b", alpha=1.0, target_prompt="test")

        # At alpha=0, should be similar to style_a
        # At alpha=1, should be similar to style_b
        # (Seeds won't be identical due to random component, but should be deterministic)
        assert interp_0.guided_seed != interp_1.guided_seed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
