#!/usr/bin/env python3
"""
MLX Configuration for Agentic System

Production-ready MLX integration for the autonomous agentic system,
optimized for Apple Silicon (M2 Max) with Metal GPU acceleration.

Usage:
    from mlx_config import MLXConfig, mlx_array, mlx_load_lm

Environment Variables:
    MLX_MEMORY_LIMIT: Maximum memory for MLX (default: auto)
    MLX_CACHE_DIR: Cache directory for models (default: ~/.cache/mlx)
"""

import os
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLXConfig:
    """Production MLX configuration and utilities for agentic system."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        memory_limit: Optional[int] = None,
        enable_profiling: bool = False
    ):
        """Initialize MLX configuration with production settings."""
        try:
            self.cache_dir = cache_dir or Path.home() / ".cache" / "mlx"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create cache directory: {e}")

        self.memory_limit = memory_limit
        self.enable_profiling = enable_profiling

        self._load_env_config()
        self.device_info = self._get_device_info()
        logger.info(f"MLX initialized with cache at {self.cache_dir}")

    def _load_env_config(self):
        """Load configuration from environment variables."""
        try:
            if env_limit := os.getenv("MLX_MEMORY_LIMIT"):
                self.memory_limit = int(env_limit)
                logger.info(f"Memory limit set to {self.memory_limit} MB")

            if env_cache := os.getenv("MLX_CACHE_DIR"):
                self.cache_dir = Path(env_cache)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Cache directory set to {self.cache_dir}")
        except ValueError as e:
            logger.error(f"Invalid environment variable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load environment config: {e}")
            raise

    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        return {
            "device": "Metal (Apple Silicon)",
            "cache_dir": str(self.cache_dir),
            "memory_limit": self.memory_limit or "auto",
        }

    def create_array(
        self,
        data: Union[List, tuple, mx.array],
        dtype: Optional[mx.Dtype] = None
    ) -> mx.array:
        """Create MLX array with unified memory."""
        try:
            if isinstance(data, mx.array):
                return data

            arr = mx.array(data, dtype=dtype)
            mx.eval(arr)
            return arr
        except Exception as e:
            raise RuntimeError(f"Failed to create MLX array: {e}")

    def to_numpy(self, arr: mx.array):
        """Convert MLX array to NumPy (zero-copy when possible)."""
        try:
            import numpy as np
            if not isinstance(arr, mx.array):
                raise TypeError(f"Expected mx.array, got {type(arr)}")
            return np.array(arr)
        except Exception as e:
            raise RuntimeError(f"Failed to convert to NumPy: {e}")

    def save_model(self, model: nn.Module, path: Union[str, Path]):
        """Save MLX model weights."""
        try:
            if not isinstance(model, nn.Module):
                raise ValueError(f"Expected nn.Module, got {type(model)}")

            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            weights = model.parameters()
            mx.savez(str(path), **weights)
            logger.info(f"Model saved to {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to save model: {e}")

    def load_model(self, model: nn.Module, path: Union[str, Path]):
        """Load MLX model weights."""
        try:
            if not isinstance(model, nn.Module):
                raise ValueError(f"Expected nn.Module, got {type(model)}")

            path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")

            weights = mx.load(str(path))
            model.load_weights(list(weights.items()))
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")


class MLXModelLoader:
    """Production model loader for the agentic system."""

    def __init__(self, config: MLXConfig):
        """Initialize model loader with configuration."""
        if not isinstance(config, MLXConfig):
            raise TypeError(f"Expected MLXConfig, got {type(config)}")
        self.config = config
        self.loaded_models = {}

    def load_language_model(
        self,
        model_name: str,
        quantize: bool = False
    ) -> Dict[str, Any]:
        """Load language model with mlx-lm."""
        try:
            if not model_name or not model_name.strip():
                raise ValueError("Model name cannot be empty")

            try:
                from mlx_lm import load
            except ImportError:
                raise ImportError("mlx-lm not installed. Run: pip install mlx-lm")

            logger.info(f"Loading model: {model_name}")
            model, tokenizer = load(model_name)

            model_info = {
                "model": model,
                "tokenizer": tokenizer,
                "name": model_name,
                "quantized": quantize
            }

            self.loaded_models[model_name] = model_info
            logger.info(f"Model loaded successfully: {model_name}")
            return model_info

        except ImportError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load model {model_name}: {e}")

    def unload_model(self, model_name: str):
        """Unload model from memory."""
        try:
            if model_name not in self.loaded_models:
                raise KeyError(f"Model not loaded: {model_name}")
            del self.loaded_models[model_name]
            logger.info(f"Model unloaded: {model_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to unload model: {e}")


class MLXKaggleUtilities:
    """Production MLX utilities for Kaggle competitions."""

    def __init__(self, config: MLXConfig):
        """Initialize Kaggle utilities."""
        if not isinstance(config, MLXConfig):
            raise TypeError(f"Expected MLXConfig, got {type(config)}")
        self.config = config

    def preprocess_dataset(
        self,
        data: Union[List, mx.array],
        normalize: bool = True,
        dtype: mx.Dtype = mx.float32
    ) -> mx.array:
        """Preprocess dataset for ML training."""
        try:
            if not data or (isinstance(data, (list, tuple)) and len(data) == 0):
                raise ValueError("Data cannot be empty")

            arr = self.config.create_array(data, dtype=dtype)

            if normalize:
                mean = mx.mean(arr, axis=0, keepdims=True)
                std = mx.std(arr, axis=0, keepdims=True)
                arr = (arr - mean) / (std + 1e-8)
                mx.eval(arr)

            return arr
        except Exception as e:
            raise RuntimeError(f"Failed to preprocess dataset: {e}")

    def train_test_split(
        self,
        X: mx.array,
        y: mx.array,
        test_size: float = 0.2,
        random_state: Optional[int] = None
    ) -> tuple:
        """Split data into train and test sets."""
        try:
            if not 0.0 < test_size < 1.0:
                raise ValueError(f"test_size must be between 0 and 1, got {test_size}")

            if X.shape[0] != y.shape[0]:
                raise ValueError(f"X and y must have same first dimension: {X.shape[0]} != {y.shape[0]}")

            if random_state is not None:
                mx.random.seed(random_state)

            n_samples = X.shape[0]
            n_test = int(n_samples * test_size)

            if n_test == 0 or n_test == n_samples:
                raise ValueError(f"Invalid split: test_size={test_size} results in empty set")

            indices = mx.random.permutation(n_samples)
            test_idx = indices[:n_test]
            train_idx = indices[n_test:]

            X_train = X[train_idx]
            X_test = X[test_idx]
            y_train = y[train_idx]
            y_test = y[test_idx]

            mx.eval(X_train, X_test, y_train, y_test)

            logger.info(f"Split: {X_train.shape[0]} train, {X_test.shape[0]} test")
            return X_train, X_test, y_train, y_test

        except Exception as e:
            raise RuntimeError(f"Failed to split dataset: {e}")

    def create_model(
        self,
        input_dim: int,
        hidden_dims: List[int],
        output_dim: int,
        activation: str = "relu"
    ) -> nn.Module:
        """Create feedforward neural network."""
        try:
            if input_dim <= 0:
                raise ValueError(f"input_dim must be > 0, got {input_dim}")
            if output_dim <= 0:
                raise ValueError(f"output_dim must be > 0, got {output_dim}")
            if not hidden_dims:
                raise ValueError("hidden_dims cannot be empty")
            if any(d <= 0 for d in hidden_dims):
                raise ValueError("All hidden dimensions must be > 0")
            if activation not in ("relu", "gelu"):
                raise ValueError(f"Activation must be 'relu' or 'gelu', got '{activation}'")

            layers = []
            prev_dim = input_dim

            for hidden_dim in hidden_dims:
                layers.append(nn.Linear(prev_dim, hidden_dim))
                if activation == "relu":
                    layers.append(nn.ReLU())
                elif activation == "gelu":
                    layers.append(nn.GELU())
                prev_dim = hidden_dim

            layers.append(nn.Linear(prev_dim, output_dim))

            model = nn.Sequential(*layers)
            logger.info(f"Created model: {input_dim} -> {hidden_dims} -> {output_dim}")
            return model

        except Exception as e:
            raise RuntimeError(f"Failed to create model: {e}")

    def train_model(
        self,
        model: nn.Module,
        X_train: mx.array,
        y_train: mx.array,
        epochs: int = 10,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """Train MLX model with mini-batch gradient descent."""
        try:
            if not isinstance(model, nn.Module):
                raise ValueError(f"Expected nn.Module, got {type(model)}")
            if epochs <= 0:
                raise ValueError(f"epochs must be > 0, got {epochs}")
            if batch_size <= 0:
                raise ValueError(f"batch_size must be > 0, got {batch_size}")
            if learning_rate <= 0:
                raise ValueError(f"learning_rate must be > 0, got {learning_rate}")
            if X_train.shape[0] != y_train.shape[0]:
                raise ValueError(f"X_train and y_train must have same first dimension")

            optimizer = optim.Adam(learning_rate=learning_rate)
            history = {"loss": []}

            def loss_fn(model, X, y):
                return mx.mean((model(X) - y) ** 2)

            loss_and_grad_fn = nn.value_and_grad(model, loss_fn)

            n_samples = X_train.shape[0]
            n_batches = (n_samples + batch_size - 1) // batch_size

            logger.info(f"Training: {epochs} epochs, {n_batches} batches/epoch")

            for epoch in range(epochs):
                epoch_loss = 0.0

                indices = mx.random.permutation(n_samples)
                X_shuffled = X_train[indices]
                y_shuffled = y_train[indices]

                for batch_idx in range(n_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, n_samples)

                    X_batch = X_shuffled[start_idx:end_idx]
                    y_batch = y_shuffled[start_idx:end_idx]

                    loss, grads = loss_and_grad_fn(model, X_batch, y_batch)
                    optimizer.update(model, grads)
                    mx.eval(model.parameters(), optimizer.state)

                    epoch_loss += loss.item()

                avg_loss = epoch_loss / n_batches
                history["loss"].append(avg_loss)

                if verbose:
                    print(f"Epoch {epoch + 1}/{epochs} - Loss: {avg_loss:.6f}")

            logger.info("Training completed successfully")
            return history

        except Exception as e:
            raise RuntimeError(f"Training failed: {e}")


_global_config = None
_global_model_loader = None
_global_kaggle_utils = None


def get_mlx_config() -> MLXConfig:
    """Get global MLX configuration instance (singleton)."""
    global _global_config
    if _global_config is None:
        _global_config = MLXConfig()
    return _global_config


def get_model_loader() -> MLXModelLoader:
    """Get global model loader instance (singleton)."""
    global _global_model_loader
    if _global_model_loader is None:
        _global_model_loader = MLXModelLoader(get_mlx_config())
    return _global_model_loader


def get_kaggle_utils() -> MLXKaggleUtilities:
    """Get global Kaggle utilities instance (singleton)."""
    global _global_kaggle_utils
    if _global_kaggle_utils is None:
        _global_kaggle_utils = MLXKaggleUtilities(get_mlx_config())
    return _global_kaggle_utils


def mlx_array(data, dtype=None) -> mx.array:
    """Create MLX array (convenience function)."""
    return get_mlx_config().create_array(data, dtype=dtype)


def mlx_load_lm(model_name: str, quantize: bool = False):
    """Load language model (convenience function)."""
    return get_model_loader().load_language_model(model_name, quantize=quantize)


__all__ = [
    "MLXConfig",
    "MLXModelLoader",
    "MLXKaggleUtilities",
    "get_mlx_config",
    "get_model_loader",
    "get_kaggle_utils",
    "mlx_array",
    "mlx_load_lm",
]
