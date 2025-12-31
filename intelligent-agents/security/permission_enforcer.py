"""
Permission Enforcer

Role-based access control for agent operations.
Following Kai pattern: Explicit permissions, deny by default.

Permission model:
1. Subjects (who) - Users, agents, services
2. Actions (what) - Operations that can be performed
3. Resources (where) - What the actions apply to
4. Conditions (when) - Contextual requirements
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
from datetime import datetime, time
import re


class PermissionAction(Enum):
    """Actions that can be controlled."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    CREATE = "create"
    UPDATE = "update"
    ADMIN = "admin"
    DELEGATE = "delegate"  # Can grant permissions to others


class ResourceType(Enum):
    """Types of resources that can be protected."""
    FILE = "file"
    DIRECTORY = "directory"
    DATABASE = "database"
    API = "api"
    SERVICE = "service"
    MEMORY = "memory"
    TOOL = "tool"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class Permission:
    """A single permission grant."""
    action: PermissionAction
    resource_type: ResourceType
    resource_pattern: str  # Regex pattern for matching resources
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    granted_by: str = "system"
    reason: str = ""


@dataclass
class Role:
    """A role with associated permissions."""
    name: str
    description: str
    permissions: List[Permission]
    parent_roles: List[str] = field(default_factory=list)  # Role inheritance
    is_active: bool = True


@dataclass
class Subject:
    """An entity that can request permissions."""
    id: str
    name: str
    subject_type: str  # user, agent, service
    roles: List[str]
    direct_permissions: List[Permission] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionRequest:
    """A request for permission to perform an action."""
    subject_id: str
    action: PermissionAction
    resource_type: ResourceType
    resource_id: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionDecision:
    """Result of permission check."""
    allowed: bool
    subject_id: str
    action: PermissionAction
    resource_id: str
    matching_permission: Optional[Permission] = None
    denial_reason: str = ""
    conditions_met: Dict[str, bool] = field(default_factory=dict)


