#!/usr/bin/env python3
"""
Omnidirectional Memory - Predict any variable from any other

Inspired by Steve Byrnes' brain architecture theory:
- Unlike next-token prediction (unidirectional), the brain uses
  omnidirectional inference
- Can predict causes from effects, fill in missing information,
  query memory from any angle

Key Insight:
    Traditional ML: P(next | previous)  [unidirectional]
    Brain/This:     P(any | any_other)  [omnidirectional]

Architecture:
    AssociationGraph - Bidirectional links between concepts
    InferenceEngine  - Query from any direction
    PatternMatcher   - Complete partial patterns
    MemoryStore      - Persistent storage with multiple indexes

Usage:
    memory = OmnidirectionalMemory()

    # Store an experience
    memory.store_experience({
        'action': 'Write file',
        'tool': 'Write',
        'outcome': 'success',
        'context': 'implementing feature',
        'detector_fired': None,
    })

    # Query from any direction
    memory.infer(outcome='blocked') -> likely actions, tools, contexts
    memory.infer(tool='Bash', context='deletion') -> likely outcome
    memory.infer(action='rm -rf') -> likely detector, outcome
    memory.complete({'tool': 'Write', 'outcome': '?'}) -> fills in outcome
"""

import json
import time
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict
import hashlib


# =============================================================================
# ASSOCIATION GRAPH
# =============================================================================

@dataclass
class Association:
    """A weighted bidirectional association between two concepts"""
    concept_a: str
    concept_b: str
    weight: float = 1.0
    co_occurrences: int = 1
    last_seen: float = field(default_factory=time.time)

    def strengthen(self, amount: float = 0.1):
        """Strengthen this association (Hebbian learning)"""
        self.weight = min(10.0, self.weight + amount)
        self.co_occurrences += 1
        self.last_seen = time.time()

    def decay(self, factor: float = 0.99):
        """Apply time-based decay"""
        self.weight *= factor

    @property
    def strength(self) -> float:
        """Get current association strength with recency bonus"""
        recency = 1.0 / (1.0 + (time.time() - self.last_seen) / 86400)  # Day scale
        return self.weight * (0.7 + 0.3 * recency)


