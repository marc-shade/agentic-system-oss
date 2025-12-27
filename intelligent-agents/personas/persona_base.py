"""
Persona Base Classes

Core abstractions for agent personas following Kai pattern.
Each persona defines a distinct role with specific capabilities and constraints.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
import json


class PersonaType(Enum):
    """Types of agent personas."""
    CODE = "code"           # Software development
    RESEARCH = "research"   # Information gathering and analysis
    OPS = "ops"             # Operations and infrastructure
    SECURITY = "security"   # Security analysis and enforcement
    CREATIVE = "creative"   # Content creation
    DATA = "data"           # Data analysis and processing
    SUPPORT = "support"     # User assistance
    ORCHESTRATOR = "orchestrator"  # Multi-agent coordination


class CommunicationStyle(Enum):
    """How the agent communicates."""
    TECHNICAL = "technical"     # Precise, detailed, jargon-ok
    CASUAL = "casual"           # Friendly, conversational
    FORMAL = "formal"           # Professional, structured
    CONCISE = "concise"         # Brief, to-the-point
    EDUCATIONAL = "educational" # Explanatory, teaching-oriented
    ANALYTICAL = "analytical"   # Data-driven, objective


class PersonaTrait(Enum):
    """Personality traits that affect behavior."""
    CAUTIOUS = "cautious"       # Double-checks, seeks confirmation
    PROACTIVE = "proactive"     # Anticipates needs, suggests improvements
    THOROUGH = "thorough"       # Comprehensive, doesn't cut corners
    EFFICIENT = "efficient"     # Optimizes for speed and resources
    COLLABORATIVE = "collaborative"  # Seeks input, works with others
    AUTONOMOUS = "autonomous"   # Works independently
    CURIOUS = "curious"         # Explores, asks questions
    FOCUSED = "focused"         # Stays on task, avoids tangents


@dataclass
class PersonaCapability:
    """A capability the persona has."""
    name: str
    description: str
    tools: List[str]  # Tools required for this capability
    proficiency: float = 1.0  # 0.0 to 1.0
    requires_confirmation: bool = False
    max_complexity: int = 10  # 1-10 scale
    dependencies: List[str] = field(default_factory=list)


@dataclass
class PersonaConstraint:
    """A constraint on the persona's behavior."""
    name: str
    description: str
    type: str  # "forbidden", "requires_approval", "limited"
    patterns: List[str] = field(default_factory=list)  # Regex patterns
    reason: str = ""


@dataclass
class DecisionFramework:
    """How the persona makes decisions."""
    primary_goal: str
    success_metrics: List[str]
    failure_indicators: List[str]
    escalation_triggers: List[str]
    default_action: str = "ask_for_clarification"
    risk_tolerance: str = "medium"  # low, medium, high


