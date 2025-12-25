"""
Activation Field Module - Holographic Memory Implementation

Implements persistent memory activation state that influences all processing
without explicit retrieval. This is the "holographic" model vs "filing cabinet" model.

Key Concepts (from YouTube video analysis):
1. Memory is DISTRIBUTED - partial recall still influences behavior
2. Memory RESHAPES behavior, doesn't just store/retrieve
3. Damage degrades fidelity, not identity (graceful degradation)
4. Experience changes future decisions unconsciously (priming)

Architecture:
- Computed ONCE per interaction from context
- Persists across tool calls within the interaction
- Automatically influences: routing, confidence, attention, priming
- No explicit retrieval needed - memory modulates behavior implicitly

Integration Points:
- AssociativeNetwork.spread_activation() - spreads activation through links
- EmotionalMemory - provides valence/arousal context
- ForgettingCurve - applies decay to activation levels
- ModelRouter - receives routing_bias for model selection
"""

import sqlite3
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from math import exp, sqrt
import threading

logger = logging.getLogger("activation-field")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Activation field parameters
DEFAULT_DECAY_RATE = 0.1  # How fast activation decays per hour
DEFAULT_SPREAD_DEPTH = 3  # How many hops to spread activation
DEFAULT_ACTIVATION_THRESHOLD = 0.2  # Minimum activation to consider
ROUTING_INFLUENCE_WEIGHT = 0.3  # How much memory influences routing
CONFIDENCE_INFLUENCE_WEIGHT = 0.2  # How much memory influences confidence