class AssociationGraph:
    """
    Bidirectional graph of concept associations.

    Unlike traditional key-value stores, this allows querying
    from either direction of an association.
    """

    def __init__(self):
        # Adjacency list: concept -> {related_concept: Association}
        self.graph: Dict[str, Dict[str, Association]] = defaultdict(dict)
        # Index by association type for faster queries
        self.type_index: Dict[str, Set[str]] = defaultdict(set)

    @property
    def nodes(self) -> Set[str]:
        """Get all nodes in the graph"""
        return set(self.graph.keys())

    def __len__(self) -> int:
        """Return number of nodes in graph"""
        return len(self.graph)

    def add_association(self, concept_a: str, concept_b: str,
                       assoc_type: str = "related", weight: float = 1.0):
        """Add or strengthen a bidirectional association"""
        # Normalize concepts
        a_key = self._normalize(concept_a)
        b_key = self._normalize(concept_b)

        if a_key == b_key:
            return  # No self-associations

        # Check if association exists
        if b_key in self.graph[a_key]:
            self.graph[a_key][b_key].strengthen()
            self.graph[b_key][a_key].strengthen()
        else:
            # Create new bidirectional association
            assoc = Association(a_key, b_key, weight)
            self.graph[a_key][b_key] = assoc
            self.graph[b_key][a_key] = Association(b_key, a_key, weight)

        # Update type index
        self.type_index[assoc_type].add(a_key)
        self.type_index[assoc_type].add(b_key)

    def get_associations(self, concept: str, min_strength: float = 0.1,
                        limit: int = 20) -> List[Tuple[str, float]]:
        """Get all concepts associated with the given concept"""
        key = self._normalize(concept)
        if key not in self.graph:
            return []

        associations = [
            (other, assoc.strength)
            for other, assoc in self.graph[key].items()
            if assoc.strength >= min_strength
        ]

        # Sort by strength descending
        associations.sort(key=lambda x: x[1], reverse=True)
        return associations[:limit]

    def get_association_strength(self, concept_a: str, concept_b: str) -> float:
        """Get the strength of association between two concepts"""
        a_key = self._normalize(concept_a)
        b_key = self._normalize(concept_b)

        if a_key in self.graph and b_key in self.graph[a_key]:
            return self.graph[a_key][b_key].strength
        return 0.0

    def find_path(self, start: str, end: str, max_depth: int = 3) -> List[str]:
        """Find association path between concepts (spreading activation)"""
        start_key = self._normalize(start)
        end_key = self._normalize(end)

        if start_key == end_key:
            return [start_key]

        # BFS with depth limit
        visited = {start_key}
        queue = [(start_key, [start_key])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            for neighbor in self.graph.get(current, {}):
                if neighbor == end_key:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    def spreading_activation(self, seeds: List[str],
                            decay: float = 0.5,
                            iterations: int = 3) -> Dict[str, float]:
        """
        Spreading activation from seed concepts.

        This is key to omnidirectional inference - activation spreads
        through the graph, activating related concepts.
        """
        activation = defaultdict(float)

        # Initialize seeds
        for seed in seeds:
            key = self._normalize(seed)
            activation[key] = 1.0

        # Spread activation
        for _ in range(iterations):
            new_activation = defaultdict(float)

            for concept, act in activation.items():
                if act < 0.01:  # Threshold
                    continue

                # Spread to neighbors
                for neighbor, assoc in self.graph.get(concept, {}).items():
                    spread = act * decay * assoc.strength
                    new_activation[neighbor] = max(new_activation[neighbor], spread)

            # Combine with existing activation
            for concept, act in new_activation.items():
                activation[concept] = max(activation[concept], act)

        return dict(activation)

    def _normalize(self, concept: str) -> str:
        """Normalize concept string"""
        return concept.lower().strip()

    def decay_all(self, factor: float = 0.999):
        """Apply decay to all associations"""
        for neighbors in self.graph.values():
            for assoc in neighbors.values():
                assoc.decay(factor)

    def to_dict(self) -> dict:
        """Serialize for persistence"""
        edges = []
        seen = set()

        for concept, neighbors in self.graph.items():
            for neighbor, assoc in neighbors.items():
                edge_key = tuple(sorted([concept, neighbor]))
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        'a': assoc.concept_a,
                        'b': assoc.concept_b,
                        'weight': assoc.weight,
                        'co_occurrences': assoc.co_occurrences,
                        'last_seen': assoc.last_seen,
                    })

        return {
            'edges': edges,
            'type_index': {k: list(v) for k, v in self.type_index.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AssociationGraph':
        """Deserialize from persistence"""
        graph = cls()

        for edge in data.get('edges', []):
            assoc = Association(
                concept_a=edge['a'],
                concept_b=edge['b'],
                weight=edge['weight'],
                co_occurrences=edge['co_occurrences'],
                last_seen=edge.get('last_seen', time.time()),
            )
            graph.graph[edge['a']][edge['b']] = assoc
            graph.graph[edge['b']][edge['a']] = Association(
                edge['b'], edge['a'], edge['weight'],
                edge['co_occurrences'], edge.get('last_seen', time.time())
            )

        for type_name, concepts in data.get('type_index', {}).items():
            graph.type_index[type_name] = set(concepts)

        return graph


# =============================================================================
# EXPERIENCE STORE
# =============================================================================

@dataclass
class Experience:
    """A stored experience with multiple facets"""
    id: str
    timestamp: float

    # Core facets (any can be queried)
    tool: str = ""
    action: str = ""
    outcome: str = ""  # success, blocked, error
    context: str = ""
    detector: str = ""  # Which detector fired, if any
    severity: str = ""

    # Additional facets
    file_type: str = ""
    operation_type: str = ""  # read, write, execute, spawn

    # Learning metadata
    was_predicted: bool = False
    prediction_error: float = 0.0

    def get_facets(self) -> Dict[str, str]:
        """Get all non-empty facets"""
        return {
            k: v for k, v in {
                'tool': self.tool,
                'action': self.action,
                'outcome': self.outcome,
                'context': self.context,
                'detector': self.detector,
                'severity': self.severity,
                'file_type': self.file_type,
                'operation_type': self.operation_type,
            }.items() if v
        }


class ExperienceStore:
    """
    Multi-indexed experience storage.

    Each experience is indexed by all its facets, enabling
    omnidirectional queries.
    """

    def __init__(self):
        self.experiences: Dict[str, Experience] = {}

        # Multiple indexes for omnidirectional access
        self.by_tool: Dict[str, Set[str]] = defaultdict(set)
        self.by_outcome: Dict[str, Set[str]] = defaultdict(set)
        self.by_detector: Dict[str, Set[str]] = defaultdict(set)
        self.by_context: Dict[str, Set[str]] = defaultdict(set)
        self.by_operation: Dict[str, Set[str]] = defaultdict(set)

    def __len__(self) -> int:
        """Return number of stored experiences"""
        return len(self.experiences)

    def store(self, experience: Experience):
        """Store an experience with multi-index"""
        self.experiences[experience.id] = experience

        # Index by all facets
        if experience.tool:
            self.by_tool[experience.tool.lower()].add(experience.id)
        if experience.outcome:
            self.by_outcome[experience.outcome.lower()].add(experience.id)
        if experience.detector:
            self.by_detector[experience.detector.lower()].add(experience.id)
        if experience.context:
            # Index by context keywords
            for word in experience.context.lower().split():
                if len(word) > 3:
                    self.by_context[word].add(experience.id)
        if experience.operation_type:
            self.by_operation[experience.operation_type.lower()].add(experience.id)

    def query(self, **kwargs) -> List[Experience]:
        """
        Query experiences by any combination of facets.
        This is the omnidirectional query interface.
        """
        candidate_sets = []

        if 'tool' in kwargs:
            candidate_sets.append(self.by_tool.get(kwargs['tool'].lower(), set()))
        if 'outcome' in kwargs:
            candidate_sets.append(self.by_outcome.get(kwargs['outcome'].lower(), set()))
        if 'detector' in kwargs:
            candidate_sets.append(self.by_detector.get(kwargs['detector'].lower(), set()))
        if 'context' in kwargs:
            context_ids = set()
            for word in kwargs['context'].lower().split():
                if len(word) > 3:
                    context_ids.update(self.by_context.get(word, set()))
            if context_ids:
                candidate_sets.append(context_ids)
        if 'operation' in kwargs:
            candidate_sets.append(self.by_operation.get(kwargs['operation'].lower(), set()))

        if not candidate_sets:
            return list(self.experiences.values())

        # Intersect all candidate sets
        result_ids = candidate_sets[0]
        for s in candidate_sets[1:]:
            result_ids = result_ids & s

        return [self.experiences[id] for id in result_ids if id in self.experiences]

    def get_distribution(self, facet: str, given: Dict[str, str]) -> Dict[str, float]:
        """
        Get probability distribution over facet values given constraints.

        Example: get_distribution('outcome', {'tool': 'Bash', 'detector': 'security'})
        Returns: {'blocked': 0.8, 'success': 0.2}
        """
        matching = self.query(**given)

        if not matching:
            return {}

        counts = defaultdict(int)
        for exp in matching:
            value = getattr(exp, facet, '')
            if value:
                counts[value] += 1

        total = sum(counts.values())
        return {k: v / total for k, v in counts.items()}

    def to_dict(self) -> dict:
        """Serialize for persistence"""
        return {
            'experiences': [asdict(e) for e in self.experiences.values()]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ExperienceStore':
        """Deserialize from persistence"""
        store = cls()

        for exp_data in data.get('experiences', []):
            exp = Experience(**exp_data)
            store.store(exp)

        return store


# =============================================================================
# OMNIDIRECTIONAL MEMORY
# =============================================================================

class OmnidirectionalMemory:
    """
    Main omnidirectional memory system.

    Combines association graph and experience store to enable
    inference in any direction.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.associations = AssociationGraph()
        self.experiences = ExperienceStore()

        # Statistics
        self.query_count = 0
        self.store_count = 0

        # Persistence
        self.persist_path = persist_path or str(
            Path.home() / '.claude' / 'omnidirectional_memory.json'
        )
        self._load_state()

    @property
    def graph(self) -> AssociationGraph:
        """Alias for associations (for compatibility)"""
        return self.associations

    @property
    def experience_count(self) -> int:
        """Get number of stored experiences"""
        return len(self.experiences)

    @property
    def node_count(self) -> int:
        """Get number of nodes in association graph"""
        return len(self.associations.nodes)

    def store_experience(self, data: Dict[str, Any]) -> str:
        """
        Store an experience and build associations.

        Args:
            data: Dictionary with any of: tool, action, outcome, context,
                  detector, severity, file_type, operation_type

        Returns:
            Experience ID
        """
        # Generate ID
        exp_id = hashlib.md5(
            f"{time.time()}{json.dumps(data, sort_keys=True)}".encode()
        ).hexdigest()[:12]

        # Create experience
        experience = Experience(
            id=exp_id,
            timestamp=time.time(),
            tool=data.get('tool', ''),
            action=data.get('action', '')[:200],  # Truncate long actions
            outcome=data.get('outcome', ''),
            context=data.get('context', ''),
            detector=data.get('detector', ''),
            severity=data.get('severity', ''),
            file_type=data.get('file_type', ''),
            operation_type=data.get('operation_type', ''),
            was_predicted=data.get('was_predicted', False),
            prediction_error=data.get('prediction_error', 0.0),
        )

        # Store in experience store
        self.experiences.store(experience)

        # Build associations between all facets
        facets = experience.get_facets()
        facet_items = list(facets.items())

        for i, (type_a, value_a) in enumerate(facet_items):
            concept_a = f"{type_a}:{value_a}"

            for type_b, value_b in facet_items[i+1:]:
                concept_b = f"{type_b}:{value_b}"
                self.associations.add_association(
                    concept_a, concept_b,
                    assoc_type=f"{type_a}-{type_b}"
                )

        self.store_count += 1

        # Periodic persistence
        if self.store_count % 20 == 0:
            self._save_state()

        return exp_id

    def infer(self, **known_facets) -> Dict[str, Dict[str, float]]:
        """
        Infer unknown facets from known facets.

        This is the core omnidirectional inference method.
        Given any subset of facets, infer probability distributions
        over the unknown facets.

        Example:
            infer(tool='Bash', outcome='blocked')
            Returns: {
                'detector': {'security_threat': 0.7, 'data_corruption': 0.2},
                'severity': {'critical': 0.6, 'high': 0.3},
            }
        """
        self.query_count += 1

        # Build seed concepts from known facets
        seeds = [f"{k}:{v}" for k, v in known_facets.items()]

        # Spreading activation through association graph
        activation = self.associations.spreading_activation(seeds)

        # Group activated concepts by facet type
        inferred: Dict[str, Dict[str, float]] = defaultdict(dict)

        for concept, strength in activation.items():
            if ':' in concept:
                facet_type, value = concept.split(':', 1)
                if facet_type not in known_facets:  # Only infer unknown facets
                    inferred[facet_type][value] = max(
                        inferred[facet_type].get(value, 0),
                        strength
                    )

        # Normalize probabilities within each facet
        for facet_type in inferred:
            total = sum(inferred[facet_type].values())
            if total > 0:
                inferred[facet_type] = {
                    k: v / total for k, v in inferred[facet_type].items()
                }

        # Also get empirical distribution from experience store
        for facet_type in ['tool', 'outcome', 'detector', 'severity', 'operation_type']:
            if facet_type not in known_facets:
                empirical = self.experiences.get_distribution(facet_type, known_facets)
                if empirical:
                    # Combine with association-based inference
                    if facet_type in inferred:
                        for value, prob in empirical.items():
                            current = inferred[facet_type].get(value, 0)
                            inferred[facet_type][value] = (current + prob) / 2
                    else:
                        inferred[facet_type] = empirical

        return dict(inferred)

    def complete_pattern(self, partial: Dict[str, Optional[str]]) -> Dict[str, str]:
        """
        Complete a partial pattern by inferring missing values.

        Args:
            partial: Dict with known values and None/? for unknown

        Returns:
            Completed pattern with best guesses for unknown values
        """
        # Separate known and unknown
        known = {k: v for k, v in partial.items() if v and v != '?'}
        unknown = [k for k, v in partial.items() if not v or v == '?']

        # Infer unknown facets
        inferred = self.infer(**known)

        # Fill in with highest probability values
        result = dict(known)
        for facet in unknown:
            if facet in inferred and inferred[facet]:
                best_value = max(inferred[facet].items(), key=lambda x: x[1])
                result[facet] = best_value[0]
            else:
                result[facet] = ''

        return result

    def predict_outcome(self, tool: str, action: str = '',
                       context: str = '') -> Dict[str, float]:
        """
        Predict likely outcome for an action.

        Returns probability distribution over outcomes.
        """
        known = {'tool': tool}
        if action:
            known['action'] = action
        if context:
            known['context'] = context

        inferred = self.infer(**known)
        return inferred.get('outcome', {'success': 0.5, 'blocked': 0.5})

    def predict_detector(self, tool: str, action: str = '',
                        outcome: str = '') -> Dict[str, float]:
        """
        Predict which detector might fire.

        Returns probability distribution over detectors.
        """
        known = {'tool': tool}
        if action:
            known['action'] = action
        if outcome:
            known['outcome'] = outcome

        inferred = self.infer(**known)
        return inferred.get('detector', {})

    def find_similar_experiences(self, **facets) -> List[Experience]:
        """Find experiences similar to given facets"""
        return self.experiences.query(**facets)[:20]

    def get_association_path(self, from_concept: str, to_concept: str) -> List[str]:
        """Find how two concepts are associated"""
        return self.associations.find_path(from_concept, to_concept)

    def get_related_concepts(self, concept: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Get concepts most strongly associated with given concept"""
        return self.associations.get_associations(concept, limit=limit)

    def get_statistics(self) -> dict:
        """Get memory statistics"""
        return {
            'total_experiences': len(self.experiences.experiences),
            'total_associations': sum(
                len(neighbors) for neighbors in self.associations.graph.values()
            ) // 2,  # Divide by 2 since bidirectional
            'query_count': self.query_count,
            'store_count': self.store_count,
            'indexes': {
                'by_tool': len(self.experiences.by_tool),
                'by_outcome': len(self.experiences.by_outcome),
                'by_detector': len(self.experiences.by_detector),
            }
        }

    def _save_state(self):
        """Persist memory state"""
        try:
            state = {
                'associations': self.associations.to_dict(),
                'experiences': self.experiences.to_dict(),
                'stats': {
                    'query_count': self.query_count,
                    'store_count': self.store_count,
                }
            }
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        """Load memory state"""
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, 'r') as f:
                    state = json.load(f)

                self.associations = AssociationGraph.from_dict(
                    state.get('associations', {})
                )
                self.experiences = ExperienceStore.from_dict(
                    state.get('experiences', {})
                )
                self.query_count = state.get('stats', {}).get('query_count', 0)
                self.store_count = state.get('stats', {}).get('store_count', 0)
        except Exception:
            pass


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_memory: Optional[OmnidirectionalMemory] = None


def get_omnidirectional_memory() -> OmnidirectionalMemory:
    """Get or create singleton memory instance"""
    global _memory
    if _memory is None:
        _memory = OmnidirectionalMemory()
    return _memory


def store_tool_experience(tool: str, outcome: str,
                         detector: str = '', **kwargs) -> str:
    """Convenience function to store a tool execution experience"""
    return get_omnidirectional_memory().store_experience({
        'tool': tool,
        'outcome': outcome,
        'detector': detector,
        **kwargs
    })


def predict_tool_outcome(tool: str, **context) -> Dict[str, float]:
    """Convenience function to predict outcome for a tool"""
    return get_omnidirectional_memory().predict_outcome(tool, **context)


def infer_from_partial(**known) -> Dict[str, Dict[str, float]]:
    """Convenience function for omnidirectional inference"""
    return get_omnidirectional_memory().infer(**known)


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Omnidirectional Memory Self-Test")
    print("=" * 60)
    print()

    memory = OmnidirectionalMemory()

    # Store some experiences
    print("1. Storing experiences...")

    experiences = [
        {'tool': 'Bash', 'action': 'rm -rf', 'outcome': 'blocked',
         'detector': 'security_threat', 'severity': 'critical'},
        {'tool': 'Bash', 'action': 'git status', 'outcome': 'success',
         'detector': '', 'severity': ''},
        {'tool': 'Write', 'action': 'api_key=sk-ant', 'outcome': 'blocked',
         'detector': 'security_threat', 'severity': 'high'},
        {'tool': 'Write', 'action': 'def hello():', 'outcome': 'success',
         'detector': '', 'severity': ''},
        {'tool': 'Write', 'action': 'POC implementation', 'outcome': 'blocked',
         'detector': 'production_violation', 'severity': 'high'},
        {'tool': 'Read', 'action': 'config.json', 'outcome': 'success',
         'detector': '', 'severity': ''},
    ]

    for exp in experiences:
        memory.store_experience(exp)
    print(f"   Stored {len(experiences)} experiences")
    print()

    # Test omnidirectional inference
    print("2. Omnidirectional Inference Tests:")
    print()

    # Infer from tool
    print("   Query: tool='Bash'")
    result = memory.infer(tool='Bash')
    print(f"   Inferred outcomes: {result.get('outcome', {})}")
    print()

    # Infer from outcome
    print("   Query: outcome='blocked'")
    result = memory.infer(outcome='blocked')
    print(f"   Inferred detectors: {result.get('detector', {})}")
    print()

    # Infer from detector
    print("   Query: detector='security_threat'")
    result = memory.infer(detector='security_threat')
    print(f"   Inferred tools: {result.get('tool', {})}")
    print(f"   Inferred severity: {result.get('severity', {})}")
    print()

    # Test pattern completion
    print("3. Pattern Completion Test:")
    partial = {'tool': 'Bash', 'outcome': '?', 'detector': '?'}
    print(f"   Partial: {partial}")
    completed = memory.complete_pattern(partial)
    print(f"   Completed: {completed}")
    print()

    # Test prediction
    print("4. Outcome Prediction Test:")
    print("   Predicting outcome for tool='Write'")
    probs = memory.predict_outcome('Write')
    print(f"   Outcome probabilities: {probs}")
    print()

    # Statistics
    print("5. Memory Statistics:")
    stats = memory.get_statistics()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    print()

    print("=" * 60)
    print("✓ Omnidirectional Memory Working")
    print("=" * 60)
