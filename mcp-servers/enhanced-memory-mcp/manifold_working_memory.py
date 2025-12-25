#!/usr/bin/env python3
"""
Manifold-Based Working Memory (PTM Phase 4)

Implements working memory on T^8 hyper-torus manifold with:
- Phase angle-based slot addressing (O(1) lookup)
- Irrational rotation for collision-free allocation
- Resonance-based retrieval (phase proximity search)
- Interference patterns for associative memory
- Natural decay via phase drift

Reference: "Memory as Resonance" (arXiv:2512.20245)

Key Concepts:
- Each memory item occupies a position (phase angles) on T^8
- Related items cluster in phase space (interference)
- Retrieval uses phase resonance (cosine similarity)
- Decay implemented as energy reduction over time
- Context keys map to manifold regions for grouping
"""

import math
import numpy as np
import hashlib
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

logger = logging.getLogger("manifold-working-memory")

# PTM-inspired constants
MANIFOLD_DIM = 8              # T^8 hyper-torus dimension
GOLDEN_RATIO = (1 + math.sqrt(5)) / 2  # φ ≈ 1.618
TWO_PI = 2 * math.pi
DEFAULT_ENERGY = 1.0          # Initial slot energy
DECAY_RATE = 0.05             # Energy decay per minute
MIN_ENERGY = 0.1              # Below this, slot is garbage collected
RESONANCE_THRESHOLD = 0.7     # Minimum phase similarity for resonance
MAX_SLOTS = 1000              # Maximum working memory slots
CONTEXT_HASH_SEED = 42        # For deterministic context hashing


