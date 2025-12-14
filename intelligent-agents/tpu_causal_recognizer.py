#!/usr/bin/env python3
"""
TPU Causal Pattern Recognizer - Edge TPU Accelerated Causal Discovery

Recognizes causal patterns in system events using semantic embeddings.
Identifies cause-effect relationships for predictive reasoning and
root cause analysis.

Integration with enhanced-memory causal chain tracking.

Usage:
    from tpu_causal_recognizer import TPUCausalRecognizer

    recognizer = TPUCausalRecognizer()

    # Analyze potential causation
    causation = await recognizer.analyze_causation(
        cause="Memory usage increased to 90%",
        effect="Application became unresponsive",
        context="High load testing"
    )
    print(f"Causal strength: {causation.strength:.2f}")

    # Predict effects
    effects = await recognizer.predict_effects(
        cause="Deployed new caching layer",
        context="Production environment"
    )
"""
import platform

import os
import sys
import json
import time
import logging
import sqlite3
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_causal_recognizer")

# TPU imports
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
except ImportError:
    pass

try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


# Database for causal patterns
DB_PATH = Path(AGENTIC_SYSTEM_PATH) / "databases" / "causal_patterns.db"


@dataclass
class CausalLink:
    """A learned cause-effect relationship"""
    link_id: str
    cause_description: str
    effect_description: str
    strength: float  # 0.0-1.0, how reliably cause leads to effect
    confidence: float  # Confidence in this relationship
    occurrences: int  # Times observed
    typical_delay_seconds: Optional[float]  # Typical time between cause and effect
    context_conditions: List[str]  # Conditions under which this holds
    cause_embedding: Optional[np.ndarray] = None
    effect_embedding: Optional[np.ndarray] = None


@dataclass
class CausationAnalysis:
    """Analysis of potential causation"""
    cause: str
    effect: str
    strength: float  # Estimated causal strength
    confidence: float  # Confidence in analysis
    mechanism: str  # Hypothesized mechanism
    similar_patterns: List[CausalLink]  # Similar known patterns
    alternative_causes: List[Tuple[str, float]]  # Other possible causes
    risk_of_spurious: float  # Risk this is spurious correlation
    latency_ms: float


@dataclass
class EffectPrediction:
    """Predicted effects of a cause"""
    cause: str
    predicted_effects: List[Tuple[str, float]]  # (effect, probability)
    confidence: float
    reasoning: str
    similar_causes: List[Tuple[CausalLink, float]]
    latency_ms: float


# Causal mechanism templates
MECHANISM_TEMPLATES = {
    "resource_exhaustion": (
        "Resource depletion leads to system degradation. "
        "Memory, CPU, disk, or network resources becoming insufficient."
    ),
    "cascade_failure": (
        "One failure triggering subsequent failures. "
        "Domino effect through dependent components."
    ),
    "configuration_change": (
        "Configuration modification affecting system behavior. "
        "Settings changes propagating to functionality."
    ),
    "code_change": (
        "Code modification introducing new behavior. "
        "Bug introduction or fix affecting system."
    ),
    "load_increase": (
        "Increased demand causing performance issues. "
        "Traffic spikes, batch jobs, or user activity."
    ),
    "external_dependency": (
        "External service affecting internal system. "
        "API failures, network issues, third-party problems."
    ),
    "timing_race": (
        "Race condition or timing-related issue. "
        "Concurrency problems, synchronization failures."
    ),
    "data_corruption": (
        "Data integrity issues causing problems. "
        "Invalid data propagating through system."
    ),
    "security_event": (
        "Security-related cause and effect. "
        "Authentication, authorization, or attack-related."
    ),
    "environmental": (
        "Environmental factors affecting system. "
        "Temperature, power, hardware issues."
    )
}


