#!/usr/bin/env python3
"""
ACE Curator Component
Manages incremental memory updates with delta tracking
Based on: arXiv 2510.04618v1 - Agentic Context Engineering
Prevents context collapse through grow-and-refine mechanism
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class DeltaUpdate:
    """Structured delta update for memory entities"""
    entity_name: str
    add_observations: List[str]
    refine_observations: Dict[str, str]
    add_relationships: List[Dict[str, str]]
    prune_observations: List[str]
    metadata_updates: Dict[str, Any]
    timestamp: str
    delta_id: str


@dataclass
class RedundancyScore:
    """Redundancy detection result"""
    is_redundant: bool
    score: float
    similar_observations: List[str]
    recommendation: str


@dataclass
class UpdateResult:
    """Result of delta update operation"""
    success: bool
    entity_name: str
    delta_id: str
    operations_applied: int
    observations_added: int
    observations_refined: int
    relationships_added: int
    pruned: int
    version_checkpoint: Optional[str]
    latency_ms: float
    message: str


class ACECurator:
    """
    Manages incremental memory updates with delta tracking.
    Addresses: Context collapse prevention from ACE paper.
    Implements: Grow-and-refine mechanism for balanced context evolution.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Curator with configuration

        Args:
            config: Optional configuration dict with thresholds and settings
        """
        self.config = config or {
            'delta_update_mode': 'incremental',
            'redundancy_threshold': 0.85,
            'checkpoint_frequency': 10,
            'auto_pruning': False,
            'preserve_history': True
        }

        self.update_counter: Dict[str, int] = {}
        self.delta_history: List[DeltaUpdate] = []

        # Memory system integration (will be initialized when available)
        self.memory_available = False
        self._check_memory_availability()

    def _check_memory_availability(self):
        """Check if enhanced-memory-mcp is available"""
        # This will be updated to actually check MCP connection
        # For now, we assume it's available when properly integrated
        self.memory_available = True

    def apply_delta_update(self, entity_name: str, delta: Dict[str, Any]) -> UpdateResult:
        """
        Apply incremental update without full rewrite.
        Implements ACE's delta update mechanism to prevent context collapse.

        Args:
            entity_name: Name of memory entity to update
            delta: Delta structure with incremental changes:
                {
                    'add_observations': [str],          # New observations to append
                    'refine_observations': {            # Observations to enhance
                        'observation_id': 'enhancement_text'
                    },
                    'add_relationships': [dict],        # New entity connections
                    'prune_observations': [str],        # Observations to remove (if truly redundant)
                    'metadata_updates': dict            # Non-destructive metadata changes
                }

        Returns:
            UpdateResult with operation details and performance metrics
        """
        start_time = datetime.now()

        # Generate delta ID
        delta_id = self._generate_delta_id(entity_name, delta)

        # Validate delta structure
        if not self._validate_delta(delta):
            return UpdateResult(
                success=False,
                entity_name=entity_name,
                delta_id=delta_id,
                operations_applied=0,
                observations_added=0,
                observations_refined=0,
                relationships_added=0,
                pruned=0,
                version_checkpoint=None,
                latency_ms=0,
                message="Invalid delta structure"
            )

        operations = 0
        obs_added = 0
        obs_refined = 0
        rel_added = 0
        pruned = 0

        try:
            # Retrieve existing entity (simulation for now)
            existing_entity = self._get_entity(entity_name)

            if existing_entity is None:
                return UpdateResult(
                    success=False,
                    entity_name=entity_name,
                    delta_id=delta_id,
                    operations_applied=0,
                    observations_added=0,
                    observations_refined=0,
                    relationships_added=0,
                    pruned=0,
                    version_checkpoint=None,
                    latency_ms=self._calc_latency(start_time),
                    message=f"Entity '{entity_name}' not found. Create it first."
                )

            # Apply add_observations (grow mechanism)
            if delta.get('add_observations'):
                for obs in delta['add_observations']:
                    # Check redundancy before adding
                    redundancy = self.detect_redundancy(entity_name, obs)

                    if not redundancy.is_redundant:
                        self._add_observation(entity_name, obs)
                        obs_added += 1
                        operations += 1
                    else:
                        # Log skipped observation
                        self._log_skip(entity_name, obs, redundancy)

            # Apply refine_observations (refine mechanism)
            if delta.get('refine_observations'):
                for obs_id, enhancement in delta['refine_observations'].items():
                    self._refine_observation(entity_name, obs_id, enhancement)
                    obs_refined += 1
                    operations += 1

            # Apply add_relationships
            if delta.get('add_relationships'):
                for rel in delta['add_relationships']:
                    self._add_relationship(entity_name, rel)
                    rel_added += 1
                    operations += 1

            # Apply pruning (only if enabled and truly redundant)
            if delta.get('prune_observations') and self.config['auto_pruning']:
                for obs in delta['prune_observations']:
                    if self._confirm_redundant(entity_name, obs):
                        self._remove_observation(entity_name, obs)
                        pruned += 1
                        operations += 1

            # Apply metadata updates
            if delta.get('metadata_updates'):
                self._update_metadata(entity_name, delta['metadata_updates'])
                operations += 1

            # Update counter for checkpoint tracking
            if entity_name not in self.update_counter:
                self.update_counter[entity_name] = 0
            self.update_counter[entity_name] += 1

            # Check if checkpoint needed
            version_checkpoint = None
            if self.update_counter[entity_name] % self.config['checkpoint_frequency'] == 0:
                version_checkpoint = self.version_checkpoint(
                    entity_name,
                    f"ACE checkpoint after {self.update_counter[entity_name]} delta updates"
                )

            # Store delta in history
            delta_record = DeltaUpdate(
                entity_name=entity_name,
                add_observations=delta.get('add_observations', []),
                refine_observations=delta.get('refine_observations', {}),
                add_relationships=delta.get('add_relationships', []),
                prune_observations=delta.get('prune_observations', []),
                metadata_updates=delta.get('metadata_updates', {}),
                timestamp=datetime.now().isoformat(),
                delta_id=delta_id
            )
            self.delta_history.append(delta_record)

            latency = self._calc_latency(start_time)

            return UpdateResult(
                success=True,
                entity_name=entity_name,
                delta_id=delta_id,
                operations_applied=operations,
                observations_added=obs_added,
                observations_refined=obs_refined,
                relationships_added=rel_added,
                pruned=pruned,
                version_checkpoint=version_checkpoint,
                latency_ms=latency,
                message=f"Delta update applied successfully: {operations} operations in {latency:.1f}ms"
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                entity_name=entity_name,
                delta_id=delta_id,
                operations_applied=operations,
                observations_added=obs_added,
                observations_refined=obs_refined,
                relationships_added=rel_added,
                pruned=pruned,
                version_checkpoint=None,
                latency_ms=self._calc_latency(start_time),
                message=f"Error applying delta: {str(e)}"
            )

    def detect_redundancy(self, entity_name: str, new_data: str) -> RedundancyScore:
        """
        Check if new observation is redundant before adding.
        Implements ACE's "grow-and-refine" mechanism.

        Args:
            entity_name: Name of entity to check against
            new_data: New observation text to evaluate

        Returns:
            RedundancyScore with detection results
        """
        entity = self._get_entity(entity_name)

        if entity is None:
            return RedundancyScore(
                is_redundant=False,
                score=0.0,
                similar_observations=[],
                recommendation="Entity not found - new data is not redundant"
            )

        # Get existing observations
        existing_observations = entity.get('observations', [])

        if not existing_observations:
            return RedundancyScore(
                is_redundant=False,
                score=0.0,
                similar_observations=[],
                recommendation="No existing observations - add as new"
            )

        # Calculate similarity scores
        similarities = []
        for obs in existing_observations:
            similarity = self._calculate_similarity(new_data, obs)
            if similarity > 0.5:  # Only track significant similarities
                similarities.append((similarity, obs))

        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])

        # Check if highest similarity exceeds threshold
        if similarities and similarities[0][0] >= self.config['redundancy_threshold']:
            return RedundancyScore(
                is_redundant=True,
                score=similarities[0][0],
                similar_observations=[obs for _, obs in similarities[:3]],
                recommendation=f"Redundant - {similarities[0][0]:.2%} similar to existing observation"
            )
        elif similarities and similarities[0][0] >= 0.7:
            # Moderately similar - suggest refinement instead of adding
            return RedundancyScore(
                is_redundant=False,
                score=similarities[0][0],
                similar_observations=[obs for _, obs in similarities[:3]],
                recommendation=f"Moderately similar ({similarities[0][0]:.2%}) - consider refining existing observation"
            )
        else:
            return RedundancyScore(
                is_redundant=False,
                score=similarities[0][0] if similarities else 0.0,
                similar_observations=[],
                recommendation="Sufficiently unique - add as new observation"
            )

    def version_checkpoint(self, entity_name: str, message: str) -> str:
        """
        Create version checkpoint using existing memory_commit functionality.
        Implements ACE's version control for delta tracking.

        Args:
            entity_name: Name of entity to checkpoint
            message: Checkpoint message

        Returns:
            Checkpoint ID or version string
        """
        timestamp = datetime.now().isoformat()
        checkpoint_id = hashlib.md5(f"{entity_name}:{timestamp}".encode()).hexdigest()[:12]

        # This will integrate with enhanced-memory-mcp's memory_commit
        # For now, we simulate the checkpoint
        checkpoint_data = {
            'checkpoint_id': checkpoint_id,
            'entity_name': entity_name,
            'timestamp': timestamp,
            'message': message,
            'delta_count': self.update_counter.get(entity_name, 0)
        }

        self._store_checkpoint(checkpoint_data)

        return checkpoint_id

    def experimental_branch(self, entity_name: str, experiment: str) -> str:
        """
        Create experimental branch using existing memory_branch functionality.
        Allows testing updates without affecting main entity.

        Args:
            entity_name: Name of entity to branch
            experiment: Experiment description

        Returns:
            Branch ID or name
        """
        timestamp = datetime.now().isoformat()
        branch_id = f"exp_{hashlib.md5(f'{entity_name}:{experiment}:{timestamp}'.encode()).hexdigest()[:8]}"

        # This will integrate with enhanced-memory-mcp's memory_branch
        # For now, we simulate the branch
        branch_data = {
            'branch_id': branch_id,
            'entity_name': entity_name,
            'experiment': experiment,
            'timestamp': timestamp,
            'parent_version': self._get_current_version(entity_name)
        }

        self._store_branch(branch_data)

        return branch_id

    def get_delta_history(self, entity_name: Optional[str] = None, limit: int = 50) -> List[DeltaUpdate]:
        """
        Get delta update history for analysis.

        Args:
            entity_name: Optional filter by entity name
            limit: Maximum number of deltas to return

        Returns:
            List of delta updates
        """
        if entity_name:
            history = [d for d in self.delta_history if d.entity_name == entity_name]
        else:
            history = self.delta_history

        return history[-limit:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for delta updates.
        Used to validate ACE paper's latency reduction claims.

        Returns:
            Performance metrics dictionary
        """
        if not self.delta_history:
            return {
                'total_updates': 0,
                'avg_latency_ms': 0,
                'total_operations': 0,
                'entities_updated': 0
            }

        # Calculate from stored UpdateResults (would be tracked separately in production)
        return {
            'total_updates': len(self.delta_history),
            'avg_latency_ms': 0,  # Would calculate from tracked results
            'total_operations': sum(len(d.add_observations) + len(d.refine_observations) + len(d.add_relationships) for d in self.delta_history),
            'entities_updated': len(set(d.entity_name for d in self.delta_history)),
            'checkpoints_created': sum(1 for entity, count in self.update_counter.items() if count % self.config['checkpoint_frequency'] == 0),
            'redundancies_prevented': 0  # Would track from redundancy detection
        }

    # Private helper methods

    def _generate_delta_id(self, entity_name: str, delta: Dict) -> str:
        """Generate unique delta ID"""
        data = f"{entity_name}:{json.dumps(delta, sort_keys=True)}:{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _validate_delta(self, delta: Dict) -> bool:
        """Validate delta structure"""
        valid_keys = {
            'add_observations',
            'refine_observations',
            'add_relationships',
            'prune_observations',
            'metadata_updates'
        }

        # Check if at least one operation is present
        has_operation = any(key in delta for key in valid_keys)

        return has_operation

    def _get_entity(self, entity_name: str) -> Optional[Dict]:
        """
        Get entity from memory system.
        Will integrate with enhanced-memory-mcp search_nodes.
        """
        # Simulation - in production, this calls:
        # mcp__enhanced-memory-mcp__search_nodes(query=entity_name, limit=1)

        # For now, return simulated entity
        return {
            'name': entity_name,
            'entityType': 'project',
            'observations': [],
            'relationships': [],
            'metadata': {}
        }

    def _add_observation(self, entity_name: str, observation: str):
        """Add observation to entity (simulation)"""
        # In production: append to entity's observations array
        # Then call enhanced-memory-mcp update
        pass

    def _refine_observation(self, entity_name: str, obs_id: str, enhancement: str):
        """Refine existing observation (simulation)"""
        # In production: locate observation by ID and append enhancement
        # Format: "Original observation | Enhancement: {enhancement}"
        pass

    def _add_relationship(self, entity_name: str, relationship: Dict):
        """Add relationship to entity (simulation)"""
        # In production: append to entity's relationships array
        pass

    def _remove_observation(self, entity_name: str, observation: str):
        """Remove observation from entity (simulation)"""
        # In production: remove from observations array
        # Only used when truly redundant
        pass

    def _update_metadata(self, entity_name: str, metadata: Dict):
        """Update entity metadata (simulation)"""
        # In production: merge with existing metadata
        pass

    def _confirm_redundant(self, entity_name: str, observation: str) -> bool:
        """Confirm observation is truly redundant"""
        redundancy = self.detect_redundancy(entity_name, observation)
        return redundancy.is_redundant and redundancy.score >= 0.95

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity score.
        Simple implementation - could be enhanced with embeddings.
        """
        # Convert to lowercase
        t1 = text1.lower()
        t2 = text2.lower()

        # Exact match
        if t1 == t2:
            return 1.0

        # Token overlap
        tokens1 = set(t1.split())
        tokens2 = set(t2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        jaccard = len(intersection) / len(union)

        # Substring check
        substring_bonus = 0.0
        if t1 in t2 or t2 in t1:
            substring_bonus = 0.2

        return min(1.0, jaccard + substring_bonus)

    def _log_skip(self, entity_name: str, observation: str, redundancy: RedundancyScore):
        """Log skipped observation for analysis"""
        # In production: log to monitoring system
        pass

    def _calc_latency(self, start_time: datetime) -> float:
        """Calculate latency in milliseconds"""
        delta = datetime.now() - start_time
        return delta.total_seconds() * 1000

    def _store_checkpoint(self, checkpoint_data: Dict):
        """Store checkpoint data (simulation)"""
        # In production: persist checkpoint to disk or database
        checkpoint_file = Path('/tmp/ace_checkpoints.json')

        checkpoints = []
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                checkpoints = json.load(f)

        checkpoints.append(checkpoint_data)

        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoints, f, indent=2)

    def _store_branch(self, branch_data: Dict):
        """Store branch data (simulation)"""
        # In production: persist branch to disk or database
        branch_file = Path('/tmp/ace_branches.json')

        branches = []
        if branch_file.exists():
            with open(branch_file, 'r') as f:
                branches = json.load(f)

        branches.append(branch_data)

        with open(branch_file, 'w') as f:
            json.dump(branches, f, indent=2)

    def _get_current_version(self, entity_name: str) -> str:
        """Get current version of entity"""
        return f"v{self.update_counter.get(entity_name, 0)}"

    def export_metrics_json(self) -> str:
        """Export performance metrics as JSON"""
        metrics = self.get_performance_metrics()
        return json.dumps(metrics, indent=2)

    def export_delta_history_json(self) -> str:
        """Export delta history as JSON"""
        return json.dumps([asdict(d) for d in self.delta_history], indent=2)


if __name__ == "__main__":
    # Example usage
    curator = ACECurator()

    # Create delta update
    delta = {
        'add_observations': [
            'Implemented JWT authentication successfully',
            'Added Redis caching for session management'
        ],
        'refine_observations': {
            'obs_123': 'Enhanced with rate limiting: 100 req/min per user'
        },
        'add_relationships': [
            {'target': 'redis_infrastructure', 'type': 'depends_on'}
        ],
        'metadata_updates': {
            'complexity_score': 7,
            'last_modified': datetime.now().isoformat()
        }
    }

    # Apply delta
    result = curator.apply_delta_update('authentication_system', delta)

    print("Delta Update Result:")
    print(json.dumps(asdict(result), indent=2))

    # Check redundancy
    redundancy = curator.detect_redundancy(
        'authentication_system',
        'Implemented JWT authentication successfully'  # Same observation
    )

    print("\nRedundancy Check:")
    print(json.dumps(asdict(redundancy), indent=2))

    # Performance metrics
    metrics = curator.get_performance_metrics()
    print("\nPerformance Metrics:")
    print(json.dumps(metrics, indent=2))