@dataclass
class ManifoldSlot:
    """
    A memory slot positioned on the T^8 manifold.

    Attributes:
        slot_id: Unique slot identifier
        phases: Position on manifold (8 phase angles in [0, 2π))
        content: Memory content string
        context_key: Context for grouping related memories
        priority: Priority level (1-10)
        energy: Current activation energy [0, 1]
        created_at: Creation timestamp
        last_accessed: Last access timestamp
        access_count: Number of retrievals
        entity_id: Optional linked entity ID
        metadata: Additional metadata
    """
    slot_id: int
    phases: np.ndarray
    content: str
    context_key: str
    priority: int = 5
    energy: float = DEFAULT_ENERGY
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    entity_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure phases are numpy array."""
        if not isinstance(self.phases, np.ndarray):
            self.phases = np.array(self.phases, dtype=np.float64)

    def phase_distance(self, other_phases: np.ndarray) -> float:
        """
        Geodesic distance on torus (phase difference).

        Returns value in [0, π√8] where 0 is identical position.
        """
        diff = np.abs(self.phases - other_phases)
        # Wrap around for torus topology
        diff = np.minimum(diff, TWO_PI - diff)
        return float(np.sqrt(np.sum(diff ** 2)))

    def phase_similarity(self, other_phases: np.ndarray) -> float:
        """
        Cosine similarity in Cartesian embedding space.

        Returns value in [0, 1] where 1 is identical position.
        """
        # Convert to Cartesian (cos, sin pairs)
        self_cart = np.concatenate([[np.cos(p), np.sin(p)] for p in self.phases])
        other_cart = np.concatenate([[np.cos(p), np.sin(p)] for p in other_phases])

        # Cosine similarity
        dot = np.dot(self_cart, other_cart)
        norm1 = np.linalg.norm(self_cart)
        norm2 = np.linalg.norm(other_cart)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Normalize to [0, 1]
        cosine_sim = dot / (norm1 * norm2)
        return float((cosine_sim + 1) / 2)

    def apply_decay(self, elapsed_minutes: float) -> float:
        """
        Apply energy decay based on elapsed time.

        Returns new energy level.
        """
        decay = DECAY_RATE * elapsed_minutes
        self.energy = max(MIN_ENERGY / 2, self.energy - decay)
        return self.energy

    def boost_energy(self, amount: float = 0.2) -> float:
        """
        Boost energy on access (reinforcement).

        Returns new energy level.
        """
        self.energy = min(1.0, self.energy + amount)
        self.last_accessed = time.time()
        self.access_count += 1
        return self.energy

    def is_expired(self) -> bool:
        """Check if slot should be garbage collected."""
        return self.energy < MIN_ENERGY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "slot_id": self.slot_id,
            "phases": self.phases.tolist(),
            "content": self.content,
            "context_key": self.context_key,
            "priority": self.priority,
            "energy": self.energy,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "entity_id": self.entity_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ManifoldSlot':
        """Create from dictionary."""
        return cls(
            slot_id=data["slot_id"],
            phases=np.array(data["phases"]),
            content=data["content"],
            context_key=data["context_key"],
            priority=data.get("priority", 5),
            energy=data.get("energy", DEFAULT_ENERGY),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            entity_id=data.get("entity_id"),
            metadata=data.get("metadata", {})
        )


class IrrationalRotation:
    """
    Irrational rotation generator for slot allocation.

    Uses golden ratio-based angles to generate positions that
    densely and uniformly fill the manifold without repetition.
    """

    def __init__(self, dim: int = MANIFOLD_DIM):
        self.dim = dim
        # Generate base rotation angles from golden ratio powers
        self.base_angles = np.array([
            (TWO_PI * (GOLDEN_RATIO ** i)) % TWO_PI
            for i in range(1, dim + 1)
        ])
        self._step_count = 0

    def next_position(self, seed_phases: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Generate next position using irrational rotation.

        If seed_phases provided, rotate from that position.
        Otherwise rotate from accumulated position.
        """
        if seed_phases is not None:
            position = seed_phases.copy()
        else:
            # Use accumulated rotation count
            position = np.zeros(self.dim)

        self._step_count += 1
        # Apply rotation (each step moves by base_angles)
        position = (position + self.base_angles * self._step_count) % TWO_PI
        return position

    def position_from_hash(self, text: str, salt: int = 0) -> np.ndarray:
        """
        Deterministic position from text hash.

        Uses SHA-256 to generate reproducible phases.
        """
        hash_input = f"{text}:{salt}:{CONTEXT_HASH_SEED}".encode()
        hash_bytes = hashlib.sha256(hash_input).digest()

        # Use first 8 bytes for 8 dimensions
        phases = np.array([
            (hash_bytes[i] / 255.0) * TWO_PI
            for i in range(self.dim)
        ])
        return phases

    def context_region_center(self, context_key: str) -> np.ndarray:
        """
        Get center position for a context region.

        All items with same context_key cluster near this center.
        """
        return self.position_from_hash(f"context:{context_key}")

    def position_in_region(self, context_key: str, content: str) -> np.ndarray:
        """
        Generate position near context region center.

        Adds content-based offset for uniqueness while maintaining proximity.
        """
        center = self.context_region_center(context_key)
        offset = self.position_from_hash(content)

        # Scale offset to keep items clustered (within 0.5 radians of center)
        scaled_offset = offset * 0.15

        return (center + scaled_offset) % TWO_PI


