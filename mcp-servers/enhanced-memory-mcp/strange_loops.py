#!/usr/bin/env python3
"""
Strange Loops Detector - Ported from ruvnet/agentic-flow

Detects circular reasoning, contradictions, and recursive patterns
in logical structures. Essential for AGI self-improvement validation.

Original: src/verification/patterns/strange-loops-detector.ts

Key capabilities:
- Circular reasoning detection using DFS cycle detection
- Contradiction detection with semantic keyword matching
- Causal chain validation (cycles, weak links)
- Recursive pattern detection (self-references, nested definitions)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PatternType(Enum):
    """Types of strange loop patterns detected."""
    CIRCULAR = "circular"
    CONTRADICTION = "contradiction"
    INVALID_CAUSAL = "invalid-causal"
    SELF_REFERENCE = "self-reference"
    NESTED_DEFINITION = "nested-definition"
    RECURSIVE = "recursive"


class Severity(Enum):
    """Severity levels for detected patterns."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EdgeType(Enum):
    """Types of causal edges."""
    CAUSES = "causes"
    IMPLIES = "implies"
    CORRELATES = "correlates"
    DEPENDS = "depends"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LogicalPattern:
    """A detected logical pattern (strange loop, contradiction, etc.)."""
    id: str
    type: PatternType
    description: str
    severity: Severity
    affected_nodes: List[str]
    evidence: List[str]
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity.value,
            "affected_nodes": self.affected_nodes,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class CausalNode:
    """A node in a causal chain."""
    id: str
    statement: str
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "confidence": self.confidence
        }


@dataclass
class CausalEdge:
    """An edge in a causal chain."""
    from_node: str
    to_node: str
    strength: float = 1.0
    edge_type: EdgeType = EdgeType.CAUSES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "strength": self.strength,
            "type": self.edge_type.value
        }


@dataclass
class CausalChain:
    """A causal chain with nodes and edges."""
    id: str
    nodes: List[CausalNode]
    edges: List[CausalEdge]
    is_valid: bool = True
    cyclic_references: List[List[str]] = field(default_factory=list)
    weak_links: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "is_valid": self.is_valid,
            "cyclic_references": self.cyclic_references,
            "weak_links": self.weak_links
        }


@dataclass
class ChainContradiction:
    """A contradiction found in a causal chain."""
    node_a: str
    node_b: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_a": self.node_a,
            "node_b": self.node_b,
            "reason": self.reason
        }


@dataclass
class RecursivePattern:
    """A detected recursive pattern."""
    pattern_id: str
    depth: int
    elements: List[str]
    pattern_type: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "depth": self.depth,
            "elements": self.elements,
            "pattern_type": self.pattern_type
        }


@dataclass
class ValidationResult:
    """Result of causal chain validation."""
    is_valid: bool
    cycles: List[List[str]]
    weak_links: List[CausalEdge]
    contradictions: List[ChainContradiction]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "cycles": self.cycles,
            "weak_links": [e.to_dict() for e in self.weak_links],
            "contradictions": [c.to_dict() for c in self.contradictions]
        }


# =============================================================================
# Strange Loops Detector
# =============================================================================

