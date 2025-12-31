"""
Configuration classes for the router package.

Extracted from model_router.py for better organization.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import RoutingMode


@dataclass
class ProviderConfig:
    """Provider configuration."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    models: Optional[Dict[str, str]] = None  # default, fast, advanced
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[Dict[str, int]] = None
    preferences: Optional[Dict[str, Any]] = None
    # ONNX/Local specific
    model_path: Optional[str] = None
    execution_providers: Optional[List[str]] = None
    local_inference: bool = False
    gpu_acceleration: bool = False


@dataclass
class RoutingRule:
    """Routing rule definition."""
    condition: Dict[str, Any]  # agent_type, requires_tools, complexity, privacy
    action: Dict[str, Any]     # provider, model, temperature, max_tokens
    reason: Optional[str] = None


@dataclass
class RoutingConfig:
    """Routing configuration."""
    mode: RoutingMode = RoutingMode.MANUAL
    rules: List[RoutingRule] = field(default_factory=list)
    cost_optimization: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enabled: bool = True
    log_level: str = "info"
    track_cost: bool = True
    track_latency: bool = True
    track_tokens: bool = True
    track_errors: bool = True
    alerts: Optional[Dict[str, float]] = None


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = False
    ttl: int = 3600
    max_size: int = 1000
    strategy: str = "lru"


@dataclass
class UncertaintyConfig:
    """Configuration for uncertainty estimation.

    Ported from ruvector/crates/ruvector-tiny-dancer-core/src/uncertainty.rs
    Uses conformal prediction concepts for reliable uncertainty quantification.
    """
    calibration_quantile: float = 0.9  # 90% confidence default
    min_samples_for_calibration: int = 30
    boundary_threshold: float = 0.5  # Decision boundary
    enable_calibration: bool = True


@dataclass
class RouterConfig:
    """Full router configuration."""
    version: str = "1.0.0"
    default_provider: "ProviderType" = None  # Forward reference, set default in __post_init__
    fallback_chain: List["ProviderType"] = field(default_factory=list)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    routing: Optional[RoutingConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    cache: Optional[CacheConfig] = None

    def __post_init__(self):
        # Import here to avoid circular import
        from .models import ProviderType
        if self.default_provider is None:
            self.default_provider = ProviderType.ANTHROPIC
