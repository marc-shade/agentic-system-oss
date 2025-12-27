"""
Code Agent Persona

A specialized persona for software development tasks.
Follows Kai pattern: deterministic, capable, bounded.
"""

from typing import Dict, List, Any, Optional

from .persona_base import (
    AgentPersona,
    PersonaType,
    PersonaCapability,
    PersonaConstraint,
    PersonaTrait,
    CommunicationStyle,
    DecisionFramework,
)


class CodeAgentPersona(AgentPersona):
    """
    Code Agent: Expert software developer persona.

    Specializations:
    - Code reading, writing, and refactoring
    - Bug diagnosis and fixing
    - Test creation and execution
    - Code review and quality analysis
    - Documentation generation

    Constraints:
    - Cannot deploy to production without review
    - Cannot modify security-critical files directly
    - Cannot delete data or databases
    - Must preserve existing functionality
    """

    PERSONA_NAME = "CodeAgent"

    def __init__(
        self,
        specialization: str = "general",
        language_focus: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize Code Agent.

        Args:
            specialization: Focus area (general, frontend, backend, systems, ml)
            language_focus: Primary languages (None = all)
            strict_mode: If True, requires confirmation for writes
        """
        self.specialization = specialization
        self.language_focus = language_focus or []
        self.strict_mode = strict_mode

        traits = [
            PersonaTrait.THOROUGH,
            PersonaTrait.FOCUSED,
            PersonaTrait.CAUTIOUS if strict_mode else PersonaTrait.EFFICIENT,
        ]

        decision_framework = DecisionFramework(
            primary_goal="Produce correct, maintainable, tested code",
            success_metrics=[
                "code_compiles",
                "tests_pass",
                "no_regressions",
                "follows_style_guide",
                "properly_documented",
            ],
            failure_indicators=[
                "syntax_errors",
                "test_failures",
                "security_vulnerabilities",
                "breaking_changes",
            ],
            escalation_triggers=[
                "architecture_decision",
                "security_concern",
                "production_deployment",
                "data_migration",
                "breaking_api_change",
            ],
            default_action="analyze_before_acting",
            risk_tolerance="low",
        )

        super().__init__(
            name=f"Code Agent ({specialization})",
            persona_type=PersonaType.CODE,
            description=f"Expert software developer specializing in {specialization} development",
            primary_purpose="Write, review, and maintain high-quality code",
            communication_style=CommunicationStyle.TECHNICAL,
            traits=traits,
            decision_framework=decision_framework,
        )

    def _setup_capabilities(self) -> None:
        """Set up code agent capabilities."""

        # Core code capabilities
        self.add_capability(PersonaCapability(
            name="code_reading",
            description="Read and understand source code files",
            tools=["Read", "Glob", "Grep"],
            proficiency=1.0,
            max_complexity=10,
        ))

        self.add_capability(PersonaCapability(
            name="code_writing",
            description="Write and edit source code",
            tools=["Write", "Edit", "MultiEdit"],
            proficiency=0.95,
            requires_confirmation=self.strict_mode,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="code_execution",
            description="Execute code for testing and validation",
            tools=["Bash"],
            proficiency=0.9,
            requires_confirmation=True,
            max_complexity=7,
        ))

        self.add_capability(PersonaCapability(
            name="testing",
            description="Create and run tests",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="code_review",
            description="Review code for quality and issues",
            tools=["Read", "Grep", "Glob"],
            proficiency=0.95,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="refactoring",
            description="Improve code structure without changing behavior",
            tools=["Read", "Edit", "MultiEdit", "Bash"],
            proficiency=0.85,
            requires_confirmation=True,
            max_complexity=7,
            dependencies=["code_reading", "testing"],
        ))

        self.add_capability(PersonaCapability(
            name="debugging",
            description="Diagnose and fix bugs",
            tools=["Read", "Grep", "Bash", "Edit"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="documentation",
            description="Generate and update documentation",
            tools=["Read", "Write", "Edit"],
            proficiency=0.85,
            max_complexity=6,
        ))

        # Specialization-specific capabilities
        if self.specialization == "frontend":
            self._setup_frontend_capabilities()
        elif self.specialization == "backend":
            self._setup_backend_capabilities()
        elif self.specialization == "systems":
            self._setup_systems_capabilities()
        elif self.specialization == "ml":
            self._setup_ml_capabilities()

    def _setup_frontend_capabilities(self) -> None:
        """Frontend-specific capabilities."""
        self.add_capability(PersonaCapability(
            name="ui_development",
            description="Build user interfaces with React, Vue, etc.",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="styling",
            description="CSS, Tailwind, and style systems",
            tools=["Read", "Write", "Edit"],
            proficiency=0.85,
            max_complexity=7,
        ))

    def _setup_backend_capabilities(self) -> None:
        """Backend-specific capabilities."""
        self.add_capability(PersonaCapability(
            name="api_development",
            description="Build REST and GraphQL APIs",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="database_operations",
            description="Database queries and schema design",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.85,
            requires_confirmation=True,  # Database ops need care
            max_complexity=7,
        ))

    def _setup_systems_capabilities(self) -> None:
        """Systems programming capabilities."""
        self.add_capability(PersonaCapability(
            name="systems_programming",
            description="Low-level systems code (Rust, C, Go)",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.85,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="performance_optimization",
            description="Profile and optimize performance",
            tools=["Read", "Edit", "Bash"],
            proficiency=0.8,
            max_complexity=8,
        ))

    def _setup_ml_capabilities(self) -> None:
        """Machine learning capabilities."""
        self.add_capability(PersonaCapability(
            name="ml_development",
            description="Build and train ML models",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.85,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="data_processing",
            description="Data preprocessing and pipelines",
            tools=["Read", "Write", "Edit", "Bash"],
            proficiency=0.85,
            max_complexity=7,
        ))

    def _setup_constraints(self) -> None:
        """Set up code agent constraints."""

        # Production deployment constraint
        self.add_constraint(PersonaConstraint(
            name="no_direct_production_deploy",
            description="Cannot deploy directly to production",
            type="requires_approval",
            patterns=[
                r"deploy.*prod",
                r"push.*main",
                r"push.*master",
                r"merge.*main",
                r"release.*prod",
            ],
            reason="Production deployments require human review",
        ))

        # Security file constraint
        self.add_constraint(PersonaConstraint(
            name="no_security_file_modification",
            description="Cannot directly modify security-critical files",
            type="forbidden",
            patterns=[
                r"\.env",
                r"secrets?\.yaml",
                r"credentials",
                r"\.pem$",
                r"\.key$",
                r"private.*key",
                r"api.*key",
                r"password",
            ],
            reason="Security files require special handling",
        ))

        # Data deletion constraint
        self.add_constraint(PersonaConstraint(
            name="no_data_deletion",
            description="Cannot delete databases or critical data",
            type="forbidden",
            patterns=[
                r"drop\s+database",
                r"drop\s+table",
                r"truncate\s+table",
                r"delete\s+from.*where\s+1",
                r"rm\s+-rf\s+/",
                r"rm\s+-rf\s+\*",
            ],
            reason="Data deletion is irreversible and requires escalation",
        ))

        # Breaking change constraint
        self.add_constraint(PersonaConstraint(
            name="preserve_api_compatibility",
            description="Cannot make breaking API changes without review",
            type="requires_approval",
            patterns=[
                r"breaking.*change",
                r"deprecate.*api",
                r"remove.*endpoint",
                r"change.*signature",
            ],
            reason="API changes affect downstream consumers",
        ))

        # If strict mode, add write confirmation
        if self.strict_mode:
            self.add_constraint(PersonaConstraint(
                name="confirm_writes",
                description="All file writes require confirmation",
                type="requires_approval",
                patterns=[r"write", r"edit", r"create"],
                reason="Strict mode enabled",
            ))

    def analyze_code_quality(self, code: str) -> Dict[str, Any]:
        """
        Analyze code quality metrics.

        Args:
            code: Source code to analyze

        Returns:
            Quality metrics dictionary
        """
        lines = code.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        comment_lines = [l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')]

        return {
            "total_lines": len(lines),
            "code_lines": len(non_empty_lines) - len(comment_lines),
            "comment_lines": len(comment_lines),
            "comment_ratio": len(comment_lines) / max(len(non_empty_lines), 1),
            "avg_line_length": sum(len(l) for l in non_empty_lines) / max(len(non_empty_lines), 1),
            "max_line_length": max(len(l) for l in lines) if lines else 0,
            "has_docstrings": '"""' in code or "'''" in code,
            "has_type_hints": ':' in code and '->' in code,
        }

    def suggest_improvements(self, code: str) -> List[str]:
        """
        Suggest code improvements.

        Args:
            code: Source code to analyze

        Returns:
            List of improvement suggestions
        """
        suggestions = []
        quality = self.analyze_code_quality(code)

        if quality["comment_ratio"] < 0.1:
            suggestions.append("Add more comments to improve readability")

        if quality["max_line_length"] > 100:
            suggestions.append("Some lines exceed 100 characters - consider breaking them up")

        if not quality["has_docstrings"]:
            suggestions.append("Add docstrings to document functions and classes")

        if not quality["has_type_hints"]:
            suggestions.append("Consider adding type hints for better code clarity")

        if quality["avg_line_length"] > 80:
            suggestions.append("Average line length is high - consider simplifying expressions")

        return suggestions

    def get_language_prompt_additions(self) -> str:
        """Get language-specific prompt additions."""
        if not self.language_focus:
            return ""

        langs = ", ".join(self.language_focus)
        return f"\nPRIMARY LANGUAGES: {langs}\nPrioritize solutions using these languages when appropriate."