class AgentPersona(ABC):
    """
    Base class for all agent personas.

    A persona defines WHO the agent is, not just WHAT it does.
    It includes:
    - Identity and purpose
    - Capabilities and constraints
    - Communication style
    - Decision-making framework
    - Behavioral traits
    """

    def __init__(
        self,
        name: str,
        persona_type: PersonaType,
        description: str,
        primary_purpose: str,
        communication_style: CommunicationStyle = CommunicationStyle.TECHNICAL,
        traits: Optional[List[PersonaTrait]] = None,
        decision_framework: Optional[DecisionFramework] = None
    ):
        """Initialize persona.

        Args:
            name: Persona name
            persona_type: Type of persona
            description: What this persona is
            primary_purpose: Main objective
            communication_style: How to communicate
            traits: Personality traits
            decision_framework: How to make decisions
        """
        self.name = name
        self.persona_type = persona_type
        self.description = description
        self.primary_purpose = primary_purpose
        self.communication_style = communication_style
        self.traits = traits or []

        self.decision_framework = decision_framework or DecisionFramework(
            primary_goal=primary_purpose,
            success_metrics=["task_completed", "user_satisfied"],
            failure_indicators=["error_occurred", "user_frustrated"],
            escalation_triggers=["uncertain", "high_risk", "out_of_scope"],
        )

        # Initialize capability and constraint registries
        self._capabilities: Dict[str, PersonaCapability] = {}
        self._constraints: Dict[str, PersonaConstraint] = {}
        self._tool_access: Set[str] = set()

        # Set up persona-specific capabilities
        self._setup_capabilities()
        self._setup_constraints()

    @abstractmethod
    def _setup_capabilities(self) -> None:
        """Set up persona-specific capabilities. Override in subclasses."""
        pass

    @abstractmethod
    def _setup_constraints(self) -> None:
        """Set up persona-specific constraints. Override in subclasses."""
        pass

    def add_capability(self, capability: PersonaCapability) -> None:
        """Add a capability to this persona."""
        self._capabilities[capability.name] = capability
        self._tool_access.update(capability.tools)

    def remove_capability(self, capability_name: str) -> bool:
        """Remove a capability."""
        if capability_name in self._capabilities:
            cap = self._capabilities.pop(capability_name)
            # Re-calculate tool access
            self._tool_access = set()
            for c in self._capabilities.values():
                self._tool_access.update(c.tools)
            return True
        return False

    def add_constraint(self, constraint: PersonaConstraint) -> None:
        """Add a constraint to this persona."""
        self._constraints[constraint.name] = constraint

    def has_capability(self, capability_name: str) -> bool:
        """Check if persona has a capability."""
        return capability_name in self._capabilities

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if persona can use a specific tool."""
        return tool_name in self._tool_access

    def get_allowed_tools(self) -> List[str]:
        """Get list of tools this persona can use."""
        return sorted(self._tool_access)

    def check_constraint(self, action: str) -> Optional[PersonaConstraint]:
        """Check if action violates any constraint.

        Returns:
            The violated constraint, or None if action is allowed
        """
        import re
        action_lower = action.lower()

        for constraint in self._constraints.values():
            for pattern in constraint.patterns:
                if re.search(pattern, action_lower, re.IGNORECASE):
                    return constraint

        return None

    def should_escalate(self, context: Dict[str, Any]) -> bool:
        """Check if current context should trigger escalation."""
        for trigger in self.decision_framework.escalation_triggers:
            trigger_lower = trigger.lower()

            # Check context values
            for key, value in context.items():
                if trigger_lower in str(key).lower() or trigger_lower in str(value).lower():
                    return True

        return False

    def format_response(self, content: str) -> str:
        """Format response according to communication style."""
        if self.communication_style == CommunicationStyle.CONCISE:
            # Truncate to essentials
            lines = content.split('\n')
            return '\n'.join(lines[:5]) if len(lines) > 5 else content

        elif self.communication_style == CommunicationStyle.FORMAL:
            # Add structure
            return f"Response:\n{content}\n"

        elif self.communication_style == CommunicationStyle.EDUCATIONAL:
            # Add explanation
            return f"{content}\n\nNote: This response was generated by {self.name}."

        return content

    def generate_system_prompt(self) -> str:
        """Generate a system prompt for this persona."""
        capabilities_list = "\n".join([
            f"  - {cap.name}: {cap.description}"
            for cap in self._capabilities.values()
        ])

        constraints_list = "\n".join([
            f"  - {con.name}: {con.description}"
            for con in self._constraints.values()
        ])

        traits_list = ", ".join([t.value for t in self.traits])

        prompt = f"""You are {self.name}, a {self.persona_type.value} agent.

PURPOSE: {self.primary_purpose}

DESCRIPTION: {self.description}

TRAITS: {traits_list or "balanced, helpful"}

COMMUNICATION STYLE: {self.communication_style.value}

CAPABILITIES:
{capabilities_list or "  - General assistance"}

