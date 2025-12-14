#!/usr/bin/env python3
"""
PySR Symbolic Regression Integration for AGI Memory System

This module uses PySR to discover interpretable mathematical equations from
memory patterns, consolidation metrics, and system behavior. It enables the
AGI system to learn mathematical laws governing its own operation.

Key Capabilities:
- Discover equations predicting memory importance from metadata
- Model memory access patterns and predict future access
- Find mathematical relationships in consolidation effectiveness
- Learn equations governing pattern frequency and success
- Model performance bottlenecks and optimization targets
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json

logger = logging.getLogger("pysr-symbolic-regression")

# Check PySR availability
try:
    from pysr import PySRRegressor
    import sympy
    PYSR_AVAILABLE = True
    logger.info("PySR symbolic regression available (v1.5.9)")
except ImportError:
    PYSR_AVAILABLE = False
    logger.warning("PySR not available - symbolic regression features disabled")

# Memory database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class SymbolicRegressionEngine:
    """
    PySR-powered symbolic regression for discovering mathematical patterns
    in the AGI memory system.
    """

    def __init__(self):
        self.models: Dict[str, PySRRegressor] = {}
        self.equations: Dict[str, str] = {}
        self.model_dir = MEMORY_DIR / "pysr_models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def discover_importance_equation(
        self,
        min_samples: int = 50,
        max_complexity: int = 15
    ) -> Dict[str, Any]:
        """
        Discover mathematical equation predicting memory importance scores.

        Features used:
        - access_count: How often memory is accessed
        - content_length: Length of memory content
        - num_tags: Number of tags
        - age_hours: Age in hours
        - tier_numeric: Memory tier (encoded)

        Returns:
            Dictionary with equation, accuracy, and model info
        """
        if not PYSR_AVAILABLE:
            return {"error": "PySR not available"}

        logger.info("Discovering importance score equation...")

        # Fetch memory data
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                importance_score,
                access_count,
                LENGTH(content) as content_length,
                tier,
                created_at,
                updated_at
            FROM entities
            WHERE importance_score IS NOT NULL
        """)

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < min_samples:
            return {
                "error": f"Insufficient data: {len(rows)} samples (need {min_samples})",
                "samples_available": len(rows)
            }

        # Prepare features
        data = []
        for row in rows:
            mem_id, importance, access_count, content_len, tier, created_at, updated_at = row

            # Calculate age in hours
            try:
                created = datetime.fromisoformat(created_at)
                age_hours = (datetime.now() - created).total_seconds() / 3600
            except:
                age_hours = 0

            # Encode tier
            tier_map = {"working": 0, "episodic": 1, "semantic": 2, "procedural": 3}
            tier_numeric = tier_map.get(tier, 0)

            # Count tags (would need to parse JSON, simplified here)
            num_tags = 0

            data.append({
                "importance_score": importance,
                "access_count": access_count or 0,
                "content_length": content_len or 0,
                "num_tags": num_tags,
                "age_hours": age_hours,
                "tier_numeric": tier_numeric
            })

        df = pd.DataFrame(data)

        # Prepare X (features) and y (target)
        feature_cols = ["access_count", "content_length", "num_tags", "age_hours", "tier_numeric"]
        X = df[feature_cols].values
        y = df["importance_score"].values

        logger.info(f"Training on {len(X)} samples with {len(feature_cols)} features")

        # Configure PySR
        model = PySRRegressor(
            niterations=50,  # Moderate iteration count
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "log", "sqrt"],
            maxsize=max_complexity,
            populations=15,
            population_size=33,
            ncyclesperiteration=550,
            procs=4,  # Use 4 processes
            verbosity=0,
            random_state=42,
            equation_file=str(self.model_dir / "importance_equation.csv")
        )

        # Fit model
        logger.info("Starting PySR equation search...")
        model.fit(X, y)

        # Get best equation
        best_equation = model.sympy()
        equation_str = str(best_equation)

        # Get accuracy metrics
        r2_score = model.score(X, y)

        # Store model
        self.models["importance"] = model
        self.equations["importance"] = equation_str

        # Save model
        model_path = self.model_dir / "importance_model.pkl"
        model.save(str(model_path))

        logger.info(f"Discovered equation: {equation_str}")
        logger.info(f"R² score: {r2_score:.4f}")

        return {
            "success": True,
            "equation": equation_str,
            "equation_latex": sympy.latex(best_equation),
            "r2_score": r2_score,
            "samples_used": len(X),
            "features": feature_cols,
            "model_path": str(model_path),
            "timestamp": datetime.now().isoformat()
        }

    def discover_consolidation_equation(
        self,
        min_samples: int = 20,
        max_complexity: int = 12
    ) -> Dict[str, Any]:
        """
        Discover equation predicting consolidation effectiveness.

        Features:
        - time_window_hours: Consolidation time window
        - entity_count: Number of entities processed
        - patterns_found: Patterns discovered
        - memories_promoted: Memories promoted to semantic

        Target:
        - effectiveness_score: patterns_found / entity_count

        Returns:
            Dictionary with equation and metrics
        """
        if not PYSR_AVAILABLE:
            return {"error": "PySR not available"}

        logger.info("Discovering consolidation effectiveness equation...")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get consolidation job history
        cursor.execute("""
            SELECT
                job_type,
                entity_count,
                patterns_found,
                memories_promoted,
                chains_created,
                links_created,
                duration_seconds,
                time_window_start,
                time_window_end
            FROM consolidation_jobs
            WHERE status = 'completed' AND entity_count > 0
        """)

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < min_samples:
            return {
                "error": f"Insufficient consolidation data: {len(rows)} samples (need {min_samples})",
                "samples_available": len(rows)
            }

        # Prepare data
        data = []
        for row in rows:
            job_type, entity_count, patterns, promoted, chains, links, duration, start, end = row

            # Calculate time window
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                time_window_hours = (end_dt - start_dt).total_seconds() / 3600
            except:
                time_window_hours = 24

            # Calculate effectiveness score
            patterns = patterns or 0
            promoted = promoted or 0
            chains = chains or 0
            links = links or 0

            effectiveness = (patterns + promoted + chains + links) / max(entity_count, 1)

            data.append({
                "time_window_hours": time_window_hours,
                "entity_count": entity_count,
                "patterns_found": patterns,
                "memories_promoted": promoted,
                "effectiveness_score": effectiveness
            })

        df = pd.DataFrame(data)

        feature_cols = ["time_window_hours", "entity_count", "patterns_found", "memories_promoted"]
        X = df[feature_cols].values
        y = df["effectiveness_score"].values

        logger.info(f"Training consolidation model on {len(X)} samples")

        # Configure PySR for consolidation
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "log"],
            maxsize=max_complexity,
            populations=10,
            population_size=25,
            ncyclesperiteration=500,
            procs=4,
            verbosity=0,
            random_state=42,
            equation_file=str(self.model_dir / "consolidation_equation.csv")
        )

        model.fit(X, y)

        best_equation = model.sympy()
        equation_str = str(best_equation)
        r2_score = model.score(X, y)

        self.models["consolidation"] = model
        self.equations["consolidation"] = equation_str

        model_path = self.model_dir / "consolidation_model.pkl"
        model.save(str(model_path))

        logger.info(f"Consolidation equation: {equation_str}")
        logger.info(f"R² score: {r2_score:.4f}")

        return {
            "success": True,
            "equation": equation_str,
            "equation_latex": sympy.latex(best_equation),
            "r2_score": r2_score,
            "samples_used": len(X),
            "features": feature_cols,
            "model_path": str(model_path),
            "timestamp": datetime.now().isoformat()
        }

    def discover_access_pattern_equation(
        self,
        min_samples: int = 100,
        max_complexity: int = 10
    ) -> Dict[str, Any]:
        """
        Discover equation predicting memory access frequency.

        This helps predict which memories will be accessed in the future.

        Features:
        - importance_score
        - age_hours
        - historical_access_rate (access_count / age_hours)
        - tier_numeric

        Target:
        - access_count (log-transformed)
        """
        if not PYSR_AVAILABLE:
            return {"error": "PySR not available"}

        logger.info("Discovering access pattern equation...")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                access_count,
                importance_score,
                tier,
                created_at
            FROM entities
            WHERE access_count > 0 AND importance_score IS NOT NULL
        """)

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < min_samples:
            return {
                "error": f"Insufficient access data: {len(rows)} samples (need {min_samples})",
                "samples_available": len(rows)
            }

        data = []
        for row in rows:
            access_count, importance, tier, created_at = row

            try:
                created = datetime.fromisoformat(created_at)
                age_hours = max(1, (datetime.now() - created).total_seconds() / 3600)
            except:
                age_hours = 1

            tier_map = {"working": 0, "episodic": 1, "semantic": 2, "procedural": 3}
            tier_numeric = tier_map.get(tier, 0)

            access_rate = access_count / age_hours

            data.append({
                "importance_score": importance,
                "age_hours": age_hours,
                "access_rate": access_rate,
                "tier_numeric": tier_numeric,
                "log_access_count": np.log1p(access_count)  # log(1 + x) transformation
            })

        df = pd.DataFrame(data)

        feature_cols = ["importance_score", "age_hours", "access_rate", "tier_numeric"]
        X = df[feature_cols].values
        y = df["log_access_count"].values

        logger.info(f"Training access pattern model on {len(X)} samples")

        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["log", "exp", "sqrt"],
            maxsize=max_complexity,
            populations=12,
            population_size=30,
            ncyclesperiteration=500,
            procs=4,
            verbosity=0,
            random_state=42,
            equation_file=str(self.model_dir / "access_pattern_equation.csv")
        )

        model.fit(X, y)

        best_equation = model.sympy()
        equation_str = str(best_equation)
        r2_score = model.score(X, y)

        self.models["access_pattern"] = model
        self.equations["access_pattern"] = equation_str

        model_path = self.model_dir / "access_pattern_model.pkl"
        model.save(str(model_path))

        logger.info(f"Access pattern equation: {equation_str}")
        logger.info(f"R² score: {r2_score:.4f}")

        return {
            "success": True,
            "equation": equation_str,
            "equation_latex": sympy.latex(best_equation),
            "r2_score": r2_score,
            "samples_used": len(X),
            "features": feature_cols,
            "model_path": str(model_path),
            "timestamp": datetime.now().isoformat()
        }

    def predict_importance(self, features: Dict[str, float]) -> Optional[float]:
        """
        Predict importance score using discovered equation.

        Args:
            features: Dictionary with keys matching feature names

        Returns:
            Predicted importance score or None
        """
        if "importance" not in self.models:
            logger.warning("Importance model not trained yet")
            return None

        model = self.models["importance"]
        feature_cols = ["access_count", "content_length", "num_tags", "age_hours", "tier_numeric"]

        X = np.array([[features.get(col, 0) for col in feature_cols]])
        prediction = model.predict(X)[0]

        # Clamp to [0, 1]
        return max(0.0, min(1.0, prediction))

    def get_all_equations(self) -> Dict[str, str]:
        """Get all discovered equations as human-readable strings."""
        return self.equations.copy()

    def load_saved_models(self) -> Dict[str, bool]:
        """Load previously saved PySR models from disk."""
        loaded = {}

        model_files = {
            "importance": "importance_model.pkl",
            "consolidation": "consolidation_model.pkl",
            "access_pattern": "access_pattern_model.pkl"
        }

        for name, filename in model_files.items():
            model_path = self.model_dir / filename
            if model_path.exists():
                try:
                    model = PySRRegressor.from_file(str(model_path))
                    self.models[name] = model
                    self.equations[name] = str(model.sympy())
                    loaded[name] = True
                    logger.info(f"Loaded {name} model: {self.equations[name]}")
                except Exception as e:
                    logger.error(f"Failed to load {name} model: {e}")
                    loaded[name] = False
            else:
                loaded[name] = False

        return loaded

    def run_full_discovery(self) -> Dict[str, Any]:
        """
        Run full symbolic regression discovery pipeline.

        Discovers equations for:
        1. Memory importance prediction
        2. Consolidation effectiveness
        3. Access pattern prediction

        Returns:
            Combined results from all discoveries
        """
        results = {
            "started_at": datetime.now().isoformat(),
            "pysr_available": PYSR_AVAILABLE
        }

        if not PYSR_AVAILABLE:
            results["error"] = "PySR not available"
            return results

        logger.info("Starting full symbolic regression discovery...")

        # 1. Importance equation
        try:
            importance_result = self.discover_importance_equation()
            results["importance"] = importance_result
        except Exception as e:
            logger.error(f"Importance discovery failed: {e}")
            results["importance"] = {"error": str(e)}

        # 2. Consolidation equation
        try:
            consolidation_result = self.discover_consolidation_equation()
            results["consolidation"] = consolidation_result
        except Exception as e:
            logger.error(f"Consolidation discovery failed: {e}")
            results["consolidation"] = {"error": str(e)}

        # 3. Access pattern equation
        try:
            access_result = self.discover_access_pattern_equation()
            results["access_pattern"] = access_result
        except Exception as e:
            logger.error(f"Access pattern discovery failed: {e}")
            results["access_pattern"] = {"error": str(e)}

        results["completed_at"] = datetime.now().isoformat()

        logger.info("Full symbolic regression discovery complete")

        return results


# Singleton instance
_engine: Optional[SymbolicRegressionEngine] = None


def get_engine() -> SymbolicRegressionEngine:
    """Get or create singleton SymbolicRegressionEngine."""
    global _engine
    if _engine is None:
        _engine = SymbolicRegressionEngine()
        # Try to load existing models
        _engine.load_saved_models()
    return _engine