def _ensure_db():
    """Ensure database exists with proper schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS causal_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT UNIQUE NOT NULL,
            cause_description TEXT NOT NULL,
            effect_description TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            occurrences INTEGER DEFAULT 1,
            typical_delay_seconds REAL,
            context_conditions TEXT,
            cause_embedding BLOB,
            effect_embedding BLOB,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_causal_strength ON causal_links(strength)
    ''')

    conn.commit()
    conn.close()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUCausalRecognizer:
    """
    Recognize and analyze causal patterns using TPU embeddings.

    Uses semantic similarity to match events to known causal patterns
    and infer causation between novel events.
    """

    def __init__(self):
        _ensure_db()
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Precompute mechanism embeddings
        self._mechanism_embeddings = self._precompute_mechanisms()

        if self.use_tpu:
            logger.info("TPU causal recognition enabled")
        else:
            logger.info("Using fallback causal recognition")

    def _precompute_mechanisms(self) -> Dict[str, np.ndarray]:
        """Precompute embeddings for causal mechanisms."""
        mechanisms = {}
        if not self.use_tpu or not _embed_text:
            return mechanisms

        for name, description in MECHANISM_TEMPLATES.items():
            try:
                embedding = _embed_text(description)
                if embedding is not None:
                    mechanisms[name] = np.array(embedding, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Failed to embed mechanism {name}: {e}")

        logger.info(f"Precomputed {len(mechanisms)} mechanism templates")
        return mechanisms

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
        cache_key = str(hash(text))
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            start = time.perf_counter()
            embedding = _embed_text(text)
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[cache_key] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "causal_embedding",
                        latency_ms=latency,
                        source="causal_recognizer"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _get_known_patterns(self, min_strength: float = 0.3) -> List[CausalLink]:
        """Get known causal patterns from database."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT link_id, cause_description, effect_description, strength,
                   confidence, occurrences, typical_delay_seconds,
                   context_conditions, cause_embedding, effect_embedding
            FROM causal_links
            WHERE strength >= ?
            ORDER BY strength DESC, occurrences DESC
            LIMIT 100
        ''', (min_strength,))

        patterns = []
        for row in cursor.fetchall():
            try:
                cause_emb = np.frombuffer(row[8], dtype=np.float32) if row[8] else None
                effect_emb = np.frombuffer(row[9], dtype=np.float32) if row[9] else None
                conditions = json.loads(row[7]) if row[7] else []

                patterns.append(CausalLink(
                    link_id=row[0],
                    cause_description=row[1],
                    effect_description=row[2],
                    strength=row[3],
                    confidence=row[4],
                    occurrences=row[5],
                    typical_delay_seconds=row[6],
                    context_conditions=conditions,
                    cause_embedding=cause_emb,
                    effect_embedding=effect_emb
                ))
            except Exception:
                continue

        conn.close()
        return patterns

    def _identify_mechanism(
        self,
        cause: str,
        effect: str,
        cause_emb: np.ndarray,
        effect_emb: np.ndarray
    ) -> str:
        """Identify the likely causal mechanism."""
        if not self._mechanism_embeddings:
            return "unknown"

        # Combine cause and effect for mechanism matching
        combined_text = f"{cause} causes {effect}"
        combined_emb = self._get_embedding(combined_text)

        if combined_emb is None:
            return "unknown"

        best_mechanism = "unknown"
        best_similarity = 0.0

        for mechanism, mech_emb in self._mechanism_embeddings.items():
            similarity = cosine_similarity(combined_emb, mech_emb)
            if similarity > best_similarity:
                best_similarity = similarity
                best_mechanism = mechanism

        return best_mechanism if best_similarity > 0.4 else "unknown"

    def _estimate_spurious_risk(
        self,
        cause_emb: np.ndarray,
        effect_emb: np.ndarray,
        similar_patterns: List[CausalLink]
    ) -> float:
        """Estimate risk of spurious correlation."""
        # Low similarity between cause and effect = higher spurious risk
        direct_similarity = cosine_similarity(cause_emb, effect_emb)

        # Few similar patterns = higher risk
        pattern_support = min(1.0, len(similar_patterns) / 5)

        # Risk calculation
        risk = 0.5 * (1.0 - direct_similarity) + 0.5 * (1.0 - pattern_support)

        return min(1.0, max(0.0, risk))

    async def analyze_causation(
        self,
        cause: str,
        effect: str,
        context: Optional[str] = None,
        time_delay_seconds: Optional[float] = None
    ) -> CausationAnalysis:
        """
        Analyze potential causation between two events.

        Args:
            cause: Description of potential cause
            effect: Description of observed effect
            context: Additional context
            time_delay_seconds: Time between cause and effect

        Returns:
            CausationAnalysis with strength, mechanism, and alternatives
        """
        start_time = time.perf_counter()

        # Get embeddings
        cause_emb = self._get_embedding(cause)
        effect_emb = self._get_embedding(effect)

        if cause_emb is None or effect_emb is None:
            return self._fallback_analysis(cause, effect)

        # Get known patterns
        known_patterns = self._get_known_patterns()

        # Find similar patterns
        similar_patterns = []
        for pattern in known_patterns:
            if pattern.cause_embedding is not None:
                cause_sim = cosine_similarity(cause_emb, pattern.cause_embedding)
                if pattern.effect_embedding is not None:
                    effect_sim = cosine_similarity(effect_emb, pattern.effect_embedding)
                    combined_sim = (cause_sim + effect_sim) / 2
                    if combined_sim > 0.5:
                        similar_patterns.append(pattern)

        # Calculate causal strength
        if similar_patterns:
            # Average strength of similar patterns, weighted by similarity
            avg_strength = np.mean([p.strength for p in similar_patterns])
            strength = avg_strength
            confidence = min(1.0, len(similar_patterns) / 5)
        else:
            # No similar patterns - use heuristics
            direct_sim = cosine_similarity(cause_emb, effect_emb)
            strength = 0.3 + 0.3 * direct_sim  # Base + similarity bonus
            confidence = 0.3

        # Identify mechanism
        mechanism = self._identify_mechanism(cause, effect, cause_emb, effect_emb)

        # Find alternative causes (causes similar to known patterns' causes)
        alternative_causes = []
        for pattern in known_patterns[:20]:
            if pattern.effect_embedding is not None:
                effect_sim = cosine_similarity(effect_emb, pattern.effect_embedding)
                if effect_sim > 0.6 and pattern.cause_description != cause:
                    alternative_causes.append(
                        (pattern.cause_description, effect_sim * pattern.strength)
                    )

        alternative_causes.sort(key=lambda x: x[1], reverse=True)
        alternative_causes = alternative_causes[:5]

        # Estimate spurious correlation risk
        spurious_risk = self._estimate_spurious_risk(cause_emb, effect_emb, similar_patterns)

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "causation_analysis",
                latency_ms=latency_ms,
                source="causal_recognizer",
                metadata={
                    "strength": strength,
                    "mechanism": mechanism
                }
            )

        return CausationAnalysis(
            cause=cause,
            effect=effect,
            strength=strength,
            confidence=confidence,
            mechanism=mechanism,
            similar_patterns=similar_patterns[:5],
            alternative_causes=alternative_causes,
            risk_of_spurious=spurious_risk,
            latency_ms=latency_ms
        )

    def _fallback_analysis(self, cause: str, effect: str) -> CausationAnalysis:
        """Fallback when TPU unavailable."""
        # Keyword-based heuristics
        causal_keywords = {
            ("memory", "crash"): 0.7,
            ("load", "slow"): 0.6,
            ("deploy", "error"): 0.5,
            ("config", "behavior"): 0.6,
            ("bug", "issue"): 0.5
        }

        strength = 0.4
        combined = f"{cause} {effect}".lower()

        for (kw1, kw2), score in causal_keywords.items():
            if kw1 in combined and kw2 in combined:
                strength = max(strength, score)

        return CausationAnalysis(
            cause=cause,
            effect=effect,
            strength=strength,
            confidence=0.3,
            mechanism="unknown",
            similar_patterns=[],
            alternative_causes=[],
            risk_of_spurious=0.5,
            latency_ms=0.0
        )

    async def predict_effects(
        self,
        cause: str,
        context: Optional[str] = None,
        top_k: int = 5
    ) -> EffectPrediction:
        """
        Predict likely effects of a cause.

        Args:
            cause: Description of the cause
            context: Additional context
            top_k: Number of effects to predict

        Returns:
            EffectPrediction with predicted effects and probabilities
        """
        start_time = time.perf_counter()

        cause_emb = self._get_embedding(cause)

        if cause_emb is None:
            return EffectPrediction(
                cause=cause,
                predicted_effects=[],
                confidence=0.0,
                reasoning="TPU unavailable for prediction",
                similar_causes=[],
                latency_ms=0.0
            )

        # Find similar causes in known patterns
        known_patterns = self._get_known_patterns()
        similar_causes = []

        for pattern in known_patterns:
            if pattern.cause_embedding is not None:
                similarity = cosine_similarity(cause_emb, pattern.cause_embedding)
                if similarity > 0.4:
                    similar_causes.append((pattern, similarity))

        similar_causes.sort(key=lambda x: x[1], reverse=True)
        similar_causes = similar_causes[:top_k * 2]

        # Collect predicted effects
        effect_scores: Dict[str, float] = defaultdict(float)

        for pattern, similarity in similar_causes:
            # Weight effect by similarity and pattern strength
            score = similarity * pattern.strength
            effect_scores[pattern.effect_description] = max(
                effect_scores[pattern.effect_description],
                score
            )

        # Sort effects by score
        predicted_effects = sorted(
            effect_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Calculate confidence
        if similar_causes:
            confidence = min(1.0, len(similar_causes) / 5) * max(
                s for _, s in similar_causes
            )
        else:
            confidence = 0.2

        # Build reasoning
        if similar_causes:
            top_cause = similar_causes[0][0]
            reasoning = f"Based on similar pattern: {top_cause.cause_description[:50]}..."
        else:
            reasoning = "Limited matching patterns found"

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "effect_prediction",
                latency_ms=latency_ms,
                source="causal_recognizer",
                metadata={"predictions": len(predicted_effects)}
            )

        return EffectPrediction(
            cause=cause,
            predicted_effects=predicted_effects,
            confidence=confidence,
            reasoning=reasoning,
            similar_causes=similar_causes[:5],
            latency_ms=latency_ms
        )

    def record_causal_observation(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5,
        delay_seconds: Optional[float] = None,
        context_conditions: Optional[List[str]] = None
    ) -> str:
        """
        Record an observed causal relationship.

        Args:
            cause: Cause description
            effect: Effect description
            strength: Observed causal strength
            delay_seconds: Time between cause and effect
            context_conditions: Conditions for this relationship

        Returns:
            link_id
        """
        import uuid

        link_id = str(uuid.uuid4())[:8]

        # Get embeddings
        cause_emb = self._get_embedding(cause)
        effect_emb = self._get_embedding(effect)

        cause_bytes = cause_emb.tobytes() if cause_emb is not None else None
        effect_bytes = effect_emb.tobytes() if effect_emb is not None else None
        conditions_json = json.dumps(context_conditions or [])

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Check for existing similar pattern
        cursor.execute('''
            SELECT id, occurrences, strength FROM causal_links
            WHERE cause_description = ? AND effect_description = ?
        ''', (cause, effect))

        existing = cursor.fetchone()

        if existing:
            # Update existing pattern
            new_occurrences = existing[1] + 1
            # Rolling average of strength
            new_strength = (existing[2] * existing[1] + strength) / new_occurrences

            cursor.execute('''
                UPDATE causal_links
                SET occurrences = ?, strength = ?, updated_at = ?,
                    cause_embedding = COALESCE(cause_embedding, ?),
                    effect_embedding = COALESCE(effect_embedding, ?)
                WHERE id = ?
            ''', (new_occurrences, new_strength, now, cause_bytes, effect_bytes, existing[0]))

            link_id = str(existing[0])
        else:
            cursor.execute('''
                INSERT INTO causal_links
                (link_id, cause_description, effect_description, strength,
                 confidence, occurrences, typical_delay_seconds,
                 context_conditions, cause_embedding, effect_embedding,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                link_id, cause, effect, strength, 0.5, 1,
                delay_seconds, conditions_json,
                cause_bytes, effect_bytes, now, now
            ))

        conn.commit()
        conn.close()

        logger.info(f"Recorded causal pattern: {cause[:30]}... -> {effect[:30]}...")
        return link_id

    async def discover_patterns(
        self,
        events: List[Tuple[str, datetime]],
        max_delay_seconds: float = 300
    ) -> List[CausalLink]:
        """
        Discover causal patterns from a sequence of events.

        Args:
            events: List of (description, timestamp) tuples
            max_delay_seconds: Maximum delay to consider causal

        Returns:
            Discovered causal links
        """
        if len(events) < 2:
            return []

        # Sort by time
        events = sorted(events, key=lambda x: x[1])

        # Embed all events
        event_embeddings = []
        for desc, ts in events:
            emb = self._get_embedding(desc)
            event_embeddings.append((desc, ts, emb))

        discovered = []

        # Look for potential causal pairs
        for i, (cause_desc, cause_time, cause_emb) in enumerate(event_embeddings):
            if cause_emb is None:
                continue

            for effect_desc, effect_time, effect_emb in event_embeddings[i+1:]:
                if effect_emb is None:
                    continue

                delay = (effect_time - cause_time).total_seconds()

                if delay > max_delay_seconds:
                    break  # Events too far apart

                # Check similarity to known patterns
                analysis = await self.analyze_causation(
                    cause_desc, effect_desc,
                    time_delay_seconds=delay
                )

                if analysis.strength > 0.5 and analysis.risk_of_spurious < 0.5:
                    discovered.append(CausalLink(
                        link_id=f"discovered_{i}",
                        cause_description=cause_desc,
                        effect_description=effect_desc,
                        strength=analysis.strength,
                        confidence=analysis.confidence,
                        occurrences=1,
                        typical_delay_seconds=delay,
                        context_conditions=[],
                        cause_embedding=cause_emb,
                        effect_embedding=effect_emb
                    ))

        return discovered

    def get_statistics(self) -> Dict[str, Any]:
        """Get recognizer statistics."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM causal_links')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT AVG(strength) FROM causal_links')
        avg_strength = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT SUM(occurrences) FROM causal_links')
        total_observations = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "tpu_available": self.use_tpu,
            "total_patterns": total,
            "avg_strength": avg_strength,
            "total_observations": total_observations,
            "mechanisms_loaded": len(self._mechanism_embeddings),
            "cache_size": len(self._embedding_cache)
        }


# CLI
if __name__ == "__main__":
    import asyncio
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="TPU Causal Pattern Recognizer")
    parser.add_argument("command", choices=["analyze", "predict", "record", "stats"],
                       help="Command to run")
    parser.add_argument("--cause", "-c", type=str, help="Cause description")
    parser.add_argument("--effect", "-e", type=str, help="Effect description")
    parser.add_argument("--strength", "-s", type=float, default=0.5, help="Causal strength")

    args = parser.parse_args()

    recognizer = TPUCausalRecognizer()

    if args.command == "analyze":
        if not args.cause or not args.effect:
            print("Error: --cause and --effect required")
            sys.exit(1)

        analysis = asyncio.run(recognizer.analyze_causation(args.cause, args.effect))
        print(json.dumps({
            "strength": analysis.strength,
            "confidence": analysis.confidence,
            "mechanism": analysis.mechanism,
            "spurious_risk": analysis.risk_of_spurious,
            "similar_patterns": len(analysis.similar_patterns),
            "alternative_causes": len(analysis.alternative_causes),
            "latency_ms": analysis.latency_ms
        }, indent=2))

    elif args.command == "predict":
        if not args.cause:
            print("Error: --cause required")
            sys.exit(1)

        prediction = asyncio.run(recognizer.predict_effects(args.cause))
        print(json.dumps({
            "predicted_effects": prediction.predicted_effects,
            "confidence": prediction.confidence,
            "reasoning": prediction.reasoning,
            "latency_ms": prediction.latency_ms
        }, indent=2))

    elif args.command == "record":
        if not args.cause or not args.effect:
            print("Error: --cause and --effect required")
            sys.exit(1)

        link_id = recognizer.record_causal_observation(
            args.cause, args.effect, args.strength
        )
        print(f"Recorded: {link_id}")

    elif args.command == "stats":
        stats = recognizer.get_statistics()
        print(json.dumps(stats, indent=2))