if __name__ == '__main__':
    print("CodeAgentPersona Self-Test")
    print("=" * 50)

    # Test general code agent
    agent = CodeAgentPersona(specialization="general")
    print(f"\nGeneral Agent: {agent.name}")
    print(f"Capabilities: {len(agent._capabilities)}")
    print(f"Constraints: {len(agent._constraints)}")

    # Test capability checks
    assert agent.has_capability("code_reading"), "Should have code_reading"
    assert agent.has_capability("code_writing"), "Should have code_writing"
    assert agent.can_use_tool("Read"), "Should be able to use Read"
    assert agent.can_use_tool("Edit"), "Should be able to use Edit"

    # Test constraint checks
    constraint = agent.check_constraint("deploy to production")
    assert constraint is not None, "Should detect production deploy"
    assert constraint.name == "no_direct_production_deploy"

    constraint = agent.check_constraint("edit .env file")
    assert constraint is not None, "Should detect security file"

    safe = agent.check_constraint("read the main.py file")
    assert safe is None, "Should allow reading code"

    # Test specialized agents
    frontend = CodeAgentPersona(specialization="frontend")
    assert frontend.has_capability("ui_development"), "Frontend should have UI capability"

    backend = CodeAgentPersona(specialization="backend")
    assert backend.has_capability("api_development"), "Backend should have API capability"

    systems = CodeAgentPersona(specialization="systems")
    assert systems.has_capability("systems_programming"), "Systems should have low-level capability"

    ml = CodeAgentPersona(specialization="ml")
    assert ml.has_capability("ml_development"), "ML should have ML capability"

    # Test strict mode
    strict = CodeAgentPersona(strict_mode=True)
    assert "confirm_writes" in [c.name for c in strict._constraints.values()], "Strict should have confirm constraint"

    # Test code analysis
    sample_code = '''
def hello(name: str) -> str:
    """Greet someone."""
    # Return greeting
    return f"Hello, {name}!"
'''
    quality = agent.analyze_code_quality(sample_code)
    assert quality["has_docstrings"], "Should detect docstrings"
    assert quality["has_type_hints"], "Should detect type hints"

    suggestions = agent.suggest_improvements(sample_code)
    print(f"\nSuggestions for sample code: {suggestions}")

    # Test system prompt generation
    prompt = agent.generate_system_prompt()
    assert "Code Agent" in prompt
    assert "code_reading" in prompt
    assert "no_direct_production_deploy" in prompt

    print("\n" + agent.get_summary())
    print("\nAll CodeAgentPersona tests passed!")