@dataclass
class ActivationState:
    """
    Persistent activation state computed from context.

    This represents the "holographic" memory field - a distributed
    representation that influences all downstream processing.
    """

    # Core activation state
    routing_bias: Dict[str, float] = field(default_factory=dict)
    """Model → weight adjustment. Positive = prefer, negative = avoid."""

    confidence_modifier: float = 1.0
    """Global confidence scaling based on memory familiarity. >1 = familiar territory, <1 = novel."""

    attention_weights: Dict[int, float] = field(default_factory=dict)
    """Entity ID → attention weight. Higher = more relevant to current context."""

    emotional_context: Dict[str, float] = field(default_factory=lambda: {
        "valence": 0.0,     # -1 (negative) to +1 (positive)
        "arousal": 0.5,     # 0 (calm) to 1 (excited)
        "dominance": 0.5    # 0 (controlled) to 1 (in control)
    })
    """Current emotional modulation from memory context."""

    primed_concepts: Set[str] = field(default_factory=set)
    """Subconsciously activated concepts - influence behavior without explicit retrieval."""

    active_entity_ids: Set[int] = field(default_factory=set)
    """Entity IDs that are currently activated in the field."""

    # Metadata
    context_hash: str = ""
    """Hash of context used to compute this field - for cache invalidation."""

    computed_at: str = ""
    """When this field was computed."""

    computation_time_ms: float = 0.0
    """How long computation took."""

    source_query: str = ""
    """The query that triggered this field computation."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "routing_bias": self.routing_bias,
            "confidence_modifier": self.confidence_modifier,
            "attention_weights": self.attention_weights,
            "emotional_context": self.emotional_context,
            "primed_concepts": list(self.primed_concepts),
            "active_entity_ids": list(self.active_entity_ids),
            "context_hash": self.context_hash,
            "computed_at": self.computed_at,
            "computation_time_ms": self.computation_time_ms,
            "source_query": self.source_query
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivationState":
        """Reconstruct from dictionary."""
        return cls(
            routing_bias=data.get("routing_bias", {}),
            confidence_modifier=data.get("confidence_modifier", 1.0),
            attention_weights=data.get("attention_weights", {}),
            emotional_context=data.get("emotional_context", {}),
            primed_concepts=set(data.get("primed_concepts", [])),
            active_entity_ids=set(data.get("active_entity_ids", [])),
            context_hash=data.get("context_hash", ""),
            computed_at=data.get("computed_at", ""),
            computation_time_ms=data.get("computation_time_ms", 0.0),
            source_query=data.get("source_query", "")
        )


class ActivationField:
    """
    Computes and maintains the holographic memory activation field.

    This is the core component that transforms our system from
    "filing cabinet" (store → retrieve → inject → hope) to
    "holographic" (memory automatically modulates behavior).

    Usage:
        field = ActivationField()

        # Compute activation field from context (once per interaction)
        state = field.compute_from_context(
            query="How do I optimize memory performance?",
            recent_entities=[...],  # Optional: recent interactions
            session_context={...}   # Optional: session metadata
        )

        # Field now influences behavior automatically:
        # - state.routing_bias adjusts model selection
        # - state.confidence_modifier scales confidence scores
        # - state.primed_concepts influence search/generation
        # - state.emotional_context colors responses
    """

    _instance: Optional["ActivationField"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - one activation field per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._current_state: Optional[ActivationState] = None
        self._state_lock = threading.Lock()
        self._initialized = True

        logger.info("ActivationField initialized (singleton)")

    @property
    def current_state(self) -> Optional[ActivationState]:
        """Get current activation state (thread-safe)."""
        with self._state_lock:
            return self._current_state

    @current_state.setter
    def current_state(self, state: ActivationState):
        """Set current activation state (thread-safe)."""
        with self._state_lock:
            self._current_state = state

    def compute_from_context(
        self,
        query: str,
        recent_entities: Optional[List[Dict[str, Any]]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        force_recompute: bool = False
    ) -> ActivationState:
        """
        Compute activation field from current context.

        This is the MAIN entry point. Call once at the start of an
        interaction, then the field automatically influences all
        downstream processing.

        Args:
            query: The current user query/context
            recent_entities: Recently accessed entities (for priming)
            session_context: Session metadata (task type, etc.)
            force_recompute: Bypass cache and recompute

        Returns:
            ActivationState with computed biases, priming, and modulation
        """
        import time
        start_time = time.time()

        # Check cache
        context_hash = self._compute_context_hash(query, session_context)
        if not force_recompute and self.current_state:
            if self.current_state.context_hash == context_hash:
                logger.debug("Using cached activation field")
                return self.current_state

        # Initialize new state
        state = ActivationState(
            context_hash=context_hash,
            computed_at=datetime.now().isoformat(),
            source_query=query
        )

        try:
            # Phase 1: Semantic activation spreading
            activated = self._spread_semantic_activation(query)
            state.active_entity_ids = set(activated.keys())
            state.attention_weights = activated

            # Phase 2: Extract primed concepts
            state.primed_concepts = self._extract_primed_concepts(
                query, activated, recent_entities
            )

            # Phase 3: Compute emotional context
            state.emotional_context = self._compute_emotional_context(activated)

            # Phase 4: Compute routing bias
            state.routing_bias = self._compute_routing_bias(
                query, activated, state.emotional_context, session_context
            )

            # Phase 5: Compute confidence modifier
            state.confidence_modifier = self._compute_confidence_modifier(
                activated, state.primed_concepts
            )

            # Record computation time
            state.computation_time_ms = (time.time() - start_time) * 1000

            # Store in memory for persistence tracking
            self._persist_activation_event(state)

            # Update current state
            self.current_state = state

            logger.info(
                f"Computed activation field: "
                f"{len(state.active_entity_ids)} entities, "
                f"{len(state.primed_concepts)} primed concepts, "
                f"confidence={state.confidence_modifier:.2f}, "
                f"in {state.computation_time_ms:.1f}ms"
            )

            return state

        except Exception as e:
            logger.error(f"Error computing activation field: {e}")
            # Return minimal valid state on error
            state.computation_time_ms = (time.time() - start_time) * 1000
            self.current_state = state
            return state

    def _compute_context_hash(
        self,
        query: str,
        session_context: Optional[Dict[str, Any]]
    ) -> str:
        """Compute hash for cache invalidation."""
        context_str = query + json.dumps(session_context or {}, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]

    def _spread_semantic_activation(
        self,
        query: str,
        max_depth: int = DEFAULT_SPREAD_DEPTH,
        threshold: float = DEFAULT_ACTIVATION_THRESHOLD
    ) -> Dict[int, float]:
        """
        Spread activation through associative network based on query.

        Returns:
            Dict of entity_id → activation_level
        """
        activations: Dict[int, float] = {}

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Step 1: Find seed entities matching query keywords
            keywords = self._extract_keywords(query)
            seed_entities = []

            for keyword in keywords[:10]:  # Limit to top 10 keywords
                # Search entities by name and entity_type
                cursor.execute(
                    '''
                    SELECT DISTINCT e.id, e.name, e.entity_type
                    FROM entities e
                    LEFT JOIN observations o ON e.id = o.entity_id
                    WHERE e.name LIKE ? OR e.entity_type LIKE ? OR o.content LIKE ?
                    LIMIT 5
                    ''',
                    (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
                )
                seed_entities.extend(cursor.fetchall())

            # Step 2: Spread activation from each seed
            for seed in seed_entities:
                # Handle both dict and tuple access patterns
                entity_id = seed[0] if isinstance(seed, tuple) else seed['id']
                initial_activation = 1.0 / len(seed_entities) if seed_entities else 0.0

                # Use BFS to spread activation
                visited = set()
                current_level = [(entity_id, initial_activation, 0)]

                while current_level:
                    next_level = []

                    for eid, activation, depth in current_level:
                        if depth >= max_depth or eid in visited:
                            continue

                        visited.add(eid)

                        # Accumulate activation
                        if eid in activations:
                            activations[eid] = min(1.0, activations[eid] + activation)
                        else:
                            activations[eid] = activation

                        if activation < threshold:
                            continue

                        # Get neighbors from associative network
                        cursor.execute(
                            '''
                            SELECT
                                CASE WHEN entity_a_id = ? THEN entity_b_id ELSE entity_a_id END as neighbor_id,
                                association_strength,
                                spread_decay
                            FROM memory_associations
                            WHERE entity_a_id = ? OR entity_b_id = ?
                            ''',
                            (eid, eid, eid)
                        )

                        for row in cursor.fetchall():
                            neighbor_id = row['neighbor_id']
                            strength = row['association_strength'] or 0.5
                            decay = row['spread_decay'] or 0.3

                            spread_activation = activation * strength * (1.0 - decay)
                            if spread_activation >= threshold:
                                next_level.append((neighbor_id, spread_activation, depth + 1))

                    current_level = next_level

            conn.close()

        except Exception as e:
            logger.error(f"Error in semantic activation spreading: {e}")

        return activations

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query for activation seeding."""
        # Remove common stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
            'because', 'until', 'while', 'what', 'which', 'who', 'whom',
            'this', 'that', 'these', 'those', 'am', 'i', 'me', 'my',
            'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its',
            'we', 'us', 'our', 'they', 'them', 'their'
        }

        # Tokenize and filter
        words = query.lower().split()
        keywords = [
            w.strip('.,!?;:()[]{}"\'-')
            for w in words
            if w.strip('.,!?;:()[]{}"\'-') not in stopwords
            and len(w.strip('.,!?;:()[]{}"\'-')) > 2
        ]

        return keywords

    def _extract_primed_concepts(
        self,
        query: str,
        activated: Dict[int, float],
        recent_entities: Optional[List[Dict[str, Any]]] = None
    ) -> Set[str]:
        """
        Extract concepts that are "primed" - subconsciously activated.

        These concepts influence behavior without explicit retrieval.
        """
        primed = set()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Get names of highly activated entities
            high_activation = [
                eid for eid, activation in activated.items()
                if activation > 0.5
            ]

            if high_activation:
                placeholders = ','.join('?' * len(high_activation))
                cursor.execute(
                    f'''
                    SELECT DISTINCT entity_type, name
                    FROM entities
                    WHERE id IN ({placeholders})
                    ''',
                    high_activation
                )

                for row in cursor.fetchall():
                    entity_type, name = row
                    primed.add(entity_type)
                    # Add significant name tokens
                    for token in name.split('_'):
                        if len(token) > 3:
                            primed.add(token.lower())

            # Add recent entity types as primed concepts
            if recent_entities:
                for entity in recent_entities[:5]:  # Top 5 recent
                    if 'entity_type' in entity:
                        primed.add(entity['entity_type'])

            conn.close()

        except Exception as e:
            logger.error(f"Error extracting primed concepts: {e}")

        return primed

    def _compute_emotional_context(
        self,
        activated: Dict[int, float]
    ) -> Dict[str, float]:
        """
        Compute emotional context from activated memories.

        Uses Russell's circumplex model (valence, arousal, dominance).
        """
        context = {
            "valence": 0.0,
            "arousal": 0.5,
            "dominance": 0.5
        }

        if not activated:
            return context

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Get emotional tags for activated entities
            entity_ids = list(activated.keys())[:50]  # Limit for performance
            placeholders = ','.join('?' * len(entity_ids))

            cursor.execute(
                f'''
                SELECT entity_id, valence, arousal, dominance, salience_score
                FROM emotional_tags
                WHERE entity_id IN ({placeholders})
                ''',
                entity_ids
            )

            total_weight = 0.0
            weighted_valence = 0.0
            weighted_arousal = 0.0
            weighted_dominance = 0.0

            for row in cursor.fetchall():
                entity_id, valence, arousal, dominance, salience = row

                # Weight by activation level and salience
                activation = activated.get(entity_id, 0.0)
                weight = activation * (salience or 0.5)

                weighted_valence += (valence or 0.0) * weight
                weighted_arousal += (arousal or 0.5) * weight
                weighted_dominance += (dominance or 0.5) * weight
                total_weight += weight

            if total_weight > 0:
                context["valence"] = weighted_valence / total_weight
                context["arousal"] = weighted_arousal / total_weight
                context["dominance"] = weighted_dominance / total_weight

            conn.close()

        except Exception as e:
            logger.error(f"Error computing emotional context: {e}")

        return context

    def _compute_routing_bias(
        self,
        query: str,
        activated: Dict[int, float],
        emotional_context: Dict[str, float],
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Compute routing bias for model selection.

        Memory influences which model is best suited for the task.
        """
        bias = {
            "simple": 0.0,     # Simple/fast models (Haiku)
            "balanced": 0.0,  # Balanced models (Sonnet)
            "complex": 0.0,   # Complex/powerful models (Opus)
            "local": 0.0      # Local models (Ollama)
        }

        # Factor 1: Query complexity from primed concepts
        if len(activated) > 20:
            # Many activated concepts = complex query
            bias["complex"] += 0.2
            bias["balanced"] += 0.1
        elif len(activated) < 5:
            # Few activated concepts = simple query
            bias["simple"] += 0.2
        else:
            bias["balanced"] += 0.15

        # Factor 2: Emotional context
        arousal = emotional_context.get("arousal", 0.5)
        if arousal > 0.7:
            # High arousal = more careful/complex reasoning
            bias["complex"] += 0.1

        valence = emotional_context.get("valence", 0.0)
        if valence < -0.3:
            # Negative context = be more cautious
            bias["complex"] += 0.1
            bias["simple"] -= 0.1

        # Factor 3: Session context
        if session_context:
            task_type = session_context.get("task_type", "")
            if task_type in ("code_review", "architecture", "security"):
                bias["complex"] += 0.2
            elif task_type in ("quick_question", "status_check"):
                bias["simple"] += 0.2

        # Factor 4: Historical success patterns (from routing learner)
        try:
            from agi.routing_learning import get_learned_routing_bias
            task_type = session_context.get("task_type", "general") if session_context else "general"
            context_key = session_context.get("context_key") if session_context else None

            learned = get_learned_routing_bias(task_type, context_key)
            sample_count = learned.pop("_sample_count", 0)

            # Apply learned bias with confidence weighting
            # More samples = more weight on learned bias
            confidence = min(0.8, sample_count / 20) if sample_count > 0 else 0.0

            for tier in ["simple", "balanced", "complex", "local"]:
                bias[tier] += learned.get(tier, 0.0) * confidence

            if sample_count > 0:
                logger.debug(f"Applied learned routing bias (n={sample_count}, conf={confidence:.2f})")

        except ImportError:
            logger.debug("Routing learner not available, using heuristics only")
        except Exception as e:
            logger.warning(f"Error applying learned routing bias: {e}")

        return bias

    def _compute_confidence_modifier(
        self,
        activated: Dict[int, float],
        primed_concepts: Set[str]
    ) -> float:
        """
        Compute confidence modifier based on memory familiarity.

        Returns:
            Float > 1.0 if familiar territory, < 1.0 if novel
        """
        modifier = 1.0

        # Factor 1: Number of activated memories
        # More memories = more familiar territory
        if len(activated) > 30:
            modifier += 0.15  # Very familiar
        elif len(activated) > 15:
            modifier += 0.08  # Somewhat familiar
        elif len(activated) < 5:
            modifier -= 0.1   # Novel territory

        # Factor 2: Average activation strength
        if activated:
            avg_activation = sum(activated.values()) / len(activated)
            if avg_activation > 0.6:
                modifier += 0.1  # Strong memories
            elif avg_activation < 0.3:
                modifier -= 0.05  # Weak memories

        # Factor 3: Primed concept count
        if len(primed_concepts) > 10:
            modifier += 0.05  # Well-primed

        # Clamp to reasonable range
        return max(0.5, min(1.5, modifier))

    def _persist_activation_event(self, state: ActivationState):
        """Persist activation computation for learning and analysis."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activation_field_log (
                    id INTEGER PRIMARY KEY,
                    context_hash TEXT,
                    source_query TEXT,
                    activated_count INTEGER,
                    primed_count INTEGER,
                    confidence_modifier REAL,
                    valence REAL,
                    arousal REAL,
                    computation_time_ms REAL,
                    computed_at TEXT,
                    routing_bias TEXT
                )
            ''')

            cursor.execute(
                '''
                INSERT INTO activation_field_log (
                    context_hash, source_query, activated_count, primed_count,
                    confidence_modifier, valence, arousal, computation_time_ms,
                    computed_at, routing_bias
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    state.context_hash,
                    state.source_query[:500],  # Truncate long queries
                    len(state.active_entity_ids),
                    len(state.primed_concepts),
                    state.confidence_modifier,
                    state.emotional_context.get("valence", 0.0),
                    state.emotional_context.get("arousal", 0.5),
                    state.computation_time_ms,
                    state.computed_at,
                    json.dumps(state.routing_bias)
                )
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to persist activation event: {e}")

    def get_routing_recommendation(self) -> str:
        """
        Get model routing recommendation based on current activation field.

        Returns:
            Recommended model tier: "simple", "balanced", "complex", or "local"
        """
        if not self.current_state:
            return "balanced"

        bias = self.current_state.routing_bias
        if not bias:
            return "balanced"

        # Return tier with highest bias
        return max(bias, key=lambda k: bias.get(k, 0))

    def get_primed_search_boost(self) -> Dict[str, float]:
        """
        Get search boost weights based on primed concepts.

        Returns:
            Dict of concept → boost weight for search ranking
        """
        if not self.current_state:
            return {}

        # Convert primed concepts to search boosts
        return {
            concept: 0.2  # Boost primed concepts in search
            for concept in self.current_state.primed_concepts
        }

    def should_elaborate(self) -> bool:
        """
        Determine if response should be more elaborate based on activation.

        Based on emotional context and familiarity.
        """
        if not self.current_state:
            return True  # Default to elaborate

        # Low confidence = explain more
        if self.current_state.confidence_modifier < 0.8:
            return True

        # High arousal = be more careful/thorough
        if self.current_state.emotional_context.get("arousal", 0.5) > 0.7:
            return True

        return False

    def clear(self):
        """Clear current activation state."""
        with self._state_lock:
            self._current_state = None
        logger.info("Activation field cleared")


# Singleton accessor
def get_activation_field() -> ActivationField:
    """Get the singleton ActivationField instance."""
    return ActivationField()


# Convenience functions for hook integration
def compute_activation_for_query(query: str) -> Dict[str, Any]:
    """
    Convenience function for hooks - compute activation field.

    Returns dict suitable for JSON serialization.
    """
    field = get_activation_field()
    state = field.compute_from_context(query)
    return state.to_dict()


def get_current_routing_bias() -> Dict[str, float]:
    """Get current routing bias for model selection."""
    field = get_activation_field()
    if field.current_state:
        return field.current_state.routing_bias
    return {}


def get_current_confidence_modifier() -> float:
    """Get current confidence modifier."""
    field = get_activation_field()
    if field.current_state:
        return field.current_state.confidence_modifier
    return 1.0
