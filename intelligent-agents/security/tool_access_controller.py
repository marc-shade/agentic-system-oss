"""
Tool Access Controller

Controls which tools are available to different agent roles.
Following Kai pattern: Least privilege principle.

Tool access levels:
1. Read-only - Can read files, search, query
2. Write - Can modify files and data
3. Execute - Can run commands and scripts
4. Admin - Full system access
5. Restricted - Limited to specific safe tools
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum


class AccessLevel(Enum):
    """Tool access levels from most to least restrictive."""
    RESTRICTED = 0   # Very limited safe tools
    READ_ONLY = 1    # Read operations only
    WRITE = 2        # Read + write operations
    EXECUTE = 3      # Read + write + execute
    ADMIN = 4        # Full access


class ToolCategory(Enum):
    """Categories of tools."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SEARCH = "search"
    WEB_FETCH = "web_fetch"
    COMMAND_EXEC = "command_exec"
    SYSTEM_INFO = "system_info"
    DATABASE = "database"
    API_CALL = "api_call"
    MEMORY = "memory"
    AGENT_SPAWN = "agent_spawn"
    ADMIN = "admin"


@dataclass
class ToolDefinition:
    """Defines a tool and its access requirements."""
    name: str
    category: ToolCategory
    description: str
    required_level: AccessLevel
    dangerous: bool = False
    requires_confirmation: bool = False
    allowed_patterns: List[str] = field(default_factory=list)  # e.g., file paths
    denied_patterns: List[str] = field(default_factory=list)


@dataclass
class AccessRequest:
    """Request to access a tool."""
    tool_name: str
    parameters: Dict[str, Any]
    requester_role: str
    context: Optional[str] = None


@dataclass
class AccessDecision:
    """Decision on tool access request."""
    allowed: bool
    tool_name: str
    requester_role: str
    reason: str
    required_level: AccessLevel
    actual_level: AccessLevel
    requires_confirmation: bool = False
    warnings: List[str] = field(default_factory=list)