class ManifoldWorkingMemory:
    """
    Working memory implemented on T^8 hyper-torus manifold.

    Features:
    - Phase-based slot addressing
    - Irrational rotation for allocation
    - Resonance-based retrieval
    - Context region clustering
    - Automatic decay and garbage collection
    """

    def __init__(self, max_slots: int = MAX_SLOTS):
        self.max_slots = max_slots
        self.rotation = IrrationalRotation()
        self.slots: Dict[int, ManifoldSlot] = {}
        self.context_index: Dict[str, List[int]] = defaultdict(list)
        self.next_slot_id = 1
        self._lock = threading.RLock()
        self._last_gc = time.time()

        # Statistics
        self._stats = {
            "total_allocations": 0,
            "total_retrievals": 0,
            "total_gc_runs": 0,
            "slots_garbage_collected": 0,
            "resonance_searches": 0
        }

    def allocate(
        self,
        content: str,
        context_key: str = "default",
        priority: int = 5,
        entity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ManifoldSlot:
        """
        Allocate a new slot on the manifold.

        Position is determined by context_key and content hash
        to ensure related items cluster together.

        Args:
            content: Memory content string
            context_key: Context for grouping (maps to manifold region)
            priority: Priority level 1-10
            entity_id: Optional linked entity
            metadata: Additional metadata

        Returns:
            Allocated ManifoldSlot
        """
        with self._lock:
            # Run GC if needed
            self._maybe_gc()

            # Evict lowest energy slot if at capacity
            if len(self.slots) >= self.max_slots:
                self._evict_lowest_energy()

            # Generate position based on context and content
            phases = self.rotation.position_in_region(context_key, content)

            slot = ManifoldSlot(
                slot_id=self.next_slot_id,
                phases=phases,
                content=content,
                context_key=context_key,
                priority=priority,
                entity_id=entity_id,
                metadata=metadata or {}
            )

            self.slots[slot.slot_id] = slot
            self.context_index[context_key].append(slot.slot_id)
            self.next_slot_id += 1
            self._stats["total_allocations"] += 1

            return slot

    def retrieve(self, slot_id: int) -> Optional[ManifoldSlot]:
        """
        Retrieve slot by ID with energy boost.

        Returns None if slot doesn't exist or is expired.
        """
        with self._lock:
            slot = self.slots.get(slot_id)
            if slot and not slot.is_expired():
                slot.boost_energy()
                self._stats["total_retrievals"] += 1
                return slot
            return None

    def retrieve_by_context(
        self,
        context_key: str,
        limit: int = 50
    ) -> List[ManifoldSlot]:
        """
        Retrieve all slots in a context region.

        Returns slots sorted by priority * energy.
        """
        with self._lock:
            slot_ids = self.context_index.get(context_key, [])
            slots = []

            for slot_id in slot_ids:
                slot = self.slots.get(slot_id)
                if slot and not slot.is_expired():
                    slot.boost_energy(0.1)  # Smaller boost for bulk retrieval
                    slots.append(slot)

            # Sort by priority * energy (effective importance)
            slots.sort(key=lambda s: s.priority * s.energy, reverse=True)
            self._stats["total_retrievals"] += len(slots[:limit])

            return slots[:limit]

    def resonance_search(
        self,
        query: str,
        context_key: Optional[str] = None,
        limit: int = 10,
        threshold: float = RESONANCE_THRESHOLD
    ) -> List[Tuple[ManifoldSlot, float]]:
        """
        Search using phase resonance (similarity on manifold).

        Finds slots with similar phase positions to query.
        This implements associative/content-addressable retrieval.

        Args:
            query: Query text (converted to phase position)
            context_key: Optional context to narrow search
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of (slot, similarity) tuples sorted by similarity
        """
        with self._lock:
            self._stats["resonance_searches"] += 1

            # Generate query position
            if context_key:
                query_phases = self.rotation.position_in_region(context_key, query)
            else:
                query_phases = self.rotation.position_from_hash(query)

            results = []

            # Search relevant slots
            if context_key:
                slot_ids = self.context_index.get(context_key, [])
            else:
                slot_ids = list(self.slots.keys())

            for slot_id in slot_ids:
                slot = self.slots.get(slot_id)
                if slot and not slot.is_expired():
                    similarity = slot.phase_similarity(query_phases)
                    if similarity >= threshold:
                        results.append((slot, similarity))

            # Sort by similarity * energy (relevance * freshness)
            results.sort(key=lambda x: x[1] * x[0].energy, reverse=True)

            # Boost energy for retrieved slots
            for slot, _ in results[:limit]:
                slot.boost_energy(0.15)

            return results[:limit]

    def interference_query(
        self,
        query_phases: np.ndarray,
        limit: int = 10
    ) -> List[Tuple[ManifoldSlot, float]]:
        """
        Direct phase-based interference query.

        Used for advanced manifold operations where
        query position is known.

        Args:
            query_phases: 8D phase position
            limit: Maximum results

        Returns:
            List of (slot, similarity) tuples
        """
        with self._lock:
            results = []

            for slot in self.slots.values():
                if not slot.is_expired():
                    similarity = slot.phase_similarity(query_phases)
                    results.append((slot, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    def apply_global_decay(self) -> int:
        """
        Apply decay to all slots based on time elapsed.

        Returns number of slots decayed.
        """
        with self._lock:
            current_time = time.time()
            decayed_count = 0

            for slot in self.slots.values():
                elapsed_minutes = (current_time - slot.last_accessed) / 60
                if elapsed_minutes > 0:
                    slot.apply_decay(elapsed_minutes)
                    decayed_count += 1

            return decayed_count

    def garbage_collect(self) -> int:
        """
        Remove expired slots.

        Returns number of slots removed.
        """
        with self._lock:
            self._stats["total_gc_runs"] += 1
            expired_ids = [
                slot_id for slot_id, slot in self.slots.items()
                if slot.is_expired()
            ]

            for slot_id in expired_ids:
                slot = self.slots.pop(slot_id)
                # Remove from context index
                if slot.context_key in self.context_index:
                    try:
                        self.context_index[slot.context_key].remove(slot_id)
                    except ValueError:
                        pass

            self._stats["slots_garbage_collected"] += len(expired_ids)
            self._last_gc = time.time()

            return len(expired_ids)

    def _maybe_gc(self):
        """Run GC if enough time has passed."""
        if time.time() - self._last_gc > 60:  # Every minute
            self.garbage_collect()

    def _evict_lowest_energy(self) -> Optional[ManifoldSlot]:
        """Evict slot with lowest energy to make room."""
        if not self.slots:
            return None

        lowest = min(self.slots.values(), key=lambda s: s.energy)
        self.slots.pop(lowest.slot_id)

        # Remove from context index
        if lowest.context_key in self.context_index:
            try:
                self.context_index[lowest.context_key].remove(lowest.slot_id)
            except ValueError:
                pass

        return lowest

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            context_sizes = {
                ctx: len(ids) for ctx, ids in self.context_index.items()
            }

            energies = [s.energy for s in self.slots.values()]
            avg_energy = sum(energies) / len(energies) if energies else 0

            return {
                **self._stats,
                "current_slots": len(self.slots),
                "max_slots": self.max_slots,
                "utilization": len(self.slots) / self.max_slots,
                "contexts": len(self.context_index),
                "context_sizes": context_sizes,
                "average_energy": avg_energy,
                "manifold_dim": MANIFOLD_DIM
            }

    def get_context_centroid(self, context_key: str) -> Optional[np.ndarray]:
        """
        Get the centroid (average position) of slots in a context.

        Useful for context-level operations.
        """
        with self._lock:
            slot_ids = self.context_index.get(context_key, [])
            if not slot_ids:
                return None

            phases_list = []
            for slot_id in slot_ids:
                slot = self.slots.get(slot_id)
                if slot:
                    phases_list.append(slot.phases)

            if not phases_list:
                return None

            # Average on torus (circular mean)
            sin_sum = np.sum([np.sin(p) for p in phases_list], axis=0)
            cos_sum = np.sum([np.cos(p) for p in phases_list], axis=0)
            centroid = np.arctan2(sin_sum, cos_sum) % TWO_PI

            return centroid

    def clear(self):
        """Clear all slots."""
        with self._lock:
            self.slots.clear()
            self.context_index.clear()
            self.next_slot_id = 1


# Singleton instance
_manifold_memory_instance: Optional[ManifoldWorkingMemory] = None
_instance_lock = threading.Lock()


def get_manifold_working_memory() -> ManifoldWorkingMemory:
    """Get or create singleton ManifoldWorkingMemory instance."""
    global _manifold_memory_instance

    with _instance_lock:
        if _manifold_memory_instance is None:
            _manifold_memory_instance = ManifoldWorkingMemory()
        return _manifold_memory_instance


def reset_manifold_working_memory():
    """Reset singleton instance (for testing)."""
    global _manifold_memory_instance

    with _instance_lock:
        if _manifold_memory_instance is not None:
            _manifold_memory_instance.clear()
        _manifold_memory_instance = None


# Convenience functions
def allocate_working_slot(
    content: str,
    context_key: str = "default",
    priority: int = 5,
    entity_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to allocate a working memory slot.

    Returns slot as dictionary.
    """
    memory = get_manifold_working_memory()
    slot = memory.allocate(content, context_key, priority, entity_id)
    return slot.to_dict()


def search_working_memory(
    query: str,
    context_key: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Convenience function for resonance search.

    Returns list of (slot_dict, similarity) pairs.
    """
    memory = get_manifold_working_memory()
    results = memory.resonance_search(query, context_key, limit)
    return [
        {"slot": slot.to_dict(), "similarity": sim}
        for slot, sim in results
    ]


def get_working_memory_stats() -> Dict[str, Any]:
    """Get working memory statistics."""
    memory = get_manifold_working_memory()
    return memory.get_stats()
