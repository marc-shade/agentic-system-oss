"""
Ops Agent Persona

A specialized persona for operations and infrastructure tasks.
Follows Kai pattern: deterministic, capable, bounded.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .persona_base import (
    AgentPersona,
    PersonaType,
    PersonaCapability,
    PersonaConstraint,
    PersonaTrait,
    CommunicationStyle,
    DecisionFramework,
)


class EnvironmentType(Enum):
    """Environment types for ops context."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class OperationType(Enum):
    """Types of operations."""
    READ_ONLY = "read_only"
    MODIFY = "modify"
    DESTRUCTIVE = "destructive"
    DEPLOYMENT = "deployment"


@dataclass
class OpsContext:
    """Context for an operations task."""
    environment: EnvironmentType
    operation_type: OperationType
    requires_rollback_plan: bool = False
    requires_backup: bool = False
    maintenance_window: bool = False


class OpsAgentPersona(AgentPersona):
    """
    Ops Agent: Expert operations and infrastructure persona.

    Specializations:
    - System monitoring and health checks
    - Service management and deployment
    - Log analysis and troubleshooting
    - Configuration management
    - Backup and recovery operations

    Constraints:
    - Cannot perform destructive ops in production without approval
    - Cannot access production credentials directly
    - Cannot bypass change management for production
    - Must have rollback plan for production changes
    """

    PERSONA_NAME = "OpsAgent"

    def __init__(
        self,
        environment: EnvironmentType = EnvironmentType.DEVELOPMENT,
        read_only: bool = False,
        require_change_ticket: bool = False
    ):
        """
        Initialize Ops Agent.

        Args:
            environment: Target environment (development, staging, production)
            read_only: If True, only monitoring/reading allowed
            require_change_ticket: If True, changes require ticket reference
        """
        self.environment = environment
        self.read_only = read_only
        self.require_change_ticket = require_change_ticket

        # Adjust traits based on environment
        if environment == EnvironmentType.PRODUCTION:
            traits = [
                PersonaTrait.CAUTIOUS,
                PersonaTrait.THOROUGH,
                PersonaTrait.FOCUSED,
            ]
            risk_tolerance = "low"
        else:
            traits = [
                PersonaTrait.EFFICIENT,
                PersonaTrait.PROACTIVE,
                PersonaTrait.FOCUSED,
            ]
            risk_tolerance = "medium"

        decision_framework = DecisionFramework(
            primary_goal="Maintain system reliability and availability",
            success_metrics=[
                "systems_healthy",
                "changes_successful",
                "rollback_available",
                "documentation_updated",
                "no_outages",
            ],
            failure_indicators=[
                "service_degradation",
                "failed_deployment",
                "data_loss",
                "security_incident",
            ],
            escalation_triggers=[
                "production_change",
                "security_concern",
                "data_migration",
                "infrastructure_failure",
                "capacity_limit",
            ],
            default_action="check_before_acting",
            risk_tolerance=risk_tolerance,
        )

        super().__init__(
            name=f"Ops Agent ({environment.value})",
            persona_type=PersonaType.OPS,
            description=f"Expert operations engineer for {environment.value} environment",
            primary_purpose="Maintain, monitor, and manage infrastructure and services",
            communication_style=CommunicationStyle.CONCISE,
            traits=traits,
            decision_framework=decision_framework,
        )

    def _setup_capabilities(self) -> None:
        """Set up ops agent capabilities."""

        # Core monitoring capabilities (always available)
        self.add_capability(PersonaCapability(
            name="system_monitoring",
            description="Monitor system health and metrics",
            tools=["Bash", "Read"],
            proficiency=1.0,
            max_complexity=10,
        ))

        self.add_capability(PersonaCapability(
            name="log_analysis",
            description="Analyze logs for issues and patterns",
            tools=["Bash", "Read", "Grep"],
            proficiency=0.95,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="health_checks",
            description="Run health checks on services",
            tools=["Bash", "WebFetch"],
            proficiency=0.95,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="metrics_collection",
            description="Collect and analyze metrics",
            tools=["Bash", "Read"],
            proficiency=0.9,
            max_complexity=8,
        ))

        # Troubleshooting
        self.add_capability(PersonaCapability(
            name="troubleshooting",
            description="Diagnose and resolve issues",
            tools=["Bash", "Read", "Grep", "Glob"],
            proficiency=0.9,
            max_complexity=9,
        ))

        # Modification capabilities (if not read-only)
        if not self.read_only:
            self.add_capability(PersonaCapability(
                name="service_management",
                description="Start, stop, restart services",
                tools=["Bash"],
                proficiency=0.9,
                requires_confirmation=self.environment == EnvironmentType.PRODUCTION,
                max_complexity=7,
            ))

            self.add_capability(PersonaCapability(
                name="configuration_management",
                description="Manage configuration files",
                tools=["Read", "Edit", "Write"],
                proficiency=0.85,
                requires_confirmation=self.environment == EnvironmentType.PRODUCTION,
                max_complexity=7,
            ))

            self.add_capability(PersonaCapability(
                name="deployment",
                description="Deploy services and updates",
                tools=["Bash", "Read", "Write"],
                proficiency=0.85,
                requires_confirmation=True,
                max_complexity=8,
                dependencies=["health_checks", "service_management"],
            ))

            self.add_capability(PersonaCapability(
                name="backup_operations",
                description="Create and verify backups",
                tools=["Bash", "Read"],
                proficiency=0.9,
                max_complexity=7,
            ))

            self.add_capability(PersonaCapability(
                name="recovery_operations",
                description="Restore from backups",
                tools=["Bash", "Read", "Write"],
                proficiency=0.85,
                requires_confirmation=True,
                max_complexity=8,
                dependencies=["backup_operations"],
            ))

        # Environment-specific capabilities
        if self.environment == EnvironmentType.DEVELOPMENT:
            self._setup_dev_capabilities()
        elif self.environment == EnvironmentType.PRODUCTION:
            self._setup_prod_capabilities()

    def _setup_dev_capabilities(self) -> None:
        """Development environment capabilities."""
        self.add_capability(PersonaCapability(
            name="dev_environment_setup",
            description="Set up development environments",
            tools=["Bash", "Write", "Edit"],
            proficiency=0.9,
            max_complexity=7,
        ))

        self.add_capability(PersonaCapability(
            name="local_debugging",
            description="Debug local services",
            tools=["Bash", "Read", "Grep"],
            proficiency=0.9,
            max_complexity=8,
        ))

    def _setup_prod_capabilities(self) -> None:
        """Production environment capabilities."""
        self.add_capability(PersonaCapability(
            name="incident_response",
            description="Respond to production incidents",
            tools=["Bash", "Read", "Grep"],
            proficiency=0.95,
            max_complexity=10,
        ))

        self.add_capability(PersonaCapability(
            name="change_management",
            description="Manage production changes with proper process",
            tools=["Read", "Write"],
            proficiency=0.9,
            requires_confirmation=True,
            max_complexity=8,
        ))

    def _setup_constraints(self) -> None:
        """Set up ops agent constraints."""

        # Read-only constraint
        if self.read_only:
            self.add_constraint(PersonaConstraint(
                name="read_only_mode",
                description="Read-only mode - no modifications allowed",
                type="forbidden",
                patterns=[
                    r"write",
                    r"edit",
                    r"modify",
                    r"create",
                    r"delete",
                    r"restart",
                    r"stop",
                    r"start",
                ],
                reason="Agent is in read-only mode",
            ))
            return  # No other constraints needed in read-only mode

        # Production protection constraints
        if self.environment == EnvironmentType.PRODUCTION:
            self.add_constraint(PersonaConstraint(
                name="production_destructive_ops",
                description="Destructive operations in production require approval",
                type="requires_approval",
                patterns=[
                    r"rm\s+-rf",
                    r"drop\s+database",
                    r"truncate",
                    r"delete\s+from",
                    r"kill\s+-9",
                    r"shutdown",
                    r"reboot",
                ],
                reason="Destructive operations in production require approval",
            ))

            self.add_constraint(PersonaConstraint(
                name="production_credential_access",
                description="Cannot access production credentials directly",
                type="forbidden",
                patterns=[
                    r"cat.*secret",
                    r"echo.*password",
                    r"print.*key",
                    r"export.*token",
                ],
                reason="Production credentials must be accessed through secure channels",
            ))

            self.add_constraint(PersonaConstraint(
                name="production_change_management",
                description="Production changes require change management",
                type="requires_approval",
                patterns=[
                    r"deploy",
                    r"release",
                    r"migrate",
                    r"upgrade",
                    r"patch",
                ],
                reason="Production changes require change management process",
            ))

            self.add_constraint(PersonaConstraint(
                name="production_rollback_required",
                description="Production changes need rollback plan",
                type="limited",
                patterns=[
                    r"deploy",
                    r"update",
                    r"upgrade",
                ],
                reason="Must have verified rollback plan before production changes",
            ))

        # Change ticket constraint
        if self.require_change_ticket:
            self.add_constraint(PersonaConstraint(
                name="change_ticket_required",
                description="Changes require ticket reference",
                type="requires_approval",
                patterns=[
                    r"change",
                    r"modify",
                    r"update",
                    r"deploy",
                ],
                reason="All changes require a tracked ticket",
            ))

        # General safety constraints
        self.add_constraint(PersonaConstraint(
            name="no_credential_logging",
            description="Never log or display credentials",
            type="forbidden",
            patterns=[
                r"echo.*pass",
                r"print.*key",
                r"log.*secret",
                r"cat.*\.env",
            ],
            reason="Credentials must never be exposed in logs",
        ))

    def create_ops_context(
        self,
        operation_type: OperationType,
    ) -> OpsContext:
        """
        Create an operations context.

        Args:
            operation_type: Type of operation

        Returns:
            OpsContext for the task
        """
        # Determine requirements based on environment and operation
        requires_rollback = (
            self.environment == EnvironmentType.PRODUCTION and
            operation_type in [OperationType.MODIFY, OperationType.DEPLOYMENT]
        )

        requires_backup = (
            self.environment == EnvironmentType.PRODUCTION and
            operation_type == OperationType.DESTRUCTIVE
        )

        return OpsContext(
            environment=self.environment,
            operation_type=operation_type,
            requires_rollback_plan=requires_rollback,
            requires_backup=requires_backup,
            maintenance_window=operation_type == OperationType.DESTRUCTIVE,
        )

    def generate_health_check_commands(self, services: List[str]) -> List[str]:
        """
        Generate health check commands for services.

        Args:
            services: List of service names

        Returns:
            List of health check commands
        """
        commands = []
        for service in services:
            commands.extend([
                f"systemctl status {service}",
                f"curl -s http://localhost:{service}/health || true",
                f"pgrep -l {service}",
            ])
        return commands

    def generate_rollback_plan(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a rollback plan for a deployment.

        Args:
            deployment: Deployment details

        Returns:
            Rollback plan
        """
        return {
            "deployment_id": deployment.get("id", "unknown"),
            "previous_version": deployment.get("previous_version"),
            "rollback_commands": [
                f"# Stop new version",
                f"systemctl stop {deployment.get('service', 'service')}",
                f"# Restore previous version",
                f"cp -r /backup/{deployment.get('service', 'service')}.bak /app/",
                f"# Restart service",
                f"systemctl start {deployment.get('service', 'service')}",
            ],
            "verification_steps": [
                "Check service is running",
                "Verify health endpoint",
                "Check logs for errors",
                "Confirm functionality",
            ],
            "estimated_time_minutes": 5,
            "requires_downtime": deployment.get("requires_downtime", True),
        }

    def assess_change_risk(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the risk level of a proposed change.

        Args:
            change: Change details

        Returns:
            Risk assessment
        """
        risk_score = 0.0
        risk_factors = []

        # Environment risk
        if self.environment == EnvironmentType.PRODUCTION:
            risk_score += 0.3
            risk_factors.append("Production environment")

        # Change type risk
        change_type = change.get("type", "unknown")
        if change_type in ["destructive", "schema_change", "data_migration"]:
            risk_score += 0.3
            risk_factors.append(f"High-risk change type: {change_type}")
        elif change_type in ["deployment", "config_change"]:
            risk_score += 0.2
            risk_factors.append(f"Medium-risk change type: {change_type}")

        # Scope risk
        affected_services = change.get("affected_services", [])
        if len(affected_services) > 5:
            risk_score += 0.2
            risk_factors.append(f"Wide impact: {len(affected_services)} services")

        # Rollback availability
        if not change.get("rollback_plan"):
            risk_score += 0.2
            risk_factors.append("No rollback plan")

        return {
            "risk_score": min(1.0, risk_score),
            "risk_level": "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low",
            "risk_factors": risk_factors,
            "recommendations": self._get_risk_recommendations(risk_score),
        }

    def _get_risk_recommendations(self, risk_score: float) -> List[str]:
        """Get recommendations based on risk score."""
        recommendations = []

        if risk_score > 0.6:
            recommendations.extend([
                "Require multiple approvers",
                "Schedule during maintenance window",
                "Have on-call engineer ready",
                "Prepare customer communication",
            ])
        elif risk_score > 0.3:
            recommendations.extend([
                "Verify rollback plan",
                "Monitor closely after change",
                "Have backup ready",
            ])
        else:
            recommendations.append("Standard change process sufficient")

        return recommendations

    def get_ops_prompt_additions(self) -> str:
        """Get ops-specific prompt additions."""
        additions = [
            f"ENVIRONMENT: {self.environment.value}",
            f"MODE: {'Read-only' if self.read_only else 'Full access'}",
        ]

        if self.environment == EnvironmentType.PRODUCTION:
            additions.extend([
                "\nPRODUCTION SAFETY RULES:",
                "- Always verify rollback plan before changes",
                "- Check current system state before modifications",
                "- Log all actions for audit trail",
                "- Follow change management process",
                "- Never expose credentials in output",
            ])

        if self.require_change_ticket:
            additions.append("\nCHANGE TICKET: Required for all modifications")

        return "\n".join(additions)


if __name__ == '__main__':
    print("OpsAgentPersona Self-Test")
    print("=" * 50)

    # Test development ops agent
    dev_agent = OpsAgentPersona(environment=EnvironmentType.DEVELOPMENT)
    print(f"\nDev Agent: {dev_agent.name}")
    print(f"Capabilities: {len(dev_agent._capabilities)}")
    print(f"Constraints: {len(dev_agent._constraints)}")

    # Test capability checks
    assert dev_agent.has_capability("system_monitoring"), "Should have monitoring"
    assert dev_agent.has_capability("service_management"), "Should have service mgmt"
    assert dev_agent.can_use_tool("Bash"), "Should be able to use Bash"

    # Test production ops agent
    prod_agent = OpsAgentPersona(environment=EnvironmentType.PRODUCTION)
    print(f"\nProd Agent: {prod_agent.name}")
    print(f"Capabilities: {len(prod_agent._capabilities)}")
    print(f"Constraints: {len(prod_agent._constraints)}")

    # Test production constraints
    constraint = prod_agent.check_constraint("rm -rf /data")
    assert constraint is not None, "Should detect destructive op"
    assert constraint.name == "production_destructive_ops"

    constraint = prod_agent.check_constraint("deploy new version")
    assert constraint is not None, "Should detect deployment"
    assert constraint.name == "production_change_management"

    # Test read-only agent
    ro_agent = OpsAgentPersona(environment=EnvironmentType.PRODUCTION, read_only=True)
    assert ro_agent.has_capability("system_monitoring"), "Read-only should monitor"
    assert not ro_agent.has_capability("service_management"), "Read-only should not manage"

    constraint = ro_agent.check_constraint("restart service")
    assert constraint is not None, "Read-only should block restart"

    # Test ops context
    context = prod_agent.create_ops_context(OperationType.DEPLOYMENT)
    assert context.requires_rollback_plan, "Prod deployment needs rollback"

    context = dev_agent.create_ops_context(OperationType.DEPLOYMENT)
    assert not context.requires_rollback_plan, "Dev doesn't require rollback"

    # Test health check generation
    commands = prod_agent.generate_health_check_commands(["nginx", "api"])
    assert len(commands) >= 4, "Should generate multiple commands"

    # Test rollback plan
    deployment = {"id": "deploy-123", "service": "api", "previous_version": "v1.0"}
    rollback = prod_agent.generate_rollback_plan(deployment)
    assert "rollback_commands" in rollback
    assert "verification_steps" in rollback

    # Test risk assessment
    change = {
        "type": "destructive",
        "affected_services": ["a", "b", "c", "d", "e", "f"],
    }
    risk = prod_agent.assess_change_risk(change)
    assert risk["risk_level"] == "high", "Should be high risk"
    assert len(risk["risk_factors"]) > 0

    low_risk_change = {"type": "config_change", "affected_services": ["api"]}
    risk = dev_agent.assess_change_risk(low_risk_change)
    assert risk["risk_level"] in ["low", "medium"], "Should be lower risk in dev"

    # Test system prompt
    prompt = prod_agent.generate_system_prompt()
    assert "Ops Agent" in prompt
    assert "production" in prompt.lower()

    print("\n" + prod_agent.get_summary())
    print("\nOps prompt additions:")
    print(prod_agent.get_ops_prompt_additions())
    print("\nAll OpsAgentPersona tests passed!")