class ToolAccessController:
    """Controls access to tools based on role and level."""

    # Default tool definitions
    DEFAULT_TOOLS: Dict[str, ToolDefinition] = {
        # File operations
        "Read": ToolDefinition(
            name="Read",
            category=ToolCategory.FILE_READ,
            description="Read file contents",
            required_level=AccessLevel.READ_ONLY,
            allowed_patterns=["*"],
            denied_patterns=["*.key", "*.pem", "*secret*", "*password*"],
        ),
        "Write": ToolDefinition(
            name="Write",
            category=ToolCategory.FILE_WRITE,
            description="Write file contents",
            required_level=AccessLevel.WRITE,
            requires_confirmation=True,
        ),
        "Edit": ToolDefinition(
            name="Edit",
            category=ToolCategory.FILE_WRITE,
            description="Edit file contents",
            required_level=AccessLevel.WRITE,
        ),
        "MultiEdit": ToolDefinition(
            name="MultiEdit",
            category=ToolCategory.FILE_WRITE,
            description="Edit multiple locations in file",
            required_level=AccessLevel.WRITE,
        ),

        # Search operations
        "Glob": ToolDefinition(
            name="Glob",
            category=ToolCategory.SEARCH,
            description="Find files by pattern",
            required_level=AccessLevel.READ_ONLY,
        ),
        "Grep": ToolDefinition(
            name="Grep",
            category=ToolCategory.SEARCH,
            description="Search file contents",
            required_level=AccessLevel.READ_ONLY,
        ),
        "WebSearch": ToolDefinition(
            name="WebSearch",
            category=ToolCategory.WEB_FETCH,
            description="Search the web",
            required_level=AccessLevel.READ_ONLY,
        ),
        "WebFetch": ToolDefinition(
            name="WebFetch",
            category=ToolCategory.WEB_FETCH,
            description="Fetch web content",
            required_level=AccessLevel.READ_ONLY,
        ),

        # Command execution
        "Bash": ToolDefinition(
            name="Bash",
            category=ToolCategory.COMMAND_EXEC,
            description="Execute bash commands",
            required_level=AccessLevel.EXECUTE,
            dangerous=True,
            requires_confirmation=True,
        ),

        # Agent operations
        "Task": ToolDefinition(
            name="Task",
            category=ToolCategory.AGENT_SPAWN,
            description="Spawn sub-agent tasks",
            required_level=AccessLevel.EXECUTE,
        ),

        # Memory operations
        "mcp__enhanced-memory__search_nodes": ToolDefinition(
            name="mcp__enhanced-memory__search_nodes",
            category=ToolCategory.MEMORY,
            description="Search memory",
            required_level=AccessLevel.READ_ONLY,
        ),
        "mcp__enhanced-memory__create_entities": ToolDefinition(
            name="mcp__enhanced-memory__create_entities",
            category=ToolCategory.MEMORY,
            description="Create memory entities",
            required_level=AccessLevel.WRITE,
        ),
    }

    # Default role access levels
    DEFAULT_ROLES: Dict[str, AccessLevel] = {
        "intern": AccessLevel.RESTRICTED,
        "researcher": AccessLevel.READ_ONLY,
        "engineer": AccessLevel.WRITE,
        "senior_engineer": AccessLevel.EXECUTE,
        "architect": AccessLevel.EXECUTE,
        "admin": AccessLevel.ADMIN,
        "qa": AccessLevel.READ_ONLY,
        "security": AccessLevel.READ_ONLY,
    }

    # Category access by level
    CATEGORY_ACCESS: Dict[AccessLevel, Set[ToolCategory]] = {
        AccessLevel.RESTRICTED: {
            ToolCategory.SEARCH,
        },
        AccessLevel.READ_ONLY: {
            ToolCategory.FILE_READ,
            ToolCategory.SEARCH,
            ToolCategory.WEB_FETCH,
            ToolCategory.SYSTEM_INFO,
        },
        AccessLevel.WRITE: {
            ToolCategory.FILE_READ,
            ToolCategory.FILE_WRITE,
            ToolCategory.SEARCH,
            ToolCategory.WEB_FETCH,
            ToolCategory.SYSTEM_INFO,
            ToolCategory.MEMORY,
            ToolCategory.DATABASE,
        },
        AccessLevel.EXECUTE: {
            ToolCategory.FILE_READ,
            ToolCategory.FILE_WRITE,
            ToolCategory.SEARCH,
            ToolCategory.WEB_FETCH,
            ToolCategory.SYSTEM_INFO,
            ToolCategory.MEMORY,
            ToolCategory.DATABASE,
            ToolCategory.COMMAND_EXEC,
            ToolCategory.API_CALL,
            ToolCategory.AGENT_SPAWN,
        },
        AccessLevel.ADMIN: set(ToolCategory),  # All categories
    }

    def __init__(
        self,
        tools: Optional[Dict[str, ToolDefinition]] = None,
        roles: Optional[Dict[str, AccessLevel]] = None
    ):
        """Initialize controller.

        Args:
            tools: Custom tool definitions (merged with defaults)
            roles: Custom role definitions (merged with defaults)
        """
        self.tools = dict(self.DEFAULT_TOOLS)
        if tools:
            self.tools.update(tools)

        self.roles = dict(self.DEFAULT_ROLES)
        if roles:
            self.roles.update(roles)

    def check_access(self, request: AccessRequest) -> AccessDecision:
        """Check if access to a tool is allowed.

        Args:
            request: The access request

        Returns:
            AccessDecision with result
        """
        tool_name = request.tool_name
        role = request.requester_role.lower()

        # Get role's access level
        if role not in self.roles:
            return AccessDecision(
                allowed=False,
                tool_name=tool_name,
                requester_role=role,
                reason=f"Unknown role: {role}",
                required_level=AccessLevel.ADMIN,
                actual_level=AccessLevel.RESTRICTED,
            )

        actual_level = self.roles[role]

        # Get tool definition
        if tool_name not in self.tools:
            # Unknown tool - allow if admin, deny otherwise
            if actual_level == AccessLevel.ADMIN:
                return AccessDecision(
                    allowed=True,
                    tool_name=tool_name,
                    requester_role=role,
                    reason="Admin access to unknown tool",
                    required_level=AccessLevel.ADMIN,
                    actual_level=actual_level,
                    warnings=["Unknown tool - not in access control list"],
                )
            else:
                return AccessDecision(
                    allowed=False,
                    tool_name=tool_name,
                    requester_role=role,
                    reason=f"Unknown tool: {tool_name}",
                    required_level=AccessLevel.ADMIN,
                    actual_level=actual_level,
                )

        tool = self.tools[tool_name]
        warnings = []

        # Check access level
        if actual_level.value < tool.required_level.value:
            return AccessDecision(
                allowed=False,
                tool_name=tool_name,
                requester_role=role,
                reason=f"Insufficient access level. Required: {tool.required_level.value}, has: {actual_level.value}",
                required_level=tool.required_level,
                actual_level=actual_level,
            )

        # Check category access
        allowed_categories = self.CATEGORY_ACCESS.get(actual_level, set())
        if tool.category not in allowed_categories:
            return AccessDecision(
                allowed=False,
                tool_name=tool_name,
                requester_role=role,
                reason=f"Category {tool.category.value} not allowed for level {actual_level.value}",
                required_level=tool.required_level,
                actual_level=actual_level,
            )

        # Check for dangerous tool
        if tool.dangerous:
            warnings.append(f"Tool '{tool_name}' is marked as dangerous")

        # Check parameter patterns
        pattern_warnings = self._check_patterns(tool, request.parameters)
        if pattern_warnings:
            for w in pattern_warnings:
                if w.startswith("DENIED:"):
                    return AccessDecision(
                        allowed=False,
                        tool_name=tool_name,
                        requester_role=role,
                        reason=w,
                        required_level=tool.required_level,
                        actual_level=actual_level,
                    )
                warnings.append(w)

        return AccessDecision(
            allowed=True,
            tool_name=tool_name,
            requester_role=role,
            reason="Access granted",
            required_level=tool.required_level,
            actual_level=actual_level,
            requires_confirmation=tool.requires_confirmation,
            warnings=warnings,
        )

    def _check_patterns(
        self,
        tool: ToolDefinition,
        parameters: Dict[str, Any]
    ) -> List[str]:
        """Check parameters against allowed/denied patterns."""
        warnings = []

        # Get file_path or similar parameter
        path_params = ["file_path", "path", "directory", "command"]
        target = None
        for param in path_params:
            if param in parameters:
                target = str(parameters[param])
                break

        if not target:
            return []

        target_lower = target.lower()

        # Check denied patterns
        for pattern in tool.denied_patterns:
            pattern_lower = pattern.lower().replace("*", "")
            if pattern_lower in target_lower:
                warnings.append(f"DENIED: Pattern '{pattern}' matches '{target}'")

        return warnings

    def is_allowed(self, tool_name: str, role: str) -> bool:
        """Quick check if tool is allowed for role."""
        request = AccessRequest(
            tool_name=tool_name,
            parameters={},
            requester_role=role
        )
        decision = self.check_access(request)
        return decision.allowed

    def get_allowed_tools(self, role: str) -> List[str]:
        """Get list of tools allowed for a role."""
        allowed = []
        for tool_name in self.tools:
            if self.is_allowed(tool_name, role):
                allowed.append(tool_name)
        return sorted(allowed)

    def get_denied_tools(self, role: str) -> List[str]:
        """Get list of tools denied for a role."""
        denied = []
        for tool_name in self.tools:
            if not self.is_allowed(tool_name, role):
                denied.append(tool_name)
        return sorted(denied)

    def add_tool(self, tool: ToolDefinition) -> None:
        """Add a tool definition."""
        self.tools[tool.name] = tool

    def add_role(self, role: str, level: AccessLevel) -> None:
        """Add a role with access level."""
        self.roles[role.lower()] = level

    def get_role_summary(self, role: str) -> str:
        """Get summary of role's access."""
        if role.lower() not in self.roles:
            return f"Unknown role: {role}"

        level = self.roles[role.lower()]
        allowed = self.get_allowed_tools(role)
        denied = self.get_denied_tools(role)

        lines = [
            f"Role: {role}",
            f"Access Level: {level.name} ({level.value})",
            "",
            f"Allowed Tools ({len(allowed)}):",
            f"  {', '.join(allowed)}",
            "",
            f"Denied Tools ({len(denied)}):",
            f"  {', '.join(denied)}",
        ]
        return "\n".join(lines)


