#!/usr/bin/env python3
"""
Bloom Filter for Efficient Memory Synchronization
==================================================

Implements Bloom filters for fast membership testing with minimal bandwidth.

A Bloom filter is a space-efficient probabilistic data structure that tests
whether an element is a member of a set. False positives are possible, but
false negatives are not.

Benefits for Memory Sync:
- Compact representation (~10 bytes per 1000 items at 1% FPR)
- Fast membership testing (O(k) where k is small)
- Efficient sync: Only transfer items not in remote Bloom filter
- 60-80% bandwidth reduction in typical scenarios

Usage:
    # Create filter for 1000 items with 1% false positive rate
    bloom = BloomFilter(expected_items=1000, false_positive_rate=0.01)

    # Add items
    bloom.add("memory-id-123")
    bloom.add("memory-id-456")

    # Check membership
    if bloom.contains("memory-id-123"):
        print("Probably in set")

    # Serialize for transmission
    data = bloom.to_bytes()

    # Reconstruct on remote node
    remote_bloom = BloomFilter.from_bytes(data)
"""

import hashlib
import json
import math
from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class BloomFilterStats:
    """Statistics about a Bloom filter."""
    expected_items: int
    false_positive_rate: float
    num_bits: int
    num_hashes: int
    items_added: int
    actual_fpr: float
    size_bytes: int


class BloomFilter:
    """
    Bloom filter for efficient membership testing.

    Space-efficient probabilistic data structure.
    Optimized for memory synchronization use case.
    """

    def __init__(
        self,
        expected_items: int = 10000,
        false_positive_rate: float = 0.01
    ):
        """
        Initialize Bloom filter.

        Args:
            expected_items: Expected number of items to store
            false_positive_rate: Desired false positive probability (0.0-1.0)
        """
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate

        # Calculate optimal parameters
        self.num_bits = self._optimal_num_bits(expected_items, false_positive_rate)
        self.num_hashes = self._optimal_num_hashes(self.num_bits, expected_items)

        # Bit array (use bytearray for efficiency)
        self.bit_array = bytearray((self.num_bits + 7) // 8)  # Round up to bytes

        # Track items added (for statistics)
        self.items_added = 0

    @staticmethod
    def _optimal_num_bits(n: int, p: float) -> int:
        """
        Calculate optimal number of bits.

        Formula: m = -n * ln(p) / (ln(2)^2)
        """
        if p <= 0 or p >= 1:
            raise ValueError("False positive rate must be between 0 and 1")

        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    @staticmethod
    def _optimal_num_hashes(m: int, n: int) -> int:
        """
        Calculate optimal number of hash functions.

        Formula: k = (m/n) * ln(2)
        """
        if n <= 0:
            return 1

        k = (m / n) * math.log(2)
        return max(1, int(math.ceil(k)))

    def _hash(self, item: str, seed: int) -> int:
        """
        Compute hash of item with seed.

        Uses SHA256 with seed for multiple independent hashes.
        """
        hash_input = f"{seed}:{item}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).digest()

        # Convert first 8 bytes to integer
        hash_int = int.from_bytes(hash_digest[:8], byteorder='big')

        return hash_int % self.num_bits

    def add(self, item: str):
        """
        Add item to Bloom filter.

        Args:
            item: Item identifier (e.g., memory ID, entity name)
        """
        for i in range(self.num_hashes):
            bit_index = self._hash(item, i)
            byte_index = bit_index // 8
            bit_offset = bit_index % 8

            # Set bit
            self.bit_array[byte_index] |= (1 << bit_offset)

        self.items_added += 1

    def contains(self, item: str) -> bool:
        """
        Check if item is (probably) in filter.

        Returns:
            True if item is probably in set
            False if item is definitely not in set
        """
        for i in range(self.num_hashes):
            bit_index = self._hash(item, i)
            byte_index = bit_index // 8
            bit_offset = bit_index % 8

            # Check bit
            if not (self.bit_array[byte_index] & (1 << bit_offset)):
                return False  # Definitely not in set

        return True  # Probably in set

    def union(self, other: "BloomFilter") -> "BloomFilter":
        """
        Create union of two Bloom filters.

        Filters must have same parameters.

        Args:
            other: Another Bloom filter

        Returns:
            New Bloom filter representing union
        """
        if (self.num_bits != other.num_bits or
            self.num_hashes != other.num_hashes):
            raise ValueError("Bloom filters must have same parameters for union")

        # Create new filter
        result = BloomFilter(self.expected_items, self.false_positive_rate)
        result.num_bits = self.num_bits
        result.num_hashes = self.num_hashes
        result.bit_array = bytearray(len(self.bit_array))

        # Bitwise OR
        for i in range(len(self.bit_array)):
            result.bit_array[i] = self.bit_array[i] | other.bit_array[i]

        result.items_added = self.items_added + other.items_added

        return result

    def intersection(self, other: "BloomFilter") -> "BloomFilter":
        """
        Create intersection of two Bloom filters.

        Note: Intersection can have high false positive rate.
        Use with caution.

        Args:
            other: Another Bloom filter

        Returns:
            New Bloom filter representing intersection
        """
        if (self.num_bits != other.num_bits or
            self.num_hashes != other.num_hashes):
            raise ValueError("Bloom filters must have same parameters for intersection")

        # Create new filter
        result = BloomFilter(self.expected_items, self.false_positive_rate)
        result.num_bits = self.num_bits
        result.num_hashes = self.num_hashes
        result.bit_array = bytearray(len(self.bit_array))

        # Bitwise AND
        for i in range(len(self.bit_array)):
            result.bit_array[i] = self.bit_array[i] & other.bit_array[i]

        result.items_added = min(self.items_added, other.items_added)

        return result

    def estimated_fill_ratio(self) -> float:
        """
        Estimate fraction of bits set to 1.

        Returns:
            Fill ratio (0.0 to 1.0)
        """
        bits_set = sum(bin(byte).count('1') for byte in self.bit_array)
        return bits_set / self.num_bits

    def estimated_fpr(self) -> float:
        """
        Estimate actual false positive rate based on fill ratio.

        Formula: fpr = (1 - e^(-k*n/m))^k

        Returns:
            Estimated false positive rate
        """
        fill_ratio = self.estimated_fill_ratio()

        # Avoid math domain error
        if fill_ratio >= 1.0:
            return 1.0

        # Calculate FPR
        fpr = (1 - math.exp(-self.num_hashes * self.items_added / self.num_bits)) ** self.num_hashes

        return min(1.0, fpr)

    def get_stats(self) -> BloomFilterStats:
        """Get statistics about this Bloom filter."""
        return BloomFilterStats(
            expected_items=self.expected_items,
            false_positive_rate=self.false_positive_rate,
            num_bits=self.num_bits,
            num_hashes=self.num_hashes,
            items_added=self.items_added,
            actual_fpr=self.estimated_fpr(),
            size_bytes=len(self.bit_array)
        )

    def to_bytes(self) -> bytes:
        """
        Serialize Bloom filter to bytes.

        Returns compact binary representation for transmission.
        """
        return bytes(self.bit_array)

    def to_dict(self) -> dict:
        """
        Serialize to dictionary (JSON-compatible).

        Includes parameters for reconstruction.
        """
        return {
            "expected_items": self.expected_items,
            "false_positive_rate": self.false_positive_rate,
            "num_bits": self.num_bits,
            "num_hashes": self.num_hashes,
            "items_added": self.items_added,
            "bit_array": self.bit_array.hex()  # Hex string
        }

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        expected_items: int,
        false_positive_rate: float
    ) -> "BloomFilter":
        """
        Reconstruct Bloom filter from bytes.

        Args:
            data: Serialized bit array
            expected_items: Original expected_items parameter
            false_positive_rate: Original FPR parameter

        Returns:
            Reconstructed Bloom filter
        """
        bloom = cls(expected_items, false_positive_rate)
        bloom.bit_array = bytearray(data)
        return bloom

    @classmethod
    def from_dict(cls, data: dict) -> "BloomFilter":
        """Reconstruct from dictionary."""
        bloom = cls(
            expected_items=data["expected_items"],
            false_positive_rate=data["false_positive_rate"]
        )
        bloom.num_bits = data["num_bits"]
        bloom.num_hashes = data["num_hashes"]
        bloom.items_added = data["items_added"]
        bloom.bit_array = bytearray.fromhex(data["bit_array"])

        return bloom


