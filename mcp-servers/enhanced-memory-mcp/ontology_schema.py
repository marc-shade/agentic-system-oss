#!/usr/bin/env python3
"""
Explicit Ontology Schema for Knowledge Graph Memory
Implements formal type definitions using Pydantic for entity and relationship validation

Inspired by: "You're Doing Memory All Wrong" - Zapai
Key concept: Define explicit schemas for entities and relationships to enable
structured reasoning, validation, and semantic coherence.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


# === ENTITY TYPE DEFINITIONS ===

class EntityType(str, Enum):
    """Core entity types in the knowledge graph"""
    # System & Core
    SYSTEM_ROLE = "system_role"
    CORE_SYSTEM = "core_system"
    CONFIGURATION = "configuration"

    # Knowledge & Learning
    CONCEPT = "concept"
    PATTERN = "pattern"
    PRINCIPLE = "principle"
    FACT = "fact"
    SKILL = "skill"
    PROCEDURE = "procedure"

    # Tasks & Execution
    PROJECT = "project"
    TASK = "task"
    GOAL = "goal"
    SESSION = "session"
    WORKFLOW = "workflow"

    # Memory & Experience
    EPISODE = "episode"
    EVENT = "event"
    EXPERIENCE = "experience"
    OBSERVATION = "observation"

    # Code & Implementation
    CODE_MODULE = "code_module"
    IMPLEMENTATION = "implementation"
    OPTIMIZATION = "optimization"
    BUG_FIX = "bug_fix"

    # Research & Learning
    RESEARCH = "research"
    PAPER = "paper"
    VIDEO = "video"
    INSIGHT = "insight"

    # Relationships & Context
    CONTEXT = "context"
    DECISION = "decision"
    OUTCOME = "outcome"
    METRIC = "metric"


class RelationType(str, Enum):
    """Relationship types with semantic meaning"""
    # Hierarchical
    CONTAINS = "contains"
    PART_OF = "part_of"
    BELONGS_TO = "belongs_to"

    # Temporal
    FOLLOWS = "follows"
    PRECEDES = "precedes"
    TRIGGERED_BY = "triggered_by"
    RESULTED_IN = "resulted_in"

    # Causal
    CAUSES = "causes"
    CAUSED_BY = "caused_by"
    ENABLES = "enables"
    DEPENDS_ON = "depends_on"

    # Semantic
    RELATES_TO = "relates_to"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"

    # Learning
    LEARNED_FROM = "learned_from"
    TEACHES = "teaches"
    APPLIES_TO = "applies_to"
    VALIDATED_BY = "validated_by"

    # Operational
    USES = "uses"
    USED_BY = "used_by"
    REQUIRES = "requires"
    PROVIDES = "provides"


class MemoryTier(str, Enum):
    """4-tier memory architecture from SAFLA"""
    WORKING = "working"      # Active, volatile, high-access
    EPISODIC = "episodic"    # Time-bound experiences
    SEMANTIC = "semantic"    # Timeless concepts
    PROCEDURAL = "procedural" # Executable skills


# === PYDANTIC MODELS ===

class EntitySchema(BaseModel):
    """Base schema for all entities with validation"""
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: EntityType
    tier: MemoryTier = MemoryTier.WORKING
    observations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Temporal attributes
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # For working memory

    # Significance scoring
    significance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = Field(default=0, ge=0)

    @validator('name')
    def validate_name(cls, v):
        """Ensure name is meaningful"""
        if v.strip() == "":
            raise ValueError("Entity name cannot be empty or whitespace")
        return v.strip()

    @validator('observations')
    def validate_observations(cls, v):
        """Ensure observations are non-empty strings"""
        return [obs.strip() for obs in v if obs.strip()]


class ConceptEntity(EntitySchema):
    """Schema for conceptual knowledge (semantic memory)"""
    entity_type: Literal[EntityType.CONCEPT] = EntityType.CONCEPT
    tier: Literal[MemoryTier.SEMANTIC] = MemoryTier.SEMANTIC

    definition: str = Field(..., min_length=10)
    related_concepts: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)

    class Config:
        schema_extra = {
            "example": {
                "name": "temporal_edge_modeling",
                "entity_type": "concept",
                "tier": "semantic",
                "definition": "Recording timestamps on graph relationships to track when connections were formed",
                "related_concepts": ["knowledge_graphs", "temporal_reasoning"],
                "observations": ["Enables time-aware retrieval", "Supports causal analysis"],
                "confidence_score": 0.9
            }
        }


class EpisodeEntity(EntitySchema):
    """Schema for episodic memories (time-bound experiences)"""
    entity_type: Literal[EntityType.EPISODE] = EntityType.EPISODE
    tier: Literal[MemoryTier.EPISODIC] = MemoryTier.EPISODIC

    event_type: str = Field(..., min_length=1)
    episode_data: Dict[str, Any] = Field(default_factory=dict)
    emotional_valence: Optional[float] = Field(default=None, ge=-1.0, le=1.0)

    class Config:
        schema_extra = {
            "example": {
                "name": "optimization_success_2025_01_11",
                "entity_type": "episode",
                "tier": "episodic",
                "event_type": "optimization_success",
                "episode_data": {
                    "method": "knowledge_graph_enhancement",
                    "improvement": "40% retrieval accuracy"
                },
                "significance_score": 0.85,
                "emotional_valence": 0.8
            }
        }


class SkillEntity(EntitySchema):
    """Schema for procedural knowledge (executable skills)"""
    entity_type: Literal[EntityType.SKILL] = EntityType.SKILL
    tier: Literal[MemoryTier.PROCEDURAL] = MemoryTier.PROCEDURAL

    skill_category: str = Field(..., min_length=1)
    procedure_steps: List[str] = Field(..., min_items=1)
    preconditions: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_count: int = Field(default=0, ge=0)

    class Config:
        schema_extra = {
            "example": {
                "name": "graph_traversal_query",
                "entity_type": "skill",
                "tier": "procedural",
                "skill_category": "memory_retrieval",
                "procedure_steps": [
                    "Start from root entity",
                    "Traverse relationships bidirectionally",
                    "Collect connected context",
                    "Score by relevance"
                ],
                "success_rate": 0.87,
                "execution_count": 156
            }
        }


class RelationshipSchema(BaseModel):
    """Schema for graph relationships with temporal and causal attributes"""
    from_entity: str = Field(..., min_length=1)
    to_entity: str = Field(..., min_length=1)
    relation_type: RelationType

    # Temporal attributes (NEW - temporal edge modeling)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Strength and confidence
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # Causal attributes (NEW - causal reasoning)
    is_causal: bool = False
    causal_direction: Optional[Literal["forward", "backward"]] = None
    causal_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)

    # Bi-directional support (NEW)
    bidirectional: bool = False  # If True, automatically create reverse relationship

    @validator('causal_strength')
    def validate_causal_strength(cls, v, values):
        """Causal strength only valid if is_causal is True"""
        if v is not None and not values.get('is_causal'):
            raise ValueError("causal_strength only valid when is_causal=True")
        return v

    class Config:
        schema_extra = {
            "example": {
                "from_entity": "enhanced_memory_system",
                "to_entity": "knowledge_graph_integration",
                "relation_type": "implements",
                "created_at": "2025-01-11T10:00:00",
                "strength": 0.9,
                "is_causal": True,
                "causal_direction": "forward",
                "causal_strength": 0.85,
                "evidence": ["Video analysis showed knowledge graphs solve vector-only limitations"],
                "bidirectional": False
            }
        }


# === ONTOLOGY VALIDATION ===

class OntologyValidator:
    """Validates entities and relationships against the ontology schema"""

    @staticmethod
    def validate_entity(entity_dict: Dict[str, Any]) -> tuple[bool, Optional[EntitySchema], Optional[str]]:
        """
        Validate entity against appropriate schema

        Returns:
            (is_valid, validated_model, error_message)
        """
        try:
            entity_type = entity_dict.get('entity_type') or entity_dict.get('entityType')

            # Map to specific schema based on type
            if entity_type == EntityType.CONCEPT:
                model = ConceptEntity(**entity_dict)
            elif entity_type == EntityType.EPISODE:
                model = EpisodeEntity(**entity_dict)
            elif entity_type == EntityType.SKILL:
                model = SkillEntity(**entity_dict)
            else:
                # Use base schema for other types
                model = EntitySchema(**entity_dict)

            return True, model, None

        except Exception as e:
            return False, None, str(e)

    @staticmethod
    def validate_relationship(rel_dict: Dict[str, Any]) -> tuple[bool, Optional[RelationshipSchema], Optional[str]]:
        """
        Validate relationship against schema

        Returns:
            (is_valid, validated_model, error_message)
        """
        try:
            model = RelationshipSchema(**rel_dict)
            return True, model, None
        except Exception as e:
            return False, None, str(e)

    @staticmethod
    def get_schema_for_type(entity_type: EntityType) -> type[EntitySchema]:
        """Get the appropriate Pydantic schema for an entity type"""
        type_map = {
            EntityType.CONCEPT: ConceptEntity,
            EntityType.EPISODE: EpisodeEntity,
            EntityType.SKILL: SkillEntity,
        }
        return type_map.get(entity_type, EntitySchema)


# === ONTOLOGY REGISTRY ===

class OntologyRegistry:
    """
    Central registry for entity and relationship schemas
    Enables runtime introspection and validation
    """

    _entity_schemas: Dict[EntityType, type[EntitySchema]] = {
        EntityType.CONCEPT: ConceptEntity,
        EntityType.EPISODE: EpisodeEntity,
        EntityType.SKILL: SkillEntity,
    }

    @classmethod
    def register_entity_schema(cls, entity_type: EntityType, schema: type[EntitySchema]):
        """Register a custom entity schema"""
        cls._entity_schemas[entity_type] = schema

    @classmethod
    def get_entity_schema(cls, entity_type: EntityType) -> type[EntitySchema]:
        """Get schema for entity type"""
        return cls._entity_schemas.get(entity_type, EntitySchema)

    @classmethod
    def list_entity_types(cls) -> List[EntityType]:
        """List all registered entity types"""
        return list(EntityType)

    @classmethod
    def list_relation_types(cls) -> List[RelationType]:
        """List all registered relationship types"""
        return list(RelationType)

    @classmethod
    def get_schema_info(cls) -> Dict[str, Any]:
        """Get comprehensive ontology information"""
        return {
            "entity_types": [t.value for t in EntityType],
            "relation_types": [t.value for t in RelationType],
            "memory_tiers": [t.value for t in MemoryTier],
            "registered_schemas": list(cls._entity_schemas.keys()),
            "validation_available": True
        }


if __name__ == "__main__":
    # Test the ontology
    print("=== Enhanced Memory Ontology Schema ===\n")

    # Test concept validation
    concept_data = {
        "name": "temporal_edge_modeling",
        "entity_type": "concept",
        "tier": "semantic",
        "definition": "Recording timestamps on graph relationships",
        "related_concepts": ["knowledge_graphs"],
        "observations": ["Enables time-aware retrieval"],
        "confidence_score": 0.9
    }

    valid, model, error = OntologyValidator.validate_entity(concept_data)
    print(f"Concept validation: {'✓ PASS' if valid else '✗ FAIL'}")
    if error:
        print(f"  Error: {error}")
    else:
        print(f"  Model: {model.name} ({model.entity_type})")

    print()

    # Test relationship validation
    rel_data = {
        "from_entity": "knowledge_graphs",
        "to_entity": "improved_retrieval",
        "relation_type": "causes",
        "is_causal": True,
        "causal_direction": "forward",
        "causal_strength": 0.85,
        "strength": 0.9
    }

    valid, model, error = OntologyValidator.validate_relationship(rel_data)
    print(f"Relationship validation: {'✓ PASS' if valid else '✗ FAIL'}")
    if error:
        print(f"  Error: {error}")
    else:
        print(f"  Model: {model.from_entity} --[{model.relation_type}]--> {model.to_entity}")
        print(f"  Causal: {model.is_causal}, Strength: {model.causal_strength}")

    print()

    # Show ontology info
    info = OntologyRegistry.get_schema_info()
    print("=== Ontology Registry ===")
    print(f"Entity types: {len(info['entity_types'])}")
    print(f"Relation types: {len(info['relation_types'])}")
    print(f"Memory tiers: {len(info['memory_tiers'])}")
    print(f"Validation: {info['validation_available']}")
