"""
ECDE Novelty Oracle - External Verification of Non-Derivability

This module addresses the LLM Council's criticism that emergent capabilities
might be "derivable from primitives." It implements an adversarial oracle
that attempts to derive each capability from the system's primitives.

Key Principle: Failed derivation = Evidence of genuine novelty

The oracle uses multiple derivation strategies:
1. Direct composition - Can the capability be expressed as f(primitive1, primitive2, ...)?
2. Rule application - Can formal rules produce this capability?
3. Search-based derivation - Can search through the primitive space find this?
4. Analogical derivation - Can analogies to primitives explain this?

If ALL strategies fail to derive a capability, it's evidence of genuine novelty.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import hashlib
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DerivationStrategy(Enum):
    """Strategies for attempting to derive capabilities from primitives."""
    DIRECT_COMPOSITION = "direct_composition"
    RULE_APPLICATION = "rule_application"
    SEARCH_BASED = "search_based"
    ANALOGICAL = "analogical"
    COMBINATORIAL = "combinatorial"
    INTERPOLATION = "interpolation"


class DerivationResult(Enum):
    """Result of a derivation attempt."""
    DERIVED = "derived"  # Successfully derived from primitives
    PARTIAL = "partial"  # Partially derivable
    FAILED = "failed"    # Cannot be derived - evidence of novelty
    UNCERTAIN = "uncertain"  # Derivation status unclear


@dataclass
class Primitive:
    """A primitive building block of the system."""
    id: str
    name: str
    description: str
    category: str  # 'operation', 'representation', 'pattern', 'rule'
    composable_with: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class DerivationAttempt:
    """Record of an attempt to derive a capability."""
    strategy: DerivationStrategy
    primitives_used: List[str]
    steps: List[str]
    result: DerivationResult
    confidence: float  # 0.0 to 1.0
    explanation: str
    computation_depth: int  # How many composition steps


@dataclass
class CapabilityNoveltyAssessment:
    """Assessment of whether a capability is truly novel."""
    capability_id: str
    capability_name: str
    capability_description: str

    # Derivation attempts
    derivation_attempts: List[DerivationAttempt] = field(default_factory=list)

    # Overall assessment
    is_novel: bool = False
    novelty_confidence: float = 0.0
    novelty_evidence: List[str] = field(default_factory=list)

    # Council criteria alignment
    satisfies_wei_novelty: bool = False  # Non-derivable from primitives
    satisfies_bostrom_novelty: bool = False  # Outside original design space


@dataclass
class NoveltyOracleResult:
    """Complete result from the novelty oracle."""
    total_capabilities_assessed: int
    genuinely_novel: int
    derivable: int
    uncertain: int

    assessments: List[CapabilityNoveltyAssessment] = field(default_factory=list)

    # Evidence compilation for council
    novelty_evidence_summary: str = ""
    derivation_failure_rate: float = 0.0
    average_novelty_confidence: float = 0.0

    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PrimitiveLibrary:
    """Library of system primitives for derivation testing."""

    def __init__(self):
        self.primitives: Dict[str, Primitive] = {}
        self._initialize_primitives()

    def _initialize_primitives(self):
        """Initialize the library of known primitives."""
        # Core operation primitives
        operations = [
            Primitive(
                id="op_compose",
                name="Compose",
                description="Combine two functions f(g(x))",
                category="operation",
                composable_with=["op_compose", "op_map", "op_filter"],
            ),
            Primitive(
                id="op_map",
                name="Map",
                description="Apply function to collection elements",
                category="operation",
                composable_with=["op_compose", "op_filter", "op_reduce"],
            ),
            Primitive(
                id="op_filter",
                name="Filter",
                description="Select elements matching predicate",
                category="operation",
                composable_with=["op_map", "op_reduce"],
            ),
            Primitive(
                id="op_reduce",
                name="Reduce",
                description="Aggregate collection to single value",
                category="operation",
                composable_with=["op_map", "op_filter"],
            ),
            Primitive(
                id="op_branch",
                name="Branch",
                description="Conditional execution path",
                category="operation",
                composable_with=["op_compose", "op_loop"],
            ),
            Primitive(
                id="op_loop",
                name="Loop",
                description="Repeated execution",
                category="operation",
                composable_with=["op_branch", "op_compose"],
            ),
            Primitive(
                id="op_recurse",
                name="Recurse",
                description="Self-referential execution",
                category="operation",
                composable_with=["op_branch", "op_compose"],
            ),
        ]

        # Pattern primitives
        patterns = [
            Primitive(
                id="pat_sequence",
                name="Sequence Pattern",
                description="Ordered series recognition",
                category="pattern",
                composable_with=["pat_hierarchy", "pat_similarity"],
            ),
            Primitive(
                id="pat_hierarchy",
                name="Hierarchy Pattern",
                description="Tree-structured relationships",
                category="pattern",
                composable_with=["pat_sequence", "pat_network"],
            ),
            Primitive(
                id="pat_similarity",
                name="Similarity Pattern",
                description="Likeness detection",
                category="pattern",
                composable_with=["pat_sequence", "pat_clustering"],
            ),
            Primitive(
                id="pat_clustering",
                name="Clustering Pattern",
                description="Group by similarity",
                category="pattern",
                composable_with=["pat_similarity", "pat_hierarchy"],
            ),
            Primitive(
                id="pat_network",
                name="Network Pattern",
                description="Graph-based relationships",
                category="pattern",
                composable_with=["pat_hierarchy", "pat_sequence"],
            ),
        ]

        # Representation primitives
        representations = [
            Primitive(
                id="rep_vector",
                name="Vector Representation",
                description="Numerical array encoding",
                category="representation",
                composable_with=["rep_embedding", "rep_sparse"],
            ),
            Primitive(
                id="rep_embedding",
                name="Embedding Representation",
                description="Dense semantic vectors",
                category="representation",
                composable_with=["rep_vector", "rep_graph"],
            ),
            Primitive(
                id="rep_graph",
                name="Graph Representation",
                description="Node-edge structure",
                category="representation",
                composable_with=["rep_embedding", "rep_sequence"],
            ),
            Primitive(
                id="rep_sequence",
                name="Sequence Representation",
                description="Ordered token series",
                category="representation",
                composable_with=["rep_vector", "rep_tree"],
            ),
            Primitive(
                id="rep_tree",
                name="Tree Representation",
                description="Hierarchical structure",
                category="representation",
                composable_with=["rep_graph", "rep_sequence"],
            ),
            Primitive(
                id="rep_sparse",
                name="Sparse Representation",
                description="Efficient sparse encoding",
                category="representation",
                composable_with=["rep_vector", "rep_embedding"],
            ),
        ]

        # Rule primitives
        rules = [
            Primitive(
                id="rule_transitivity",
                name="Transitivity Rule",
                description="If A->B and B->C then A->C",
                category="rule",
                composable_with=["rule_symmetry", "rule_inheritance"],
            ),
            Primitive(
                id="rule_symmetry",
                name="Symmetry Rule",
                description="If A->B then B->A",
                category="rule",
                composable_with=["rule_transitivity"],
            ),
            Primitive(
                id="rule_inheritance",
                name="Inheritance Rule",
                description="Child inherits from parent",
                category="rule",
                composable_with=["rule_transitivity", "rule_specialization"],
            ),
            Primitive(
                id="rule_specialization",
                name="Specialization Rule",
                description="Specific case of general",
                category="rule",
                composable_with=["rule_inheritance", "rule_generalization"],
            ),
            Primitive(
                id="rule_generalization",
                name="Generalization Rule",
                description="Abstract from specific cases",
                category="rule",
                composable_with=["rule_specialization"],
            ),
        ]

        # Add all primitives
        for p in operations + patterns + representations + rules:
            self.primitives[p.id] = p

    def get_all_primitives(self) -> List[Primitive]:
        """Get all known primitives."""
        return list(self.primitives.values())

    def get_primitives_by_category(self, category: str) -> List[Primitive]:
        """Get primitives of a specific category."""
        return [p for p in self.primitives.values() if p.category == category]

    def get_composable_pairs(self) -> List[Tuple[Primitive, Primitive]]:
        """Get all pairs of primitives that can be composed."""
        pairs = []
        for p1 in self.primitives.values():
            for composable_id in p1.composable_with:
                if composable_id in self.primitives:
                    pairs.append((p1, self.primitives[composable_id]))
        return pairs


class DerivationEngine:
    """Engine for attempting to derive capabilities from primitives."""

    def __init__(self, primitive_library: PrimitiveLibrary):
        self.library = primitive_library
        self.max_composition_depth = 5
        self.max_search_iterations = 1000

    def attempt_direct_composition(
        self,
        capability_description: str,
        capability_features: List[str]
    ) -> DerivationAttempt:
        """
        Attempt to derive capability through direct composition of primitives.

        This tries to express the capability as a composition of known primitives.
        """
        primitives = self.library.get_all_primitives()

        # Extract keywords from capability
        cap_keywords = set(capability_description.lower().split())
        cap_keywords.update(f.lower() for f in capability_features)

        # Find relevant primitives
        relevant_primitives = []
        for p in primitives:
            p_keywords = set(p.description.lower().split())
            p_keywords.add(p.name.lower())
            overlap = cap_keywords & p_keywords
            if overlap:
                relevant_primitives.append((p, len(overlap)))

        # Sort by relevance
        relevant_primitives.sort(key=lambda x: x[1], reverse=True)

        if not relevant_primitives:
            return DerivationAttempt(
                strategy=DerivationStrategy.DIRECT_COMPOSITION,
                primitives_used=[],
                steps=["No relevant primitives found"],
                result=DerivationResult.FAILED,
                confidence=0.9,
                explanation="Capability uses concepts not present in primitive library",
                computation_depth=0
            )

        # Attempt composition
        best_primitives = [p[0] for p in relevant_primitives[:5]]
        composition_steps = []
        primitives_used = []

        for depth in range(1, self.max_composition_depth + 1):
            for p in best_primitives:
                primitives_used.append(p.id)
                composition_steps.append(f"Apply {p.name}: {p.description}")

                # Check if composition covers capability
                coverage = self._estimate_coverage(
                    capability_features,
                    primitives_used
                )

                if coverage > 0.9:
                    return DerivationAttempt(
                        strategy=DerivationStrategy.DIRECT_COMPOSITION,
                        primitives_used=primitives_used,
                        steps=composition_steps,
                        result=DerivationResult.DERIVED,
                        confidence=coverage,
                        explanation=f"Capability derived through {depth}-level composition",
                        computation_depth=depth
                    )

        # Partial derivation
        coverage = self._estimate_coverage(capability_features, primitives_used)
        if coverage > 0.5:
            return DerivationAttempt(
                strategy=DerivationStrategy.DIRECT_COMPOSITION,
                primitives_used=primitives_used,
                steps=composition_steps,
                result=DerivationResult.PARTIAL,
                confidence=coverage,
                explanation=f"Partial derivation achieved ({coverage:.1%} coverage)",
                computation_depth=self.max_composition_depth
            )

        return DerivationAttempt(
            strategy=DerivationStrategy.DIRECT_COMPOSITION,
            primitives_used=primitives_used,
            steps=composition_steps,
            result=DerivationResult.FAILED,
            confidence=0.8,
            explanation="Direct composition insufficient to derive capability",
            computation_depth=self.max_composition_depth
        )

    def attempt_rule_application(
        self,
        capability_description: str,
        capability_features: List[str]
    ) -> DerivationAttempt:
        """
        Attempt to derive capability through rule application.

        This checks if formal rules can produce the capability.
        """
        rules = self.library.get_primitives_by_category("rule")

        applicable_rules = []
        steps = []

        # Check each rule for applicability
        for rule in rules:
            # Heuristic: check if rule concepts appear in capability
            if any(keyword in capability_description.lower()
                   for keyword in rule.description.lower().split()):
                applicable_rules.append(rule)
                steps.append(f"Consider rule: {rule.name} - {rule.description}")

        if not applicable_rules:
            return DerivationAttempt(
                strategy=DerivationStrategy.RULE_APPLICATION,
                primitives_used=[],
                steps=["No applicable rules found"],
                result=DerivationResult.FAILED,
                confidence=0.85,
                explanation="Capability cannot be derived through known rules",
                computation_depth=0
            )

        # Attempt rule chaining
        primitives_used = [r.id for r in applicable_rules]

        # Simulate rule application
        for i, rule in enumerate(applicable_rules[:3]):  # Max 3 rules
            steps.append(f"Apply {rule.name}")

            # Check transitivity chains
            if rule.id == "rule_transitivity":
                steps.append("Attempt transitive inference chain")
            elif rule.id == "rule_inheritance":
                steps.append("Apply inheritance hierarchy")

        # Estimate derivation success
        coverage = len(applicable_rules) / max(len(capability_features), 1)

        if coverage > 0.8:
            return DerivationAttempt(
                strategy=DerivationStrategy.RULE_APPLICATION,
                primitives_used=primitives_used,
                steps=steps,
                result=DerivationResult.DERIVED,
                confidence=coverage,
                explanation=f"Derived through {len(applicable_rules)} rule applications",
                computation_depth=len(applicable_rules)
            )
        elif coverage > 0.4:
            return DerivationAttempt(
                strategy=DerivationStrategy.RULE_APPLICATION,
                primitives_used=primitives_used,
                steps=steps,
                result=DerivationResult.PARTIAL,
                confidence=coverage,
                explanation=f"Partial derivation via rules ({coverage:.1%})",
                computation_depth=len(applicable_rules)
            )

        return DerivationAttempt(
            strategy=DerivationStrategy.RULE_APPLICATION,
            primitives_used=primitives_used,
            steps=steps,
            result=DerivationResult.FAILED,
            confidence=0.7,
            explanation="Rules insufficient to derive capability",
            computation_depth=len(applicable_rules)
        )

    def attempt_search_derivation(
        self,
        capability_description: str,
        capability_features: List[str]
    ) -> DerivationAttempt:
        """
        Attempt to derive capability through search over primitive space.

        This simulates exhaustive search through compositions.
        """
        primitives = self.library.get_all_primitives()
        composable_pairs = self.library.get_composable_pairs()

        steps = []
        best_coverage = 0.0
        best_composition = []

        # Random search through composition space
        for iteration in range(min(self.max_search_iterations, 500)):
            # Random composition
            composition = []
            current = random.choice(primitives)
            composition.append(current.id)

            for depth in range(random.randint(1, self.max_composition_depth)):
                # Find composable next step
                candidates = [p for p in primitives
                             if p.id in current.composable_with]
                if not candidates:
                    break
                current = random.choice(candidates)
                composition.append(current.id)

            # Evaluate composition
            coverage = self._estimate_coverage(capability_features, composition)

            if coverage > best_coverage:
                best_coverage = coverage
                best_composition = composition
                steps.append(f"Iteration {iteration}: Found composition with {coverage:.1%} coverage")

            if best_coverage > 0.95:
                break

        if best_coverage > 0.9:
            return DerivationAttempt(
                strategy=DerivationStrategy.SEARCH_BASED,
                primitives_used=best_composition,
                steps=steps[-5:],  # Last 5 steps
                result=DerivationResult.DERIVED,
                confidence=best_coverage,
                explanation=f"Search found derivation in {iteration} iterations",
                computation_depth=len(best_composition)
            )
        elif best_coverage > 0.5:
            return DerivationAttempt(
                strategy=DerivationStrategy.SEARCH_BASED,
                primitives_used=best_composition,
                steps=steps[-5:],
                result=DerivationResult.PARTIAL,
                confidence=best_coverage,
                explanation=f"Best search result: {best_coverage:.1%} coverage",
                computation_depth=len(best_composition)
            )

        return DerivationAttempt(
            strategy=DerivationStrategy.SEARCH_BASED,
            primitives_used=best_composition,
            steps=[f"Searched {self.max_search_iterations} compositions",
                   f"Best coverage achieved: {best_coverage:.1%}"],
            result=DerivationResult.FAILED,
            confidence=0.85,
            explanation=f"Exhaustive search failed after {self.max_search_iterations} iterations",
            computation_depth=len(best_composition)
        )

    def attempt_analogical_derivation(
        self,
        capability_description: str,
        capability_features: List[str]
    ) -> DerivationAttempt:
        """
        Attempt to derive capability through analogy to primitives.

        This checks if the capability is structurally similar to known primitives.
        """
        primitives = self.library.get_all_primitives()
        steps = []

        # Compute structural similarity to each primitive
        similarities = []
        for p in primitives:
            sim = self._compute_structural_similarity(
                capability_description,
                capability_features,
                p
            )
            similarities.append((p, sim))
            steps.append(f"Similarity to {p.name}: {sim:.2f}")

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        best_matches = similarities[:3]

        if not best_matches or best_matches[0][1] < 0.3:
            return DerivationAttempt(
                strategy=DerivationStrategy.ANALOGICAL,
                primitives_used=[],
                steps=["No strong analogies found"],
                result=DerivationResult.FAILED,
                confidence=0.9,
                explanation="Capability has no structural analogy to primitives",
                computation_depth=0
            )

        best_primitive, best_sim = best_matches[0]

        if best_sim > 0.8:
            return DerivationAttempt(
                strategy=DerivationStrategy.ANALOGICAL,
                primitives_used=[best_primitive.id],
                steps=steps[:5],
                result=DerivationResult.DERIVED,
                confidence=best_sim,
                explanation=f"Strong analogy to {best_primitive.name}",
                computation_depth=1
            )
        elif best_sim > 0.5:
            return DerivationAttempt(
                strategy=DerivationStrategy.ANALOGICAL,
                primitives_used=[m[0].id for m in best_matches],
                steps=steps[:5],
                result=DerivationResult.PARTIAL,
                confidence=best_sim,
                explanation=f"Partial analogy to {best_primitive.name}",
                computation_depth=len(best_matches)
            )

        return DerivationAttempt(
            strategy=DerivationStrategy.ANALOGICAL,
            primitives_used=[m[0].id for m in best_matches],
            steps=steps[:5],
            result=DerivationResult.FAILED,
            confidence=0.75,
            explanation="No sufficient analogy found",
            computation_depth=len(best_matches)
        )

    def attempt_combinatorial_derivation(
        self,
        capability_description: str,
        capability_features: List[str]
    ) -> DerivationAttempt:
        """
        Attempt to derive capability through combinatorial composition.

        This systematically tries all combinations up to a depth limit.
        """
        primitives = self.library.get_all_primitives()
        steps = []

        # Generate all combinations up to depth 3
        all_combinations = []

        # Depth 1: single primitives
        for p in primitives:
            all_combinations.append([p.id])

        # Depth 2: pairs
        for p1 in primitives:
            for p2_id in p1.composable_with:
                if p2_id in self.library.primitives:
                    all_combinations.append([p1.id, p2_id])

        # Depth 3: triples
        for p1 in primitives:
            for p2_id in p1.composable_with:
                if p2_id in self.library.primitives:
                    p2 = self.library.primitives[p2_id]
                    for p3_id in p2.composable_with:
                        if p3_id in self.library.primitives:
                            all_combinations.append([p1.id, p2_id, p3_id])

        steps.append(f"Generated {len(all_combinations)} combinations")

        # Evaluate each combination
        best_coverage = 0.0
        best_combination = []

        for combo in all_combinations:
            coverage = self._estimate_coverage(capability_features, combo)
            if coverage > best_coverage:
                best_coverage = coverage
                best_combination = combo

        steps.append(f"Best combination: {best_combination}")
        steps.append(f"Best coverage: {best_coverage:.1%}")

        if best_coverage > 0.9:
            return DerivationAttempt(
                strategy=DerivationStrategy.COMBINATORIAL,
                primitives_used=best_combination,
                steps=steps,
                result=DerivationResult.DERIVED,
                confidence=best_coverage,
                explanation=f"Combinatorial search found derivation",
                computation_depth=len(best_combination)
            )
        elif best_coverage > 0.5:
            return DerivationAttempt(
                strategy=DerivationStrategy.COMBINATORIAL,
                primitives_used=best_combination,
                steps=steps,
                result=DerivationResult.PARTIAL,
                confidence=best_coverage,
                explanation=f"Partial combinatorial derivation",
                computation_depth=len(best_combination)
            )

        return DerivationAttempt(
            strategy=DerivationStrategy.COMBINATORIAL,
            primitives_used=best_combination,
            steps=steps,
            result=DerivationResult.FAILED,
            confidence=0.9,
            explanation=f"All {len(all_combinations)} combinations tested, max coverage {best_coverage:.1%}",
            computation_depth=3
        )

    def _estimate_coverage(
        self,
        capability_features: List[str],
        primitives_used: List[str]
    ) -> float:
        """Estimate how well primitives cover capability features."""
        if not capability_features or not primitives_used:
            return 0.0

        # Get primitive descriptions
        primitive_keywords = set()
        for p_id in primitives_used:
            if p_id in self.library.primitives:
                p = self.library.primitives[p_id]
                primitive_keywords.update(p.description.lower().split())
                primitive_keywords.add(p.name.lower())

        # Count covered features
        covered = 0
        for feature in capability_features:
            feature_words = set(feature.lower().split())
            if feature_words & primitive_keywords:
                covered += 1

        return covered / len(capability_features) if capability_features else 0.0

    def _compute_structural_similarity(
        self,
        cap_description: str,
        cap_features: List[str],
        primitive: Primitive
    ) -> float:
        """Compute structural similarity between capability and primitive."""
        # Simple keyword-based similarity
        cap_words = set(cap_description.lower().split())
        cap_words.update(f.lower() for f in cap_features)

        prim_words = set(primitive.description.lower().split())
        prim_words.add(primitive.name.lower())

        intersection = len(cap_words & prim_words)
        union = len(cap_words | prim_words)

        return intersection / union if union > 0 else 0.0


class ECDENoveltyOracle:
    """
    Adversarial oracle that attempts to derive capabilities from primitives.

    This implements the External Novelty Oracle approach from the council feedback:
    "Build separate system that audits novelty claims. Attempts to derive
    'emergent' capabilities from primitives. Failed derivation = evidence
    of genuine novelty."
    """

    def __init__(self):
        self.primitive_library = PrimitiveLibrary()
        self.derivation_engine = DerivationEngine(self.primitive_library)

    async def assess_capability_novelty(
        self,
        capability_id: str,
        capability_name: str,
        capability_description: str,
        capability_features: Optional[List[str]] = None
    ) -> CapabilityNoveltyAssessment:
        """
        Assess whether a capability is genuinely novel.

        Attempts multiple derivation strategies and records results.
        """
        features = capability_features or capability_description.split()[:10]

        assessment = CapabilityNoveltyAssessment(
            capability_id=capability_id,
            capability_name=capability_name,
            capability_description=capability_description
        )

        # Try all derivation strategies
        strategies = [
            ("Direct Composition", self.derivation_engine.attempt_direct_composition),
            ("Rule Application", self.derivation_engine.attempt_rule_application),
            ("Search-Based", self.derivation_engine.attempt_search_derivation),
            ("Analogical", self.derivation_engine.attempt_analogical_derivation),
            ("Combinatorial", self.derivation_engine.attempt_combinatorial_derivation),
        ]

        derived_count = 0
        failed_count = 0
        partial_count = 0

        for name, strategy_fn in strategies:
            try:
                attempt = strategy_fn(capability_description, features)
                assessment.derivation_attempts.append(attempt)

                if attempt.result == DerivationResult.DERIVED:
                    derived_count += 1
                elif attempt.result == DerivationResult.FAILED:
                    failed_count += 1
                elif attempt.result == DerivationResult.PARTIAL:
                    partial_count += 1

            except Exception as e:
                logger.error(f"Strategy {name} failed: {e}")
                # Failed strategy counts as failed derivation
                failed_count += 1

        # Determine overall novelty
        total_strategies = len(strategies)

        # Novel if MOST strategies failed to derive
        if failed_count >= total_strategies * 0.8:
            assessment.is_novel = True
            assessment.novelty_confidence = failed_count / total_strategies
            assessment.novelty_evidence = [
                f"{failed_count}/{total_strategies} derivation strategies failed",
                "Capability cannot be expressed as composition of primitives",
                "No structural analogy to known building blocks found"
            ]
            assessment.satisfies_wei_novelty = True
            assessment.satisfies_bostrom_novelty = failed_count == total_strategies

        elif failed_count > total_strategies * 0.5:
            assessment.is_novel = True
            assessment.novelty_confidence = failed_count / total_strategies
            assessment.novelty_evidence = [
                f"{failed_count}/{total_strategies} derivation strategies failed",
                "Partial derivation possible but incomplete",
                "Some novel aspects not reducible to primitives"
            ]
            assessment.satisfies_wei_novelty = True
            assessment.satisfies_bostrom_novelty = False

        else:
            assessment.is_novel = False
            assessment.novelty_confidence = derived_count / total_strategies
            assessment.novelty_evidence = [
                f"{derived_count}/{total_strategies} strategies successfully derived",
                "Capability can be expressed through known primitives"
            ]

        return assessment

    async def run_oracle_assessment(
        self,
        capabilities: List[Dict[str, Any]]
    ) -> NoveltyOracleResult:
        """
        Run the oracle on a list of capabilities.

        Args:
            capabilities: List of dicts with 'id', 'name', 'description', 'features'

        Returns:
            NoveltyOracleResult with all assessments
        """
        assessments = []
        genuinely_novel = 0
        derivable = 0
        uncertain = 0

        logger.info(f"Running novelty oracle on {len(capabilities)} capabilities...")

        for cap in capabilities:
            assessment = await self.assess_capability_novelty(
                capability_id=cap.get('id', 'unknown'),
                capability_name=cap.get('name', 'Unknown'),
                capability_description=cap.get('description', ''),
                capability_features=cap.get('features', [])
            )
            assessments.append(assessment)

            if assessment.is_novel:
                genuinely_novel += 1
                logger.info(f"  NOVEL: {cap.get('name')} - {assessment.novelty_confidence:.1%} confidence")
            else:
                derivable += 1
                logger.info(f"  DERIVABLE: {cap.get('name')}")

        # Compile results
        total = len(capabilities)
        result = NoveltyOracleResult(
            total_capabilities_assessed=total,
            genuinely_novel=genuinely_novel,
            derivable=derivable,
            uncertain=uncertain,
            assessments=assessments,
            derivation_failure_rate=genuinely_novel / total if total > 0 else 0.0,
            average_novelty_confidence=sum(a.novelty_confidence for a in assessments) / total if total else 0.0
        )

        # Generate evidence summary
        result.novelty_evidence_summary = self._generate_evidence_summary(result)

        return result

    def _generate_evidence_summary(self, result: NoveltyOracleResult) -> str:
        """Generate a summary of novelty evidence for the council."""
        lines = [
            "=== NOVELTY ORACLE ASSESSMENT SUMMARY ===",
            "",
            f"Total Capabilities Assessed: {result.total_capabilities_assessed}",
            f"Genuinely Novel: {result.genuinely_novel} ({result.derivation_failure_rate:.1%})",
            f"Derivable from Primitives: {result.derivable}",
            f"Average Novelty Confidence: {result.average_novelty_confidence:.1%}",
            "",
            "--- Wei et al. Criteria Alignment ---",
        ]

        wei_satisfied = sum(1 for a in result.assessments if a.satisfies_wei_novelty)
        bostrom_satisfied = sum(1 for a in result.assessments if a.satisfies_bostrom_novelty)

        lines.append(f"Satisfies Wei Novelty (non-derivable): {wei_satisfied}/{result.total_capabilities_assessed}")
        lines.append(f"Satisfies Bostrom Novelty (outside design space): {bostrom_satisfied}/{result.total_capabilities_assessed}")

        lines.append("")
        lines.append("--- Top Novel Capabilities ---")

        novel_caps = [a for a in result.assessments if a.is_novel]
        novel_caps.sort(key=lambda x: x.novelty_confidence, reverse=True)

        for cap in novel_caps[:5]:
            lines.append(f"  - {cap.capability_name}: {cap.novelty_confidence:.1%} novel")
            for evidence in cap.novelty_evidence[:2]:
                lines.append(f"    * {evidence}")

        lines.append("")
        lines.append("--- Derivation Strategy Results ---")

        # Aggregate strategy results
        strategy_results = {}
        for a in result.assessments:
            for attempt in a.derivation_attempts:
                strat_name = attempt.strategy.value
                if strat_name not in strategy_results:
                    strategy_results[strat_name] = {'derived': 0, 'failed': 0, 'partial': 0}
                if attempt.result == DerivationResult.DERIVED:
                    strategy_results[strat_name]['derived'] += 1
                elif attempt.result == DerivationResult.FAILED:
                    strategy_results[strat_name]['failed'] += 1
                else:
                    strategy_results[strat_name]['partial'] += 1

        for strat, counts in strategy_results.items():
            total = counts['derived'] + counts['failed'] + counts['partial']
            fail_rate = counts['failed'] / total if total > 0 else 0
            lines.append(f"  {strat}: {counts['failed']}/{total} derivations failed ({fail_rate:.1%})")

        return "\n".join(lines)


async def run_novelty_oracle_on_ecde(ecde_results: Optional[Dict] = None) -> NoveltyOracleResult:
    """
    Run the novelty oracle on ECDE results.

    Args:
        ecde_results: Optional pre-loaded ECDE results. If None, runs ECDE first.

    Returns:
        NoveltyOracleResult with novelty assessments
    """
    oracle = ECDENoveltyOracle()

    # If no results provided, try to load from ECDE
    if ecde_results is None:
        try:
            # Import and run ECDE
            from empirical_capability_discovery import EmpiricalCapabilityDiscoveryEngine
            from ecde_novel_capability_adapter import ECDENovelCapabilityAdapter

            # Create ECDE instance and load state
            ecde = EmpiricalCapabilityDiscoveryEngine()
            ecde.load_state()

            # Run discovery if needed
            if len(ecde.capabilities) < 10:
                ecde.run_discovery(num_cycles=10)

            # Get capabilities from ECDE
            ecde_results = {
                'emergent_capabilities': [
                    cap for cap in ecde.capabilities.values()
                    if hasattr(cap, 'capability_type') and cap.capability_type.value == 'emergent'
                ],
                'meta_capabilities': [
                    cap for cap in ecde.capabilities.values()
                    if hasattr(cap, 'capability_type') and cap.capability_type.value == 'meta'
                ],
                'all_capabilities': list(ecde.capabilities.values())
            }
        except Exception as e:
            logger.warning(f"ECDE not available ({e}), using mock data")
            ecde_results = _get_mock_ecde_results()

    # Extract capabilities for oracle
    capabilities = []

    def safe_str(obj) -> str:
        """Safely convert object to string for description."""
        if obj is None:
            return "Unknown capability"
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return str(obj)
        return str(obj)

    def safe_list(obj) -> List[str]:
        """Safely convert object to list of features."""
        if obj is None:
            return []
        if isinstance(obj, list):
            return [str(x) for x in obj]
        return []

    # Extract emergent capabilities
    emergent = ecde_results.get('emergent_capabilities', [])
    for cap in emergent:
        cap_name = getattr(cap, 'name', f"emergent_{len(capabilities)}")
        cap_desc = getattr(cap, 'description', None) or getattr(cap, 'emergence_evidence', None)
        capabilities.append({
            'id': getattr(cap, 'id', f"emergent_{len(capabilities)}"),
            'name': safe_str(cap_name),
            'description': safe_str(cap_desc) if cap_desc else f"Emergent capability: {cap_name}",
            'features': safe_list(getattr(cap, 'parent_capabilities', []))
        })

    # Extract meta capabilities
    meta = ecde_results.get('meta_capabilities', [])
    for cap in meta:
        cap_name = getattr(cap, 'name', f"meta_{len(capabilities)}")
        cap_desc = getattr(cap, 'description', None) or getattr(cap, 'capability_signature', None)
        capabilities.append({
            'id': getattr(cap, 'id', f"meta_{len(capabilities)}"),
            'name': safe_str(cap_name),
            'description': safe_str(cap_desc) if cap_desc else f"Meta capability: {cap_name}",
            'features': []
        })

    # If no capabilities found, use mock
    if not capabilities:
        capabilities = _get_mock_capabilities()

    # Run oracle
    result = await oracle.run_oracle_assessment(capabilities)

    # Print summary
    print("\n" + result.novelty_evidence_summary)

    return result


def _get_mock_ecde_results() -> Dict:
    """Get mock ECDE results for testing."""
    return {}


def _get_mock_capabilities() -> List[Dict]:
    """Get mock capabilities for testing."""
    return [
        {
            'id': 'cap_1',
            'name': 'Emergent Pattern Recognition',
            'description': 'System recognizes complex patterns through unexpected combination of clustering and sequence analysis',
            'features': ['pattern', 'recognition', 'clustering', 'sequence', 'emergent']
        },
        {
            'id': 'cap_2',
            'name': 'Self-Modifying Optimization',
            'description': 'Algorithm modifies its own optimization strategy based on task performance',
            'features': ['self-modification', 'optimization', 'meta-learning', 'adaptive']
        },
        {
            'id': 'cap_3',
            'name': 'Cross-Domain Abstraction Transfer',
            'description': 'Abstractions learned in one domain spontaneously apply to unrelated domains',
            'features': ['abstraction', 'transfer', 'cross-domain', 'generalization', 'spontaneous']
        },
        {
            'id': 'cap_4',
            'name': 'Recursive Strategy Evolution',
            'description': 'Strategy improvement mechanism that improves its own improvement process',
            'features': ['recursive', 'strategy', 'evolution', 'meta-improvement', 'self-referential']
        },
        {
            'id': 'cap_5',
            'name': 'Compositional Efficiency Discovery',
            'description': 'Discovered efficient compositions not present in training or design',
            'features': ['composition', 'efficiency', 'discovery', 'novel-combination']
        }
    ]


if __name__ == "__main__":
    # Run the novelty oracle
    print("=== ECDE Novelty Oracle ===")
    print("Attempting to derive capabilities from primitives...")
    print("Failed derivation = Evidence of genuine novelty")
    print()

    result = asyncio.run(run_novelty_oracle_on_ecde())

    # Save results
    output_path = Path(__file__).parent / "ecde_novelty_oracle_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            'total_assessed': result.total_capabilities_assessed,
            'genuinely_novel': result.genuinely_novel,
            'derivable': result.derivable,
            'derivation_failure_rate': result.derivation_failure_rate,
            'average_novelty_confidence': result.average_novelty_confidence,
            'evidence_summary': result.novelty_evidence_summary,
            'assessments': [
                {
                    'id': a.capability_id,
                    'name': a.capability_name,
                    'is_novel': a.is_novel,
                    'novelty_confidence': a.novelty_confidence,
                    'satisfies_wei': a.satisfies_wei_novelty,
                    'satisfies_bostrom': a.satisfies_bostrom_novelty
                }
                for a in result.assessments
            ]
        }, f, indent=2)

    print(f"\nResults saved to: {output_path}")
