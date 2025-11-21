"""Agent decision and output schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    EXECUTE = "execute"
    DELEGATE = "delegate"
    QUERY = "query"
    RESPOND = "respond"
    WAIT = "wait"
    ESCALATE = "escalate"


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(description="Why this tool is being called")


class AgentDecision(BaseModel):
    action: ActionType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Chain of thought reasoning")
    tool_calls: List[ToolCall] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class TaskDecomposition(BaseModel):
    original_task: str
    subtasks: List[str] = Field(min_length=1)
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    estimated_complexity: int = Field(ge=1, le=10)


class AgentResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    follow_up_questions: List[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    step_number: int
    description: str
    tool: Optional[str] = None
    expected_output: str
    fallback: Optional[str] = None


class ExecutionPlan(BaseModel):
    goal: str
    steps: List[PlanStep]
    success_criteria: List[str]
    estimated_duration: Optional[str] = None


class ErrorRecovery(BaseModel):
    error_type: str
    severity: Priority
    recovery_actions: List[str]
    can_continue: bool
    user_action_required: bool
