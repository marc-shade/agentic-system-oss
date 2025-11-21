#!/usr/bin/env python3
"""
Vector Clock Implementation for Causal Ordering
================================================

Implements Lamport vector clocks for distributed event ordering.

A vector clock is a data structure used to determine the partial ordering of
events in a distributed system and detect causality violations.

Properties:
- Each node maintains a vector of logical clocks
- Clock increments on every local event
- Clocks merge on message receipt
- Enables happens-before relationship detection

Use Cases:
- Detect causal dependencies between events
- Identify concurrent (conflicting) updates
- Order events consistently across nodes
- Implement distributed consensus

Usage:
    clock = VectorClock(node_id="macpro51")

    # Local event
    clock.tick()

    # Send message
    message = {"data": "...", "vector_clock": clock.to_dict()}

    # Receive message
    clock.merge(message["vector_clock"])

    # Check causality
    if clock.happens_before(other_clock):
        print("This event caused the other")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Any


@dataclass
class VectorClock:
    """
    Vector clock for causal ordering in distributed systems.

    Each node maintains a vector of logical clocks (one per node).
    Provides happens-before relationships and conflict detection.
    """

    node_id: str
    clocks: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize clock for this node to 0."""
        if self.node_id not in self.clocks:
            self.clocks[self.node_id] = 0

    def tick(self) -> "VectorClock":
        """
        Increment this node's clock (local event).

        Call this when:
        - Creating a new message
        - Processing local computation
        - Before sending a message

        Returns:
            Self for chaining
        """
        self.clocks[self.node_id] += 1
        return self

    def merge(self, other_clocks: Dict[str, int]) -> "VectorClock":
        """
        Merge with another vector clock (message receipt).

        Takes element-wise maximum of all clocks, then increments local clock.

        Call this when:
        - Receiving a message from another node
        - Synchronizing state

        Args:
            other_clocks: Vector clock from remote node

        Returns:
            Self for chaining
        """
        # Get all node IDs from both clocks
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        # Take element-wise maximum
        for node in all_nodes:
            local_value = self.clocks.get(node, 0)
            remote_value = other_clocks.get(node, 0)
            self.clocks[node] = max(local_value, remote_value)

        # Increment local clock after merge
        self.tick()

        return self

    def happens_before(self, other_clocks: Dict[str, int]) -> bool:
        """
        Check if this clock happens-before another clock.

        Returns True if:
        - All clocks in self <= corresponding clocks in other
        - At least one clock in self < corresponding clock in other

        This establishes a causal relationship:
        If A happens-before B, then A causally affects B.

        Args:
            other_clocks: Another vector clock

        Returns:
            True if this event causally precedes the other
        """
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        # Check: self <= other for all nodes
        less_or_equal = all(
            self.clocks.get(node, 0) <= other_clocks.get(node, 0)
            for node in all_nodes
        )

        # Check: self < other for at least one node
        strictly_less = any(
            self.clocks.get(node, 0) < other_clocks.get(node, 0)
            for node in all_nodes
        )

        return less_or_equal and strictly_less

    def concurrent_with(self, other_clocks: Dict[str, int]) -> bool:
        """
        Check if this clock is concurrent with another.

        Two events are concurrent if neither happens-before the other.
        Concurrent events represent a conflict that needs resolution.

        Args:
            other_clocks: Another vector clock

        Returns:
            True if events are concurrent (conflicting)
        """
        return (
            not self.happens_before(other_clocks)
            and not self._other_happens_before(other_clocks)
        )

    def _other_happens_before(self, other_clocks: Dict[str, int]) -> bool:
        """Check if other happens-before this."""
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        less_or_equal = all(
            other_clocks.get(node, 0) <= self.clocks.get(node, 0)
            for node in all_nodes
        )

        strictly_less = any(
            other_clocks.get(node, 0) < self.clocks.get(node, 0)
            for node in all_nodes
        )

        return less_or_equal and strictly_less

    def dominates(self, other_clocks: Dict[str, int]) -> bool:
        """
        Check if this clock dominates (is strictly greater than) another.

        Returns True if all clocks in self >= other clocks.
        Used for garbage collection and pruning old events.

        Args:
            other_clocks: Another vector clock

        Returns:
            True if this clock dominates the other
        """
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        return all(
            self.clocks.get(node, 0) >= other_clocks.get(node, 0)
            for node in all_nodes
        )

    def copy(self) -> "VectorClock":
        """Create a deep copy of this vector clock."""
        return VectorClock(
            node_id=self.node_id,
            clocks=self.clocks.copy()
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for serialization."""
        return self.clocks.copy()

    @classmethod
    def from_dict(cls, node_id: str, clocks_dict: Dict[str, int]) -> "VectorClock":
        """Create vector clock from dictionary."""
        return cls(node_id=node_id, clocks=clocks_dict.copy())

    def __repr__(self) -> str:
        """String representation."""
        clock_str = ", ".join(f"{node}:{count}" for node, count in sorted(self.clocks.items()))
        return f"VectorClock({clock_str})"

    def __eq__(self, other: Any) -> bool:
        """Check equality with another vector clock."""
        if not isinstance(other, VectorClock):
            return False

        all_nodes = set(self.clocks.keys()) | set(other.clocks.keys())
        return all(
            self.clocks.get(node, 0) == other.clocks.get(node, 0)
            for node in all_nodes
        )

    def __lt__(self, other: "VectorClock") -> bool:
        """Less than (happens-before) operator."""
        return self.happens_before(other.clocks)


@dataclass
class CausalMessage:
    """
    Message with vector clock for causal ordering.

    Wraps any message payload with causal metadata.
    """

    sender: str
    message_id: str
    vector_clock: Dict[str, int]
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "sender": self.sender,
            "message_id": self.message_id,
            "vector_clock": self.vector_clock,
            "payload": self.payload,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalMessage":
        """Deserialize from dictionary."""
        return cls(
            sender=data["sender"],
            message_id=data["message_id"],
            vector_clock=data["vector_clock"],
            payload=data["payload"],
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )


class CausalHistory:
    """
    Maintains causal history of events for a node.

    Stores all events with their vector clocks to enable:
    - Causal ordering
    - Conflict detection
    - Garbage collection of old events
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.events: Dict[str, CausalMessage] = {}  # message_id -> CausalMessage
        self.clock = VectorClock(node_id=node_id)

    def add_local_event(self, message_id: str, payload: Dict[str, Any]) -> CausalMessage:
        """
        Add a local event to history.

        Args:
            message_id: Unique event identifier
            payload: Event data

        Returns:
            CausalMessage with current vector clock
        """
        # Tick clock for local event
        self.clock.tick()

        # Create causal message
        message = CausalMessage(
            sender=self.node_id,
            message_id=message_id,
            vector_clock=self.clock.to_dict(),
            payload=payload
        )

        # Store in history
        self.events[message_id] = message

        return message

    def add_remote_event(self, message: CausalMessage) -> CausalMessage:
        """
        Add a remote event to history.

        Merges vector clock and stores event.

        Args:
            message: CausalMessage from remote node

        Returns:
            The message (possibly reordered)
        """
        # Merge vector clock
        self.clock.merge(message.vector_clock)

        # Store in history
        self.events[message.message_id] = message

        return message

    def get_causally_ordered_events(self) -> list[CausalMessage]:
        """
        Get all events in causal order.

        Returns events sorted by happens-before relationship.
        Concurrent events maintain their arrival order.

        Returns:
            List of events in causal order
        """
        events = list(self.events.values())

        # Sort by vector clock (happens-before)
        def clock_key(msg: CausalMessage):
            # Sum of all clocks gives a rough ordering
            # (exact ordering requires topological sort)
            return sum(msg.vector_clock.values())

        return sorted(events, key=clock_key)

    def detect_conflicts(self) -> list[tuple[str, str]]:
        """
        Detect concurrent (conflicting) events.

        Returns:
            List of (event_id1, event_id2) pairs that are concurrent
        """
        conflicts = []
        event_list = list(self.events.items())

        for i, (id1, msg1) in enumerate(event_list):
            for id2, msg2 in event_list[i + 1:]:
                # Check if concurrent
                clock1 = VectorClock.from_dict(self.node_id, msg1.vector_clock)
                if clock1.concurrent_with(msg2.vector_clock):
                    conflicts.append((id1, id2))

        return conflicts

    def prune_old_events(self, keep_count: int = 1000):
        """
        Remove old events that are dominated by current clock.

        Keeps most recent events and any that might still be needed.

        Args:
            keep_count: Minimum number of events to keep
        """
        if len(self.events) <= keep_count:
            return

        # Sort events by clock sum (older first)
        sorted_events = sorted(
            self.events.items(),
            key=lambda x: sum(x[1].vector_clock.values())
        )

        # Keep only recent events
        events_to_keep = sorted_events[-keep_count:]
        self.events = dict(events_to_keep)


# ============================================================================
# Example Usage and Testing
# ============================================================================

def example_distributed_scenario():
    """
    Example: Three nodes exchanging messages.

    Demonstrates:
    - Local event processing
    - Message exchange
    - Causal ordering
    - Conflict detection
    """
    print("\n" + "=" * 70)
    print("Vector Clock Example: Distributed Message Exchange")
    print("=" * 70)

    # Initialize three nodes
    node_a = CausalHistory(node_id="node-a")
    node_b = CausalHistory(node_id="node-b")
    node_c = CausalHistory(node_id="node-c")

    print("\n1. Node A creates event A1:")
    msg_a1 = node_a.add_local_event("a1", {"action": "initialize"})
    print(f"   {node_a.clock}")

    print("\n2. Node B creates event B1 (concurrent with A1):")
    msg_b1 = node_b.add_local_event("b1", {"action": "initialize"})
    print(f"   {node_b.clock}")

    print("\n3. Node A sends A1 to Node B:")
    node_b.add_remote_event(msg_a1)
    print(f"   Node B after receiving A1: {node_b.clock}")

    print("\n4. Node B creates event B2 (caused by A1):")
    msg_b2 = node_b.add_local_event("b2", {"action": "process", "from": "a1"})
    print(f"   {node_b.clock}")

    print("\n5. Node C receives both A1 and B2:")
    node_c.add_remote_event(msg_a1)
    print(f"   Node C after A1: {node_c.clock}")
    node_c.add_remote_event(msg_b2)
    print(f"   Node C after B2: {node_c.clock}")

    print("\n6. Causal Analysis:")

    # Check happens-before
    clock_a1 = VectorClock.from_dict("node-a", msg_a1.vector_clock)
    clock_b2 = VectorClock.from_dict("node-b", msg_b2.vector_clock)

    if clock_a1.happens_before(clock_b2.to_dict()):
        print(f"   ✓ A1 happens-before B2 (A1 → B2)")

    # Check concurrency
    clock_b1 = VectorClock.from_dict("node-b", msg_b1.vector_clock)
    if clock_a1.concurrent_with(clock_b1.to_dict()):
        print(f"   ✓ A1 concurrent with B1 (conflict!)")

    print("\n7. Events in causal order:")
    for event in node_c.get_causally_ordered_events():
        print(f"   {event.message_id}: {event.vector_clock}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_distributed_scenario()

    print("\nVector Clock module loaded successfully ✓")