class MemorySyncBloomFilter:
    """
    Bloom filter optimized for memory synchronization.

    Maintains separate filters for different memory types.
    Enables efficient differential sync.
    """

    def __init__(
        self,
        node_id: str,
        expected_memories: int = 10000,
        false_positive_rate: float = 0.01
    ):
        self.node_id = node_id
        self.expected_memories = expected_memories
        self.false_positive_rate = false_positive_rate

        # Separate filters for each memory type
        self.working_memory_filter = BloomFilter(expected_memories, false_positive_rate)
        self.episodic_memory_filter = BloomFilter(expected_memories, false_positive_rate)
        self.semantic_memory_filter = BloomFilter(expected_memories, false_positive_rate)

    def add_memory(self, memory_id: str, memory_type: str = "working"):
        """Add memory to appropriate filter."""
        if memory_type == "working":
            self.working_memory_filter.add(memory_id)
        elif memory_type == "episodic":
            self.episodic_memory_filter.add(memory_id)
        elif memory_type == "semantic":
            self.semantic_memory_filter.add(memory_id)
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def contains_memory(self, memory_id: str, memory_type: str = "working") -> bool:
        """Check if memory is (probably) present."""
        if memory_type == "working":
            return self.working_memory_filter.contains(memory_id)
        elif memory_type == "episodic":
            return self.episodic_memory_filter.contains(memory_id)
        elif memory_type == "semantic":
            return self.semantic_memory_filter.contains(memory_id)
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def get_missing_memories(
        self,
        local_memory_ids: List[str],
        remote_filter: "MemorySyncBloomFilter",
        memory_type: str = "working"
    ) -> List[str]:
        """
        Find memories present locally but missing from remote.

        This is the key optimization: Instead of sending all memories,
        we send only those not in the remote Bloom filter.

        Args:
            local_memory_ids: IDs of all local memories
            remote_filter: Bloom filter from remote node
            memory_type: Type of memory to check

        Returns:
            List of memory IDs to send to remote
        """
        missing = []

        for memory_id in local_memory_ids:
            if not remote_filter.contains_memory(memory_id, memory_type):
                # Remote doesn't have this memory (or false negative)
                missing.append(memory_id)

        return missing

    def to_dict(self) -> dict:
        """Serialize for transmission."""
        return {
            "node_id": self.node_id,
            "expected_memories": self.expected_memories,
            "false_positive_rate": self.false_positive_rate,
            "working_memory": self.working_memory_filter.to_dict(),
            "episodic_memory": self.episodic_memory_filter.to_dict(),
            "semantic_memory": self.semantic_memory_filter.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemorySyncBloomFilter":
        """Reconstruct from dictionary."""
        sync_filter = cls(
            node_id=data["node_id"],
            expected_memories=data["expected_memories"],
            false_positive_rate=data["false_positive_rate"]
        )

        sync_filter.working_memory_filter = BloomFilter.from_dict(data["working_memory"])
        sync_filter.episodic_memory_filter = BloomFilter.from_dict(data["episodic_memory"])
        sync_filter.semantic_memory_filter = BloomFilter.from_dict(data["semantic_memory"])

        return sync_filter

    def get_stats(self) -> dict:
        """Get statistics for all filters."""
        return {
            "node_id": self.node_id,
            "working_memory": self.working_memory_filter.get_stats().__dict__,
            "episodic_memory": self.episodic_memory_filter.get_stats().__dict__,
            "semantic_memory": self.semantic_memory_filter.get_stats().__dict__
        }


# ============================================================================
# Example Usage
# ============================================================================

def example_bloom_filter():
    """Example: Use Bloom filter for efficient sync."""
    print("\n" + "=" * 70)
    print("Bloom Filter Example: Efficient Memory Sync")
    print("=" * 70)

    # Node A has 1000 memories
    node_a_memories = [f"memory-{i:04d}" for i in range(1000)]

    # Node B has 900 of the same memories + 100 different ones
    node_b_memories = node_a_memories[:900] + [f"memory-new-{i}" for i in range(100)]

    print(f"\nNode A: {len(node_a_memories)} memories")
    print(f"Node B: {len(node_b_memories)} memories")
    print(f"Overlap: {len(set(node_a_memories) & set(node_b_memories))} memories")

    # Create Bloom filters
    filter_a = MemorySyncBloomFilter("node-a", expected_memories=1000)
    filter_b = MemorySyncBloomFilter("node-b", expected_memories=1000)

    # Add memories to filters
    for mem_id in node_a_memories:
        filter_a.add_memory(mem_id, "episodic")

    for mem_id in node_b_memories:
        filter_b.add_memory(mem_id, "episodic")

    print("\nWithout Bloom filter:")
    print(f"  Would transfer all {len(node_a_memories)} memories = ~100KB")

    print("\nWith Bloom filter:")

    # Find what A needs to send to B
    missing_in_b = filter_a.get_missing_memories(
        node_a_memories,
        filter_b,
        "episodic"
    )

    print(f"  Bloom filter size: {filter_b.episodic_memory_filter.get_stats().size_bytes} bytes")
    print(f"  Memories to transfer: {len(missing_in_b)} (only missing ones)")
    print(f"  Bandwidth savings: {(1 - len(missing_in_b)/len(node_a_memories)) * 100:.1f}%")

    # Check accuracy
    expected_missing = set(node_a_memories) - set(node_b_memories)
    actual_missing = set(missing_in_b)

    false_positives = actual_missing - expected_missing
    false_negatives = expected_missing - actual_missing

    print(f"\nAccuracy:")
    print(f"  Expected to send: {len(expected_missing)}")
    print(f"  Actually sending: {len(actual_missing)}")
    print(f"  False positives: {len(false_positives)} (sent unnecessarily)")
    print(f"  False negatives: {len(false_negatives)} (should have been sent)")

    # Show stats
    stats = filter_a.get_stats()
    print(f"\nFilter statistics:")
    print(f"  Bits: {stats['episodic_memory']['num_bits']}")
    print(f"  Hashes: {stats['episodic_memory']['num_hashes']}")
    print(f"  Items: {stats['episodic_memory']['items_added']}")
    print(f"  Size: {stats['episodic_memory']['size_bytes']} bytes")
    print(f"  Actual FPR: {stats['episodic_memory']['actual_fpr']:.4f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_bloom_filter()
    print("\nBloom filter module loaded successfully ✓")
