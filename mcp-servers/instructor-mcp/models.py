"""
Common Pydantic models for agentic system structured extraction.
Production-ready models with full validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    TOOL = "tool"
    PROJECT = "project"
    TASK = "task"
    MEMORY = "memory"


# Core extraction models

class ExtractedEntity(BaseModel):
    """Entity extracted from text with confidence scoring."""
    name: str = Field(..., min_length=1, description="Entity name")
    entity_type: EntityType = Field(..., description="Type of entity")
    description: Optional[str] = Field(None, description="Brief description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('confidence')
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class ExtractedRelation(BaseModel):
    """Relationship between two entities."""
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Type of relationship")
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    bidirectional: bool = Field(default=False)


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph extraction."""
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relations: List[ExtractedRelation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskExtraction(BaseModel):
    """Structured task extracted from natural language."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Priority = Field(default=Priority.MEDIUM)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000)
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None


class ActionItem(BaseModel):
    """Action item from meeting notes or conversation."""
    action: str = Field(..., description="What needs to be done")
    owner: Optional[str] = Field(None, description="Person responsible")
    deadline: Optional[str] = Field(None, description="When it's due")
    context: Optional[str] = Field(None, description="Additional context")
    priority: Priority = Field(default=Priority.MEDIUM)


class MeetingNotes(BaseModel):
    """Structured meeting notes extraction."""
    title: str = Field(..., description="Meeting title")
    date: Optional[datetime] = None
    attendees: List[str] = Field(default_factory=list)
    summary: str = Field(..., description="Brief meeting summary")
    key_points: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)


class CodeAnalysis(BaseModel):
    """Code analysis extraction for agentic coding."""
    language: str = Field(..., description="Programming language")
    purpose: str = Field(..., description="What the code does")
    complexity: str = Field(..., description="low/medium/high/very_high")
    functions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class MemoryEntry(BaseModel):
    """Entry for enhanced-memory-mcp integration."""
    name: str = Field(..., min_length=1)
    entity_type: str = Field(...)
    observations: List[str] = Field(default_factory=list, min_length=1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Where this info came from")


class ExtractionResult(BaseModel):
    """Generic wrapper for extraction results."""
    success: bool = Field(default=True)
    data: Any = Field(...)
    model_used: str = Field(default="claude-sonnet-4-20250514")
    extraction_time_ms: float = Field(default=0.0)
    retries: int = Field(default=0)
    validation_errors: List[str] = Field(default_factory=list)


# Registry of available models for dynamic schema selection
MODEL_REGISTRY: Dict[str, type[BaseModel]] = {
    "entity": ExtractedEntity,
    "relation": ExtractedRelation,
    "knowledge_graph": KnowledgeGraph,
    "task": TaskExtraction,
    "action_item": ActionItem,
    "meeting_notes": MeetingNotes,
    "code_analysis": CodeAnalysis,
    "memory_entry": MemoryEntry,
}


def get_model(name: str) -> Optional[type[BaseModel]]:
    """Get a model class by name."""
    return MODEL_REGISTRY.get(name.lower())


def list_available_models() -> List[str]:
    """List all available model names."""
    return list(MODEL_REGISTRY.keys())