class StrangeLoopsDetector:
    """
    Detects strange loops, circular reasoning, and logical contradictions.

    Core capabilities:
    1. Circular reasoning detection via DFS cycle detection
    2. Contradiction detection via semantic keyword matching
    3. Causal chain validation (cycles, weak links)
    4. Recursive pattern detection (self-references, nested definitions)
    """

    # Contradiction keyword pairs (if A and B appear, potential contradiction)
    CONTRADICTION_PAIRS = [
        (["always", "never"], "temporal contradiction"),
        (["all", "none"], "universal contradiction"),
        (["true", "false"], "boolean contradiction"),
        (["increase", "decrease"], "directional contradiction"),
        (["yes", "no"], "affirmation contradiction"),
        (["must", "cannot"], "modal contradiction"),
        (["enable", "disable"], "state contradiction"),
        (["include", "exclude"], "set contradiction"),
        (["positive", "negative"], "polarity contradiction"),
        (["accept", "reject"], "decision contradiction"),
    ]

    # Weak link threshold
    WEAK_LINK_THRESHOLD = 0.5

    def __init__(self):
        """Initialize the strange loops detector."""
        self.detected_patterns: List[LogicalPattern] = []
        self.detection_count = 0
        self.stats = {
            "circular_detections": 0,
            "contradiction_detections": 0,
            "causal_validations": 0,
            "recursive_detections": 0
        }

    def _generate_pattern_id(self, pattern_type: PatternType, evidence: List[str]) -> str:
        """Generate unique pattern ID."""
        content = f"{pattern_type.value}:{':'.join(evidence)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # =========================================================================
    # Circular Reasoning Detection
    # =========================================================================

    def detect_circular_reasoning(
        self,
        graph: Dict[str, List[str]]
    ) -> List[LogicalPattern]:
        """
        Detect circular reasoning using DFS cycle detection.

        Args:
            graph: Adjacency list representation of reasoning graph
                   {node_id: [list of nodes this node points to]}

        Returns:
            List of detected circular patterns
        """
        patterns = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        all_cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            """DFS to find cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle - extract it
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    all_cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        # Run DFS from each unvisited node
        for node in graph:
            if node not in visited:
                dfs(node, [])

        # Create patterns for each cycle
        for cycle in all_cycles:
            # Determine severity based on cycle length
            if len(cycle) <= 2:
                severity = Severity.CRITICAL  # Direct self-reference
            elif len(cycle) <= 4:
                severity = Severity.HIGH
            elif len(cycle) <= 6:
                severity = Severity.MEDIUM
            else:
                severity = Severity.LOW

            pattern = LogicalPattern(
                id=self._generate_pattern_id(PatternType.CIRCULAR, cycle),
                type=PatternType.CIRCULAR,
                description=f"Circular reasoning detected: {' -> '.join(cycle)}",
                severity=severity,
                affected_nodes=cycle,
                evidence=[f"Cycle of length {len(cycle) - 1}"]
            )
            patterns.append(pattern)
            self.detected_patterns.append(pattern)

        self.stats["circular_detections"] += len(patterns)
        self.detection_count += len(patterns)

        return patterns

    # =========================================================================
    # Contradiction Detection
    # =========================================================================

    def detect_contradictions(
        self,
        statements: List[str]
    ) -> List[LogicalPattern]:
        """
        Detect contradictions using keyword-based semantic matching.

        Args:
            statements: List of statements to check for contradictions

        Returns:
            List of detected contradiction patterns
        """
        patterns = []

        # Normalize statements for comparison
        normalized = [s.lower().strip() for s in statements]

        # Check each pair of statements
        for i, stmt1 in enumerate(normalized):
            for j, stmt2 in enumerate(normalized):
                if i >= j:
                    continue

                # Check for contradiction pairs
                for keywords, contradiction_type in self.CONTRADICTION_PAIRS:
                    has_first = any(kw in stmt1 for kw in keywords[:1])
                    has_second = any(kw in stmt2 for kw in keywords[1:])

                    # Also check reverse
                    has_first_rev = any(kw in stmt2 for kw in keywords[:1])
                    has_second_rev = any(kw in stmt1 for kw in keywords[1:])

                    if (has_first and has_second) or (has_first_rev and has_second_rev):
                        pattern = LogicalPattern(
                            id=self._generate_pattern_id(
                                PatternType.CONTRADICTION,
                                [statements[i], statements[j]]
                            ),
                            type=PatternType.CONTRADICTION,
                            description=f"Potential {contradiction_type} between statements",
                            severity=Severity.HIGH,
                            affected_nodes=[statements[i], statements[j]],
                            evidence=[
                                f"Statement 1: {statements[i]}",
                                f"Statement 2: {statements[j]}",
                                f"Contradiction type: {contradiction_type}"
                            ]
                        )
                        patterns.append(pattern)
                        self.detected_patterns.append(pattern)
                        break  # One contradiction per pair is enough

        self.stats["contradiction_detections"] += len(patterns)
        self.detection_count += len(patterns)

        return patterns

    # =========================================================================
    # Causal Chain Validation
    # =========================================================================

    def validate_causal_chain(self, chain: CausalChain) -> ValidationResult:
        """
        Validate a causal chain for cycles and weak links.

        Args:
            chain: CausalChain to validate

        Returns:
            ValidationResult with cycles, weak links, and contradictions
        """
        self.stats["causal_validations"] += 1

        # Build adjacency list from edges
        graph: Dict[str, List[str]] = {}
        for edge in chain.edges:
            if edge.from_node not in graph:
                graph[edge.from_node] = []
            graph[edge.from_node].append(edge.to_node)

        # Detect cycles
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def find_cycles(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    find_cycles(neighbor, path)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                find_cycles(node, [])

        # Find weak links (strength below threshold)
        weak_links = [
            edge for edge in chain.edges
            if edge.strength < self.WEAK_LINK_THRESHOLD
        ]

        # Build node lookup for contradiction check
        node_lookup = {node.id: node for node in chain.nodes}

        # Check for contradictions between connected nodes
        contradictions: List[ChainContradiction] = []
        for edge in chain.edges:
            from_node = node_lookup.get(edge.from_node)
            to_node = node_lookup.get(edge.to_node)

            if from_node and to_node:
                # Simple keyword-based contradiction check
                stmt1 = from_node.statement.lower()
                stmt2 = to_node.statement.lower()

                for keywords, contradiction_type in self.CONTRADICTION_PAIRS:
                    has_first = any(kw in stmt1 for kw in keywords[:1])
                    has_second = any(kw in stmt2 for kw in keywords[1:])

                    if has_first and has_second:
                        contradictions.append(ChainContradiction(
                            node_a=edge.from_node,
                            node_b=edge.to_node,
                            reason=contradiction_type
                        ))
                        break

        # Chain is valid if no cycles, no weak links, and no contradictions
        is_valid = len(cycles) == 0 and len(weak_links) == 0 and len(contradictions) == 0

        # Create pattern for invalid chain
        if not is_valid:
            evidence = []
            if cycles:
                evidence.append(f"Contains {len(cycles)} cycle(s)")
            if weak_links:
                evidence.append(f"Contains {len(weak_links)} weak link(s)")
            if contradictions:
                evidence.append(f"Contains {len(contradictions)} contradiction(s)")

            pattern = LogicalPattern(
                id=self._generate_pattern_id(PatternType.INVALID_CAUSAL, [chain.id]),
                type=PatternType.INVALID_CAUSAL,
                description=f"Invalid causal chain: {chain.id}",
                severity=Severity.HIGH if cycles else Severity.MEDIUM,
                affected_nodes=[n.id for n in chain.nodes],
                evidence=evidence
            )
            self.detected_patterns.append(pattern)
            self.detection_count += 1

        # Update chain validity
        chain.is_valid = is_valid
        chain.cyclic_references = cycles
        chain.weak_links = [e.from_node + "->" + e.to_node for e in weak_links]

        return ValidationResult(
            is_valid=is_valid,
            cycles=cycles,
            weak_links=weak_links,
            contradictions=contradictions
        )

    # =========================================================================
    # Recursive Pattern Detection
    # =========================================================================

    def detect_recursive_patterns(
        self,
        structure: Any,
        path: Optional[List[str]] = None,
        seen: Optional[Set[int]] = None
    ) -> List[RecursivePattern]:
        """
        Detect recursive patterns (self-references, nested definitions).

        Args:
            structure: Any nested structure (dict, list, object)
            path: Current path in structure (for tracking)
            seen: Set of seen object IDs (for cycle detection)

        Returns:
            List of detected recursive patterns
        """
        if path is None:
            path = []
        if seen is None:
            seen = set()

        patterns: List[RecursivePattern] = []

        # Check for object identity cycle (same object referenced again)
        obj_id = id(structure)
        if obj_id in seen:
            pattern = RecursivePattern(
                pattern_id=self._generate_pattern_id(
                    PatternType.SELF_REFERENCE,
                    path
                ),
                depth=len(path),
                elements=path.copy(),
                pattern_type="self-reference"
            )
            patterns.append(pattern)

            # Create logical pattern
            logical_pattern = LogicalPattern(
                id=pattern.pattern_id,
                type=PatternType.SELF_REFERENCE,
                description=f"Self-reference detected at depth {len(path)}",
                severity=Severity.HIGH,
                affected_nodes=path,
                evidence=[f"Object references itself at path: {' -> '.join(path)}"]
            )
            self.detected_patterns.append(logical_pattern)
            self.detection_count += 1
            self.stats["recursive_detections"] += 1

            return patterns

        seen.add(obj_id)

        # Recursively check nested structures
        if isinstance(structure, dict):
            for key, value in structure.items():
                new_path = path + [str(key)]
                nested_patterns = self.detect_recursive_patterns(value, new_path, seen)
                patterns.extend(nested_patterns)

        elif isinstance(structure, (list, tuple)):
            for i, item in enumerate(structure):
                new_path = path + [f"[{i}]"]
                nested_patterns = self.detect_recursive_patterns(item, new_path, seen)
                patterns.extend(nested_patterns)

        elif hasattr(structure, "__dict__"):
            for key, value in structure.__dict__.items():
                if not key.startswith("_"):  # Skip private attributes
                    new_path = path + [str(key)]
                    nested_patterns = self.detect_recursive_patterns(value, new_path, seen)
                    patterns.extend(nested_patterns)

        seen.discard(obj_id)  # Remove when backtracking

        return patterns

    # =========================================================================
    # Statistics and Reporting
    # =========================================================================

    def get_all_patterns(self) -> List[LogicalPattern]:
        """Get all detected patterns."""
        return self.detected_patterns

    def get_patterns_by_type(self, pattern_type: PatternType) -> List[LogicalPattern]:
        """Get patterns of a specific type."""
        return [p for p in self.detected_patterns if p.type == pattern_type]

    def get_patterns_by_severity(self, severity: Severity) -> List[LogicalPattern]:
        """Get patterns of a specific severity."""
        return [p for p in self.detected_patterns if p.severity == severity]

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        severity_counts = {}
        for sev in Severity:
            severity_counts[sev.value] = len(self.get_patterns_by_severity(sev))

        type_counts = {}
        for pt in PatternType:
            type_counts[pt.value] = len(self.get_patterns_by_type(pt))

        return {
            "total_detections": self.detection_count,
            "pattern_count": len(self.detected_patterns),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "operations": self.stats
        }

    def clear_patterns(self) -> None:
        """Clear all detected patterns."""
        self.detected_patterns = []
        self.detection_count = 0

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = {
            "circular_detections": 0,
            "contradiction_detections": 0,
            "causal_validations": 0,
            "recursive_detections": 0
        }


# =============================================================================
# MCP Tool Registration
# =============================================================================

def register_strange_loops_tools(app) -> StrangeLoopsDetector:
    """
    Register Strange Loops detection tools with MCP server.

    Tools registered:
    - sl_detect_circular: Detect circular reasoning in graph
    - sl_detect_contradictions: Detect contradictions in statements
    - sl_validate_chain: Validate causal chain
    - sl_detect_recursive: Detect recursive patterns
    - sl_get_patterns: Get detected patterns
    - sl_status: Get detector status

    Args:
        app: FastMCP app instance

    Returns:
        StrangeLoopsDetector instance
    """
    detector = StrangeLoopsDetector()

    @app.tool()
    async def sl_detect_circular(
        graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Detect circular reasoning patterns in a directed graph.

        Uses DFS-based cycle detection to find circular reasoning.

        Args:
            graph: Adjacency list {node_id: [list of connected nodes]}

        Returns:
            List of detected circular patterns with severity

        Example:
            sl_detect_circular({
                "A": ["B"],
                "B": ["C"],
                "C": ["A"]  # Creates cycle A->B->C->A
            })
        """
        patterns = detector.detect_circular_reasoning(graph)
        return {
            "patterns_found": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "stats": detector.get_stats()
        }

    @app.tool()
    async def sl_detect_contradictions(
        statements: List[str]
    ) -> Dict[str, Any]:
        """
        Detect contradictions between statements.

        Uses keyword-based semantic matching to find contradictions
        like "always/never", "true/false", "increase/decrease".

        Args:
            statements: List of statements to check

        Returns:
            List of detected contradiction patterns

        Example:
            sl_detect_contradictions([
                "The system always restarts at midnight",
                "The system never restarts automatically"
            ])
        """
        patterns = detector.detect_contradictions(statements)
        return {
            "patterns_found": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "stats": detector.get_stats()
        }

    @app.tool()
    async def sl_validate_chain(
        chain_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a causal chain for cycles and weak links.

        Args:
            chain_id: Unique identifier for the chain
            nodes: List of nodes [{id, statement, confidence}]
            edges: List of edges [{from, to, strength, type}]

        Returns:
            Validation result with cycles, weak links, contradictions

        Example:
            sl_validate_chain(
                chain_id="chain_001",
                nodes=[
                    {"id": "A", "statement": "Rain falls", "confidence": 0.9},
                    {"id": "B", "statement": "Ground is wet", "confidence": 0.95}
                ],
                edges=[
                    {"from": "A", "to": "B", "strength": 0.8, "type": "causes"}
                ]
            )
        """
        # Convert to dataclasses
        causal_nodes = [
            CausalNode(
                id=n["id"],
                statement=n.get("statement", ""),
                confidence=n.get("confidence", 1.0)
            )
            for n in nodes
        ]

        causal_edges = [
            CausalEdge(
                from_node=e["from"],
                to_node=e["to"],
                strength=e.get("strength", 1.0),
                edge_type=EdgeType(e.get("type", "causes"))
            )
            for e in edges
        ]

        chain = CausalChain(
            id=chain_id,
            nodes=causal_nodes,
            edges=causal_edges
        )

        result = detector.validate_causal_chain(chain)

        return {
            "chain_id": chain_id,
            "is_valid": result.is_valid,
            "cycles": result.cycles,
            "weak_links": [e.to_dict() for e in result.weak_links],
            "contradictions": [c.to_dict() for c in result.contradictions],
            "stats": detector.get_stats()
        }

    @app.tool()
    async def sl_detect_recursive(
        structure: Any
    ) -> Dict[str, Any]:
        """
        Detect recursive patterns (self-references, nested definitions).

        Analyzes nested structures for circular references.

        Args:
            structure: Any JSON-serializable nested structure

        Returns:
            List of detected recursive patterns

        Example:
            sl_detect_recursive({
                "name": "root",
                "children": [
                    {"name": "child1"},
                    {"name": "child2", "parent": "..."}  # Potential reference
                ]
            })
        """
        patterns = detector.detect_recursive_patterns(structure)
        return {
            "patterns_found": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "stats": detector.get_stats()
        }

    @app.tool()
    async def sl_get_patterns(
        pattern_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detected patterns with optional filtering.

        Args:
            pattern_type: Filter by type (circular, contradiction, etc.)
            severity: Filter by severity (low, medium, high, critical)

        Returns:
            Filtered list of patterns
        """
        patterns = detector.get_all_patterns()

        if pattern_type:
            try:
                pt = PatternType(pattern_type)
                patterns = [p for p in patterns if p.type == pt]
            except ValueError:
                pass

        if severity:
            try:
                sev = Severity(severity)
                patterns = [p for p in patterns if p.severity == sev]
            except ValueError:
                pass

        return {
            "pattern_count": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "filters_applied": {
                "pattern_type": pattern_type,
                "severity": severity
            }
        }

    @app.tool()
    async def sl_status() -> Dict[str, Any]:
        """
        Get Strange Loops Detector status and statistics.

        Returns:
            Detector statistics including detection counts by type and severity
        """
        stats = detector.get_stats()
        return {
            "detector": "StrangeLoopsDetector",
            "version": "1.0.0",
            "ported_from": "ruvnet/agentic-flow",
            "original_file": "src/verification/patterns/strange-loops-detector.ts",
            "capabilities": [
                "circular_reasoning_detection",
                "contradiction_detection",
                "causal_chain_validation",
                "recursive_pattern_detection"
            ],
            "statistics": stats
        }

    @app.tool()
    async def sl_clear() -> Dict[str, Any]:
        """
        Clear all detected patterns and reset statistics.

        Returns:
            Confirmation of reset
        """
        old_count = len(detector.detected_patterns)
        detector.clear_patterns()
        detector.reset_stats()
        return {
            "cleared": True,
            "patterns_removed": old_count,
            "stats_reset": True
        }

    logger.info("Strange Loops Detector tools registered: sl_detect_circular, "
                "sl_detect_contradictions, sl_validate_chain, sl_detect_recursive, "
                "sl_get_patterns, sl_status, sl_clear")

    return detector


# =============================================================================
# Standalone Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_detector():
        """Test the Strange Loops Detector."""
        print("=" * 60)
        print("Strange Loops Detector - Standalone Test")
        print("=" * 60)

        detector = StrangeLoopsDetector()

        # Test 1: Circular reasoning detection
        print("\n=== Test 1: Circular Reasoning ===")
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],  # Cycle!
            "D": ["E"],
            "E": ["D"]   # Another cycle!
        }
        patterns = detector.detect_circular_reasoning(graph)
        print(f"  Found {len(patterns)} circular patterns")
        for p in patterns:
            print(f"  - {p.description} (severity: {p.severity.value})")

        # Test 2: Contradiction detection
        print("\n=== Test 2: Contradiction Detection ===")
        statements = [
            "The system always runs at full capacity",
            "The system never runs at full capacity",
            "Temperature will increase over time",
            "Temperature will decrease over time"
        ]
        patterns = detector.detect_contradictions(statements)
        print(f"  Found {len(patterns)} contradictions")
        for p in patterns:
            print(f"  - {p.description}")

        # Test 3: Causal chain validation
        print("\n=== Test 3: Causal Chain Validation ===")
        chain = CausalChain(
            id="test_chain",
            nodes=[
                CausalNode("A", "Rain falls", 0.9),
                CausalNode("B", "Ground is wet", 0.95),
                CausalNode("C", "Plants grow", 0.8),
                CausalNode("D", "Rain falls again", 0.7)  # Potential cycle back
            ],
            edges=[
                CausalEdge("A", "B", 0.9),
                CausalEdge("B", "C", 0.8),
                CausalEdge("C", "D", 0.3),  # Weak link!
                CausalEdge("D", "A", 0.7)   # Creates cycle
            ]
        )
        result = detector.validate_causal_chain(chain)
        print(f"  Chain valid: {result.is_valid}")
        print(f"  Cycles: {len(result.cycles)}")
        print(f"  Weak links: {len(result.weak_links)}")

        # Test 4: Recursive pattern detection
        print("\n=== Test 4: Recursive Patterns ===")
        # Create structure with self-reference
        structure = {"name": "root", "children": []}
        structure["children"].append({"name": "child1", "parent": structure})  # Self-ref!
        patterns = detector.detect_recursive_patterns(structure)
        print(f"  Found {len(patterns)} recursive patterns")

        # Print final stats
        print("\n=== Final Statistics ===")
        stats = detector.get_stats()
        print(f"  Total detections: {stats['total_detections']}")
        print(f"  By type: {stats['by_type']}")
        print(f"  By severity: {stats['by_severity']}")

        print("\n✅ All tests completed!")

    asyncio.run(test_detector())