if __name__ == '__main__':
    # Self-test
    print("Tool Access Controller Self-Test")
    print("=" * 50)

    controller = ToolAccessController()

    test_cases = [
        # Intern - restricted
        ("Read", "intern", False),
        ("Glob", "intern", True),  # Search is allowed
        ("Bash", "intern", False),

        # Researcher - read only
        ("Read", "researcher", True),
        ("Write", "researcher", False),
        ("Glob", "researcher", True),
        ("Bash", "researcher", False),

        # Engineer - write
        ("Read", "engineer", True),
        ("Write", "engineer", True),
        ("Edit", "engineer", True),
        ("Bash", "engineer", False),

        # Senior engineer - execute
        ("Bash", "senior_engineer", True),
        ("Task", "senior_engineer", True),

        # Admin - all
        ("Bash", "admin", True),
        ("unknown_tool", "admin", True),
    ]

    passed = 0
    failed = 0

    for tool, role, expected in test_cases:
        result = controller.is_allowed(tool, role)
        if result == expected:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"{status}: {role} + {tool} = {result} (expected {expected})")

    print()
    print("Role Summary for 'researcher':")
    print(controller.get_role_summary("researcher"))

    print()
    print(f"Results: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} tests failed"
    print('All ToolAccessController tests passed!')