CONSTRAINTS (DO NOT VIOLATE):
{constraints_list or "  - None specified"}

DECISION FRAMEWORK:
  - Primary Goal: {self.decision_framework.primary_goal}
  - Risk Tolerance: {self.decision_framework.risk_tolerance}
  - Default Action: {self.decision_framework.default_action}
  - Escalate When: {', '.join(self.decision_framework.escalation_triggers)}

TOOLS AVAILABLE: {', '.join(sorted(self._tool_access)) or "None"}

Remember: Stay within your defined scope. If asked to do something outside your capabilities or that violates constraints, explain what you can and cannot do.
"""
        return prompt

    def to_dict(self) -> Dict[str, Any]:
        """Serialize persona to dictionary."""
        return {
            "name": self.name,
            "type": self.persona_type.value,
            "description": self.description,
            "primary_purpose": self.primary_purpose,
            "communication_style": self.communication_style.value,
            "traits": [t.value for t in self.traits],
            "capabilities": {
                name: {
                    "description": cap.description,
                    "tools": cap.tools,
                    "proficiency": cap.proficiency,
                } for name, cap in self._capabilities.items()
            },
            "constraints": {
                name: {
                    "description": con.description,
                    "type": con.type,
                    "reason": con.reason,
                } for name, con in self._constraints.items()
            },
            "tool_access": list(self._tool_access),
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Persona: {self.name}",
            f"Type: {self.persona_type.value}",
            f"Purpose: {self.primary_purpose}",
            f"Style: {self.communication_style.value}",
            f"Traits: {', '.join(t.value for t in self.traits)}",
            f"Capabilities: {len(self._capabilities)}",
            f"Constraints: {len(self._constraints)}",
            f"Tools: {len(self._tool_access)}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"


if __name__ == '__main__':
    # Self-test with a simple concrete implementation
    class TestPersona(AgentPersona):
        def _setup_capabilities(self):
            self.add_capability(PersonaCapability(
                name="test_capability",
                description="A test capability",
                tools=["Read", "Write"],
                proficiency=0.9,
            ))

        def _setup_constraints(self):
            self.add_constraint(PersonaConstraint(
                name="no_delete",
                description="Cannot delete files",
                type="forbidden",
                patterns=[r"delete", r"remove", r"rm\s+-rf"],
                reason="Deletion is not allowed",
            ))

    print("AgentPersona Base Class Self-Test")
    print("=" * 50)

    persona = TestPersona(
        name="Test Agent",
        persona_type=PersonaType.CODE,
        description="A test agent for validation",
        primary_purpose="Test the persona system",
        traits=[PersonaTrait.CAUTIOUS, PersonaTrait.THOROUGH],
    )

    # Test capability checks
    assert persona.has_capability("test_capability"), "Should have test_capability"
    assert not persona.has_capability("unknown"), "Should not have unknown"

    # Test tool access
    assert persona.can_use_tool("Read"), "Should be able to use Read"
    assert persona.can_use_tool("Write"), "Should be able to use Write"
    assert not persona.can_use_tool("Bash"), "Should not be able to use Bash"

    # Test constraint checking
    constraint = persona.check_constraint("delete all files")
    assert constraint is not None, "Should detect constraint violation"
    assert constraint.name == "no_delete", "Should be no_delete constraint"

    safe_constraint = persona.check_constraint("read the file")
    assert safe_constraint is None, "Safe action should not violate constraints"

    # Test serialization
    data = persona.to_dict()
    assert data["name"] == "Test Agent"
    assert "test_capability" in data["capabilities"]

    # Test system prompt generation
    prompt = persona.generate_system_prompt()
    assert "Test Agent" in prompt
    assert "test_capability" in prompt

    print(persona.get_summary())
    print()
    print("System Prompt Preview:")
    print("-" * 40)
    print(prompt[:500] + "...")

    print()
    print("All AgentPersona base tests passed!")