class PermissionEnforcer:
    """Enforces role-based access control."""

    # Default roles
    DEFAULT_ROLES: Dict[str, Role] = {
        "viewer": Role(
            name="viewer",
            description="Read-only access",
            permissions=[
                Permission(
                    action=PermissionAction.READ,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.READ,
                    resource_type=ResourceType.MEMORY,
                    resource_pattern=".*",
                ),
            ]
        ),
        "editor": Role(
            name="editor",
            description="Read and write access",
            permissions=[
                Permission(
                    action=PermissionAction.READ,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.WRITE,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                    conditions={"exclude_patterns": ["*.key", "*.pem", "*secret*"]},
                ),
                Permission(
                    action=PermissionAction.CREATE,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.UPDATE,
                    resource_type=ResourceType.MEMORY,
                    resource_pattern=".*",
                ),
            ],
            parent_roles=["viewer"],
        ),
        "operator": Role(
            name="operator",
            description="Can execute operations",
            permissions=[
                Permission(
                    action=PermissionAction.EXECUTE,
                    resource_type=ResourceType.TOOL,
                    resource_pattern=".*",
                    conditions={"exclude_tools": ["admin_*", "system_*"]},
                ),
                Permission(
                    action=PermissionAction.EXECUTE,
                    resource_type=ResourceType.SERVICE,
                    resource_pattern=".*",
                ),
            ],
            parent_roles=["editor"],
        ),
        "admin": Role(
            name="admin",
            description="Full system access",
            permissions=[
                Permission(
                    action=PermissionAction.ADMIN,
                    resource_type=ResourceType.SYSTEM,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.DELETE,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.DELEGATE,
                    resource_type=ResourceType.SYSTEM,
                    resource_pattern=".*",
                ),
            ],
            parent_roles=["operator"],
        ),
        "agent": Role(
            name="agent",
            description="Autonomous agent permissions",
            permissions=[
                Permission(
                    action=PermissionAction.READ,
                    resource_type=ResourceType.FILE,
                    resource_pattern=".*",
                ),
                Permission(
                    action=PermissionAction.WRITE,
                    resource_type=ResourceType.FILE,
                    resource_pattern=r"^(?!.*\.(key|pem|env)).*$",  # Exclude sensitive
                ),
                Permission(
                    action=PermissionAction.EXECUTE,
                    resource_type=ResourceType.TOOL,
                    resource_pattern=".*",
                    conditions={
                        "require_confirmation": ["Bash", "Delete", "SystemModify"],
                        "time_window": {"start": "06:00", "end": "22:00"},
                    },
                ),
                Permission(
                    action=PermissionAction.UPDATE,
                    resource_type=ResourceType.MEMORY,
                    resource_pattern=".*",
                ),
            ],
        ),
    }

    def __init__(
        self,
        roles: Optional[Dict[str, Role]] = None,
        subjects: Optional[Dict[str, Subject]] = None,
        condition_evaluators: Optional[Dict[str, Callable]] = None
    ):
        """Initialize enforcer.

        Args:
            roles: Custom role definitions (merged with defaults)
            subjects: Known subjects
            condition_evaluators: Custom condition evaluation functions
        """
        self.roles = dict(self.DEFAULT_ROLES)
        if roles:
            self.roles.update(roles)

        self.subjects: Dict[str, Subject] = subjects or {}

        # Default condition evaluators
        self.condition_evaluators: Dict[str, Callable] = {
            "time_window": self._check_time_window,
            "exclude_patterns": self._check_exclude_patterns,
            "exclude_tools": self._check_exclude_tools,
            "require_confirmation": self._check_require_confirmation,
            "max_size": self._check_max_size,
            "ip_whitelist": self._check_ip_whitelist,
        }
        if condition_evaluators:
            self.condition_evaluators.update(condition_evaluators)

    def register_subject(self, subject: Subject) -> None:
        """Register a subject (user, agent, service)."""
        self.subjects[subject.id] = subject

    def check_permission(self, request: PermissionRequest) -> PermissionDecision:
        """Check if a permission request should be allowed.

        Args:
            request: The permission request

        Returns:
            PermissionDecision with result
        """
        # Get subject
        if request.subject_id not in self.subjects:
            return PermissionDecision(
                allowed=False,
                subject_id=request.subject_id,
                action=request.action,
                resource_id=request.resource_id,
                denial_reason=f"Unknown subject: {request.subject_id}",
            )

        subject = self.subjects[request.subject_id]

        # Collect all permissions from roles and direct grants
        all_permissions = list(subject.direct_permissions)
        for role_name in subject.roles:
            all_permissions.extend(self._get_role_permissions(role_name))

        # Find matching permission
        for perm in all_permissions:
            if self._permission_matches(perm, request):
                # Check conditions
                conditions_met, failed_condition = self._evaluate_conditions(
                    perm, request
                )

                if all(conditions_met.values()):
                    # Check expiry
                    if perm.expires_at and datetime.now() > perm.expires_at:
                        continue

                    return PermissionDecision(
                        allowed=True,
                        subject_id=request.subject_id,
                        action=request.action,
                        resource_id=request.resource_id,
                        matching_permission=perm,
                        conditions_met=conditions_met,
                    )
                else:
                    return PermissionDecision(
                        allowed=False,
                        subject_id=request.subject_id,
                        action=request.action,
                        resource_id=request.resource_id,
                        matching_permission=perm,
                        denial_reason=f"Condition failed: {failed_condition}",
                        conditions_met=conditions_met,
                    )

        # No matching permission - deny by default
        return PermissionDecision(
            allowed=False,
            subject_id=request.subject_id,
            action=request.action,
            resource_id=request.resource_id,
            denial_reason="No matching permission found",
        )

    def _get_role_permissions(self, role_name: str) -> List[Permission]:
        """Get all permissions for a role, including inherited."""
        if role_name not in self.roles:
            return []

        role = self.roles[role_name]
        if not role.is_active:
            return []

        permissions = list(role.permissions)

        # Add inherited permissions
        for parent_role in role.parent_roles:
            permissions.extend(self._get_role_permissions(parent_role))

        return permissions

    def _permission_matches(
        self,
        permission: Permission,
        request: PermissionRequest
    ) -> bool:
        """Check if permission matches request."""
        # Check action
        if permission.action != request.action:
            # Admin action allows everything
            if permission.action != PermissionAction.ADMIN:
                return False

        # Check resource type
        if permission.resource_type != request.resource_type:
            # System resource type allows everything
            if permission.resource_type != ResourceType.SYSTEM:
                return False

        # Check resource pattern
        try:
            pattern = re.compile(permission.resource_pattern)
            if not pattern.match(request.resource_id):
                return False
        except re.error:
            return False

        return True

    def _evaluate_conditions(
        self,
        permission: Permission,
        request: PermissionRequest
    ) -> tuple:
        """Evaluate permission conditions.

        Returns:
            (conditions_met dict, first_failed_condition or None)
        """
        conditions_met = {}
        failed_condition = None

        for condition_name, condition_value in permission.conditions.items():
            if condition_name in self.condition_evaluators:
                evaluator = self.condition_evaluators[condition_name]
                result = evaluator(condition_value, request)
                conditions_met[condition_name] = result
                if not result and failed_condition is None:
                    failed_condition = condition_name
            else:
                # Unknown condition - fail safe
                conditions_met[condition_name] = False
                if failed_condition is None:
                    failed_condition = f"unknown:{condition_name}"

        return conditions_met, failed_condition

    # Condition evaluators
    def _check_time_window(self, config: Dict, request: PermissionRequest) -> bool:
        """Check if current time is within allowed window."""
        now = datetime.now().time()
        start = time.fromisoformat(config.get("start", "00:00"))
        end = time.fromisoformat(config.get("end", "23:59"))

        if start <= end:
            return start <= now <= end
        else:
            # Overnight window (e.g., 22:00 to 06:00)
            return now >= start or now <= end

    def _check_exclude_patterns(
        self, patterns: List[str], request: PermissionRequest
    ) -> bool:
        """Check if resource doesn't match excluded patterns."""
        resource = request.resource_id.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower().replace("*", "")
            if pattern_lower in resource:
                return False
        return True

    def _check_exclude_tools(
        self, tools: List[str], request: PermissionRequest
    ) -> bool:
        """Check if tool is not in excluded list."""
        resource = request.resource_id
        for tool_pattern in tools:
            if tool_pattern.endswith("*"):
                if resource.startswith(tool_pattern[:-1]):
                    return False
            elif resource == tool_pattern:
                return False
        return True

    def _check_require_confirmation(
        self, tools: List[str], request: PermissionRequest
    ) -> bool:
        """Check if confirmation is required (returns False to trigger review)."""
        if request.resource_id in tools:
            # Need confirmation - check if provided in context
            return request.context.get("confirmation_provided", False)
        return True

    def _check_max_size(self, max_bytes: int, request: PermissionRequest) -> bool:
        """Check if resource size is within limit."""
        size = request.context.get("size_bytes", 0)
        return size <= max_bytes

    def _check_ip_whitelist(
        self, whitelist: List[str], request: PermissionRequest
    ) -> bool:
        """Check if request IP is whitelisted."""
        ip = request.context.get("ip_address", "")
        return ip in whitelist

    def is_allowed(
        self,
        subject_id: str,
        action: PermissionAction,
        resource_type: ResourceType,
        resource_id: str
    ) -> bool:
        """Quick check if action is allowed."""
        request = PermissionRequest(
            subject_id=subject_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        decision = self.check_permission(request)
        return decision.allowed

    def grant_permission(
        self,
        subject_id: str,
        permission: Permission,
        granter_id: str
    ) -> bool:
        """Grant a permission to a subject.

        Args:
            subject_id: Subject to grant to
            permission: Permission to grant
            granter_id: Who is granting

        Returns:
            True if granted successfully
        """
        # Check if granter has delegate permission
        if not self.is_allowed(
            granter_id,
            PermissionAction.DELEGATE,
            ResourceType.SYSTEM,
            "permissions"
        ):
            return False

        if subject_id not in self.subjects:
            return False

        permission.granted_by = granter_id
        self.subjects[subject_id].direct_permissions.append(permission)
        return True

    def revoke_permission(
        self,
        subject_id: str,
        action: PermissionAction,
        resource_pattern: str
    ) -> bool:
        """Revoke a direct permission from a subject."""
        if subject_id not in self.subjects:
            return False

        subject = self.subjects[subject_id]
        original_count = len(subject.direct_permissions)

        subject.direct_permissions = [
            p for p in subject.direct_permissions
            if not (p.action == action and p.resource_pattern == resource_pattern)
        ]

        return len(subject.direct_permissions) < original_count

    def get_subject_permissions(self, subject_id: str) -> List[Permission]:
        """Get all effective permissions for a subject."""
        if subject_id not in self.subjects:
            return []

        subject = self.subjects[subject_id]
        permissions = list(subject.direct_permissions)

        for role_name in subject.roles:
            permissions.extend(self._get_role_permissions(role_name))

        return permissions

    def get_permission_summary(self, subject_id: str) -> str:
        """Get human-readable permission summary."""
        if subject_id not in self.subjects:
            return f"Unknown subject: {subject_id}"

        subject = self.subjects[subject_id]
        permissions = self.get_subject_permissions(subject_id)

        lines = [
            f"Subject: {subject.name} ({subject.id})",
            f"Type: {subject.subject_type}",
            f"Roles: {', '.join(subject.roles)}",
            "",
            f"Effective Permissions ({len(permissions)}):",
        ]

        # Group by action
        by_action: Dict[PermissionAction, List[Permission]] = {}
        for p in permissions:
            if p.action not in by_action:
                by_action[p.action] = []
            by_action[p.action].append(p)

        for action, perms in sorted(by_action.items(), key=lambda x: x[0].value):
            lines.append(f"  {action.value.upper()}:")
            for p in perms:
                conditions = f" (conditions: {list(p.conditions.keys())})" if p.conditions else ""
                lines.append(f"    - {p.resource_type.value}: {p.resource_pattern}{conditions}")

        return "\n".join(lines)


if __name__ == '__main__':
    # Self-test
    print("Permission Enforcer Self-Test")
    print("=" * 50)

    enforcer = PermissionEnforcer()

    # Register test subjects
    enforcer.register_subject(Subject(
        id="user1",
        name="Test User",
        subject_type="user",
        roles=["viewer"],
    ))

    enforcer.register_subject(Subject(
        id="agent1",
        name="Code Agent",
        subject_type="agent",
        roles=["agent"],
    ))

    enforcer.register_subject(Subject(
        id="admin1",
        name="Admin User",
        subject_type="user",
        roles=["admin"],
    ))

    test_cases = [
        # Viewer tests
        ("user1", PermissionAction.READ, ResourceType.FILE, "test.py", True),
        ("user1", PermissionAction.WRITE, ResourceType.FILE, "test.py", False),
        ("user1", PermissionAction.EXECUTE, ResourceType.TOOL, "Bash", False),

        # Agent tests
        ("agent1", PermissionAction.READ, ResourceType.FILE, "test.py", True),
        ("agent1", PermissionAction.WRITE, ResourceType.FILE, "test.py", True),
        ("agent1", PermissionAction.WRITE, ResourceType.FILE, "secret.key", False),  # Excluded
        ("agent1", PermissionAction.EXECUTE, ResourceType.TOOL, "Read", True),

        # Admin tests
        ("admin1", PermissionAction.DELETE, ResourceType.FILE, "anything.txt", True),
        ("admin1", PermissionAction.ADMIN, ResourceType.SYSTEM, "all", True),

        # Unknown subject
        ("unknown", PermissionAction.READ, ResourceType.FILE, "test.py", False),
    ]

    passed = 0
    failed = 0

    for subject_id, action, resource_type, resource_id, expected in test_cases:
        result = enforcer.is_allowed(subject_id, action, resource_type, resource_id)
        if result == expected:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"{status}: {subject_id} {action.value} {resource_type.value}:{resource_id} = {result} (expected {expected})")

    print()
    print("Permission Summary for 'agent1':")
    print(enforcer.get_permission_summary("agent1"))

    print()
    print(f"Results: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} tests failed"
    print('All PermissionEnforcer tests passed!')
