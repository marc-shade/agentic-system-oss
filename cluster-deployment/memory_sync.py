#!/usr/bin/env python3
"""
CRDT-Based Memory Synchronization
==================================

Implements Conflict-Free Replicated Data Types (CRDTs) for distributed memory.

CRDTs enable automatic conflict-free merging of updates across nodes without
coordination. Updates can be applied in any order and always converge to the
same state.

CRDT Types Implemented:
- LWW-Register (Last-Write-Wins): For single values
- OR-Set (Observed-Remove Set): For collections
- Counter: For incrementing values

Use Cases:
- Synchronize working memory across nodes
- Share episodic memories
- Replicate semantic concepts
- Distributed configuration

Usage:
    sync = ClusterMemorySync(node_id="macpro51")

    # Add shared memory
    sync.add_shared_memory("task_status", {"status": "running"})

    # Get update to send to other nodes
    update = sync.get_sync_update()

    # Apply update from another node
    sync.apply_remote_update(update)
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

from vector_clock import VectorClock

logger = logging.getLogger(__name__)


@dataclass
class LWWRegister:
    """
    Last-Write-Wins Register CRDT.

    Stores a single value with timestamp. Conflicts resolved by taking
    the value with the latest timestamp (or highest node ID if tied).
    """

    value: Any
    timestamp: float
    node_id: str

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        """Merge with another register (take latest)."""
        if other.timestamp > self.timestamp:
            return other
        elif other.timestamp == self.timestamp:
            # Tie-break by node ID (deterministic)
            if other.node_id > self.node_id:
                return other
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "timestamp": self.timestamp, "node_id": self.node_id}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LWWRegister":
        return cls(**data)


@dataclass
class ORSetElement:
    """Element in an Observed-Remove Set with unique tag."""
    value: Any
    tag: str  # Unique identifier (node_id + timestamp)
    added_by: str
    added_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ORSetElement":
        return cls(**data)


@dataclass
class ORSet:
    """
    Observed-Remove Set CRDT.

    Add-biased set where elements can be added and removed.
    Conflicts resolved by keeping elements if add timestamp > remove timestamp.
    """

    elements: Dict[str, ORSetElement] = field(default_factory=dict)  # tag -> element
    tombstones: Dict[str, float] = field(default_factory=dict)  # tag -> remove_timestamp

    def add(self, value: Any, node_id: str) -> str:
        """Add element to set. Returns unique tag."""
        tag = f"{node_id}-{time.time()}-{hash(json.dumps(value, sort_keys=True))}"
        element = ORSetElement(
            value=value,
            tag=tag,
            added_by=node_id,
            added_at=time.time()
        )
        self.elements[tag] = element
        return tag

    def remove(self, tag: str):
        """Remove element by tag."""
        if tag in self.elements:
            self.tombstones[tag] = time.time()

    def contains(self, value: Any) -> bool:
        """Check if value is in set (not tombstoned)."""
        for tag, element in self.elements.items():
            if element.value == value and tag not in self.tombstones:
                return True
        return False

    def get_values(self) -> List[Any]:
        """Get all non-tombstoned values."""
        return [
            element.value
            for tag, element in self.elements.items()
            if tag not in self.tombstones
        ]

    def merge(self, other: "ORSet") -> "ORSet":
        """Merge with another OR-Set."""
        merged = ORSet()

        # Merge elements (union)
        merged.elements = {**self.elements, **other.elements}

        # Merge tombstones (union with max timestamp)
        all_tags = set(self.tombstones.keys()) | set(other.tombstones.keys())
        for tag in all_tags:
            merged.tombstones[tag] = max(
                self.tombstones.get(tag, 0),
                other.tombstones.get(tag, 0)
            )

        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elements": {tag: elem.to_dict() for tag, elem in self.elements.items()},
            "tombstones": self.tombstones
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ORSet":
        return cls(
            elements={
                tag: ORSetElement.from_dict(elem_data)
                for tag, elem_data in data.get("elements", {}).items()
            },
            tombstones=data.get("tombstones", {})
        )


@dataclass
class GCounter:
    """
    Grow-only Counter CRDT.

    Each node maintains its own counter. Total is sum of all counters.
    Monotonically increasing (no decrements).
    """

    counts: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str, amount: int = 1):
        """Increment counter for a node."""
        self.counts[node_id] = self.counts.get(node_id, 0) + amount

    def value(self) -> int:
        """Get total count across all nodes."""
        return sum(self.counts.values())

    def merge(self, other: "GCounter") -> "GCounter":
        """Merge with another counter (element-wise max)."""
        merged = GCounter()
        all_nodes = set(self.counts.keys()) | set(other.counts.keys())

        for node in all_nodes:
            merged.counts[node] = max(
                self.counts.get(node, 0),
                other.counts.get(node, 0)
            )

        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {"counts": self.counts}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GCounter":
        return cls(counts=data.get("counts", {}))


class ClusterMemorySync:
    """
    CRDT-based memory synchronization for cluster nodes.

    Manages three types of shared memory:
    - Working memory: Temporary shared context (LWW-Register)
    - Episodic memory: Shared experiences (OR-Set)
    - Semantic memory: Shared concepts and knowledge (OR-Set)
    """

    def __init__(self, node_id: str, storage_dir: Optional[Path] = None):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id=node_id)

        if storage_dir is None:
            storage_dir = Path.home() / ".cache" / "gitMQ-memory-sync"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # CRDT data structures
        self.working_memory: Dict[str, LWWRegister] = {}  # key -> LWW register
        self.episodic_memory = ORSet()  # Set of episodic events
        self.semantic_memory = ORSet()  # Set of concepts
        self.access_counts = GCounter()  # Memory access tracking

        # Metadata
        self.last_sync_time: Dict[str, float] = {}  # node_id -> timestamp

        # Load persisted state
        self._load_state()

        logger.info(f"Memory sync initialized for {node_id}")

    def _load_state(self):
        """Load persisted CRDT state from disk."""
        state_file = self.storage_dir / f"{self.node_id}.json"

        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                data = json.load(f)

            # Restore working memory
            self.working_memory = {
                key: LWWRegister.from_dict(reg_data)
                for key, reg_data in data.get("working_memory", {}).items()
            }

            # Restore episodic memory
            if "episodic_memory" in data:
                self.episodic_memory = ORSet.from_dict(data["episodic_memory"])

            # Restore semantic memory
            if "semantic_memory" in data:
                self.semantic_memory = ORSet.from_dict(data["semantic_memory"])

            # Restore access counts
            if "access_counts" in data:
                self.access_counts = GCounter.from_dict(data["access_counts"])

            # Restore vector clock
            if "vector_clock" in data:
                self.vector_clock = VectorClock.from_dict(self.node_id, data["vector_clock"])

            logger.info(f"Loaded memory sync state from {state_file}")

        except Exception as e:
            logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Persist CRDT state to disk."""
        state_file = self.storage_dir / f"{self.node_id}.json"

        try:
            data = {
                "node_id": self.node_id,
                "working_memory": {
                    key: reg.to_dict()
                    for key, reg in self.working_memory.items()
                },
                "episodic_memory": self.episodic_memory.to_dict(),
                "semantic_memory": self.semantic_memory.to_dict(),
                "access_counts": self.access_counts.to_dict(),
                "vector_clock": self.vector_clock.to_dict(),
                "last_sync_time": self.last_sync_time,
                "updated_at": datetime.now().isoformat()
            }

            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def add_shared_memory(
        self,
        key: str,
        value: Any,
        memory_type: str = "working"
    ):
        """
        Add or update shared memory.

        Args:
            key: Memory identifier
            value: Memory content
            memory_type: "working", "episodic", or "semantic"
        """
        self.vector_clock.tick()

        if memory_type == "working":
            # Working memory uses LWW-Register
            self.working_memory[key] = LWWRegister(
                value=value,
                timestamp=time.time(),
                node_id=self.node_id
            )

        elif memory_type == "episodic":
            # Episodic memory uses OR-Set
            self.episodic_memory.add(value, self.node_id)

        elif memory_type == "semantic":
            # Semantic memory uses OR-Set
            self.semantic_memory.add(value, self.node_id)

        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

        # Track access
        self.access_counts.increment(self.node_id)

        # Persist
        self._save_state()

        logger.debug(f"Added {memory_type} memory: {key}")

    def get_shared_memory(self, key: str, memory_type: str = "working") -> Optional[Any]:
        """Get shared memory value."""
        if memory_type == "working":
            reg = self.working_memory.get(key)
            return reg.value if reg else None

        elif memory_type == "episodic":
            return self.episodic_memory.get_values()

        elif memory_type == "semantic":
            return self.semantic_memory.get_values()

        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def get_sync_update(self) -> Dict[str, Any]:
        """
        Get CRDT update to send to other nodes.

        Returns complete state that can be merged by remote nodes.
        """
        return {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.to_dict(),
            "working_memory": {
                key: reg.to_dict()
                for key, reg in self.working_memory.items()
            },
            "episodic_memory": self.episodic_memory.to_dict(),
            "semantic_memory": self.semantic_memory.to_dict(),
            "access_counts": self.access_counts.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

    def apply_remote_update(self, update: Dict[str, Any]):
        """
        Apply CRDT update from another node.

        Automatically merges updates using CRDT properties.
        Conflicts are resolved deterministically.
        """
        remote_node = update.get("node_id")
        logger.info(f"Applying update from {remote_node}")

        # Merge vector clock
        if "vector_clock" in update:
            self.vector_clock.merge(update["vector_clock"])

        # Merge working memory (LWW-Register merge)
        if "working_memory" in update:
            for key, remote_reg_data in update["working_memory"].items():
                remote_reg = LWWRegister.from_dict(remote_reg_data)

                if key in self.working_memory:
                    # Merge: take latest
                    self.working_memory[key] = self.working_memory[key].merge(remote_reg)
                else:
                    # New key
                    self.working_memory[key] = remote_reg

        # Merge episodic memory (OR-Set merge)
        if "episodic_memory" in update:
            remote_episodic = ORSet.from_dict(update["episodic_memory"])
            self.episodic_memory = self.episodic_memory.merge(remote_episodic)

        # Merge semantic memory (OR-Set merge)
        if "semantic_memory" in update:
            remote_semantic = ORSet.from_dict(update["semantic_memory"])
            self.semantic_memory = self.semantic_memory.merge(remote_semantic)

        # Merge access counts (GCounter merge)
        if "access_counts" in update:
            remote_counts = GCounter.from_dict(update["access_counts"])
            self.access_counts = self.access_counts.merge(remote_counts)

        # Update last sync time
        self.last_sync_time[remote_node] = time.time()

        # Persist
        self._save_state()

        logger.info(f"✓ Merged update from {remote_node}")

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get memory synchronization statistics."""
        return {
            "node_id": self.node_id,
            "vector_clock": str(self.vector_clock),
            "working_memory_keys": len(self.working_memory),
            "episodic_memories": len(self.episodic_memory.get_values()),
            "semantic_concepts": len(self.semantic_memory.get_values()),
            "total_accesses": self.access_counts.value(),
            "last_syncs": {
                node: datetime.fromtimestamp(ts).isoformat()
                for node, ts in self.last_sync_time.items()
            }
        }


# ============================================================================
# Example Usage
# ============================================================================

def example_memory_sync():
    """Example: Synchronize memory across three nodes."""
    print("\n" + "=" * 70)
    print("CRDT Memory Synchronization Example")
    print("=" * 70)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize three nodes
        node_a = ClusterMemorySync("node-a", storage_dir=Path(tmpdir) / "a")
        node_b = ClusterMemorySync("node-b", storage_dir=Path(tmpdir) / "b")
        node_c = ClusterMemorySync("node-c", storage_dir=Path(tmpdir) / "c")

        print("\n1. Node A adds working memory:")
        node_a.add_shared_memory("task_status", {"status": "running", "progress": 50})
        print(f"   Node A task_status: {node_a.get_shared_memory('task_status')}")

        print("\n2. Node B adds episodic memory:")
        node_b.add_shared_memory(
            "event-1",
            {"type": "task_completed", "task_id": "abc-123"},
            memory_type="episodic"
        )

        print("\n3. Sync Node A → Node B:")
        update_a = node_a.get_sync_update()
        node_b.apply_remote_update(update_a)
        print(f"   Node B task_status: {node_b.get_shared_memory('task_status')}")

        print("\n4. Node C updates task_status (concurrent):")
        time.sleep(0.1)  # Slight delay for timestamp difference
        node_c.add_shared_memory("task_status", {"status": "completed", "progress": 100})

        print("\n5. Sync both to Node B (conflict resolution):")
        update_c = node_c.get_sync_update()
        node_b.apply_remote_update(update_c)
        final_status = node_b.get_shared_memory("task_status")
        print(f"   Final task_status (LWW): {final_status}")
        print(f"   Winner: Node {final_status.get('status')}")

        print("\n6. Sync episodic memories:")
        update_b = node_b.get_sync_update()
        node_a.apply_remote_update(update_b)
        node_c.apply_remote_update(update_b)

        print(f"   Node A episodic: {len(node_a.episodic_memory.get_values())} events")
        print(f"   Node C episodic: {len(node_c.episodic_memory.get_values())} events")

        print("\n7. Statistics:")
        for node in [node_a, node_b, node_c]:
            stats = node.get_sync_stats()
            print(f"   {stats['node_id']}: {stats['vector_clock']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_memory_sync()
    print("\nMemory sync module loaded successfully ✓")
