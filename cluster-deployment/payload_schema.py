#!/usr/bin/env python3
"""
Payload Schema Validation for GitMQ Messages
==============================================

Defines and validates all message types exchanged between cluster nodes.

Benefits:
- Type safety: Catch errors before execution
- Documentation: Schema serves as API contract
- Versioning: Supports schema evolution
- Security: Prevents malformed/malicious payloads

Message Types:
- TaskPayload: General task execution requests
- HealthCheckPayload: Node health verification
- CodeExecutionPayload: Code execution with sandboxing
- BuildPayload: Build/compilation tasks
- MemorySyncPayload: Memory synchronization
- ResultPayload: Task execution results

Usage:
    from payload_schema import TaskPayload, validate_payload

    # Create and validate
    task = TaskPayload(
        task_id="uuid-here",
        type="code_execution",
        source_node="macpro51",
        target_node="mac-studio",
        payload={"code": "print('hello')"}
    )

    # Validate untrusted data
    try:
        task = validate_payload(untrusted_dict, TaskPayload)
    except ValidationError as e:
        logger.error(f"Invalid payload: {e}")
"""

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


# ============================================================================
# Enumerations
# ============================================================================

class TaskType(str, Enum):
    """Valid task types for cluster execution."""
    HEALTH_CHECK = "health_check"
    CODE_EXECUTION = "code_execution"
    BUILD = "build"
    TEST = "test"
    MEMORY_SYNC = "memory_sync"
    DEPLOYMENT = "deployment"
    BENCHMARK = "benchmark"


class ExecutionMode(str, Enum):
    """Code execution isolation modes."""
    SANDBOXED = "sandboxed"  # Full container isolation (required)
    VALIDATED = "validated"  # Schema validation + restricted subprocess
    TRUSTED = "trusted"      # No sandboxing (only for system tasks)


class Priority(int, Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


# ============================================================================
# Base Models
# ============================================================================

class ExecutionContext(BaseModel):
    """Execution context and constraints for tasks."""
    model_config = ConfigDict(extra="forbid")

    mode: ExecutionMode = ExecutionMode.SANDBOXED
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    max_memory_mb: int = Field(default=512, ge=64, le=8192)
    max_cpu_percent: int = Field(default=80, ge=10, le=100)
    working_directory: Optional[str] = Field(default=None, max_length=500)
    environment_vars: Dict[str, str] = Field(default_factory=dict)

    @field_validator('working_directory')
    @classmethod
    def validate_working_directory(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        # Prevent directory traversal attacks
        if '..' in v or v.startswith('/etc') or v.startswith('/root'):
            raise ValueError(f"Invalid working directory: {v}")

        return v

    @field_validator('environment_vars')
    @classmethod
    def validate_env_vars(cls, v: Dict[str, str]) -> Dict[str, str]:
        # Block sensitive env vars from being overridden
        blocked = {'PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'USER'}

        for key in v.keys():
            if key in blocked:
                raise ValueError(f"Cannot override protected environment variable: {key}")

        return v


class VectorClock(BaseModel):
    """Lamport vector clock for causal ordering."""
    model_config = ConfigDict(extra="allow")

    clocks: Dict[str, int] = Field(default_factory=dict)

    def increment(self, node_id: str) -> "VectorClock":
        """Increment this node's clock."""
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1
        return self

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Merge with another vector clock."""
        for node, count in other.clocks.items():
            self.clocks[node] = max(self.clocks.get(node, 0), count)
        return self


# ============================================================================
# Payload Models
# ============================================================================

class TaskPayload(BaseModel):
    """
    Base task payload for all cluster tasks.

    All messages exchanged between nodes must conform to this schema.
    """
    model_config = ConfigDict(extra="forbid")

    # Identity
    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
    )
    type: TaskType

    # Routing
    source_node: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-z0-9\-]+$")
    target_node: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-z0-9\-]+$")

    # Timing
    timestamp: datetime = Field(default_factory=datetime.now)
    vector_clock: VectorClock = Field(default_factory=VectorClock)

    # Causality tracking
    causality_deps: List[str] = Field(default_factory=list)
    parent_task_id: Optional[str] = None

    # Priority
    priority: Priority = Priority.NORMAL

    # Execution context
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)

    # Task-specific data
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Integrity
    checksum: Optional[str] = Field(default=None, pattern=r"^sha256:[a-f0-9]{64}$")

    @field_validator('timestamp')
    @classmethod
    def timestamp_not_future(cls, v: datetime) -> datetime:
        """Prevent timestamp forgery."""
        if v > datetime.now():
            raise ValueError("Timestamp cannot be in the future")
        return v

    @field_validator('causality_deps')
    @classmethod
    def validate_causality_deps(cls, v: List[str]) -> List[str]:
        """Validate all dependency IDs are UUIDs."""
        uuid_pattern = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")

        for dep_id in v:
            if not uuid_pattern.match(dep_id):
                raise ValueError(f"Invalid task ID in causality_deps: {dep_id}")

        return v

    @model_validator(mode='after')
    def compute_checksum(self) -> 'TaskPayload':
        """Compute payload checksum if not provided."""
        if self.checksum is None:
            payload_json = json.dumps(self.payload, sort_keys=True)
            hash_obj = hashlib.sha256(payload_json.encode('utf-8'))
            self.checksum = f"sha256:{hash_obj.hexdigest()}"

        return self

    def verify_checksum(self) -> bool:
        """Verify payload integrity."""
        if not self.checksum:
            return False

        expected_hash = self.checksum.split(":", 1)[1]
        payload_json = json.dumps(self.payload, sort_keys=True)
        actual_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()

        return expected_hash == actual_hash


class CodeExecutionPayload(BaseModel):
    """
    Payload for code execution tasks.

    SECURITY: All code execution MUST use sandboxing.
    """
    model_config = ConfigDict(extra="forbid")

    # Code delivery
    code: Optional[str] = Field(default=None, max_length=50_000)  # Inline code (max 50KB)
    code_file: Optional[str] = None  # Git LFS path for larger files
    code_language: str = Field(default="python", pattern=r"^(python|bash|javascript|typescript|rust|go)$")

    # Dependencies
    dependencies: List[str] = Field(default_factory=list)
    requirements_file: Optional[str] = None  # Git LFS path

    # Execution
    entry_point: str = Field(default="main.py")
    arguments: List[str] = Field(default_factory=list)

    # Validation
    expected_exit_code: int = Field(default=0, ge=0, le=255)
    expected_output_pattern: Optional[str] = None

    @field_validator('arguments')
    @classmethod
    def validate_arguments(cls, v: List[str]) -> List[str]:
        """Prevent shell injection via arguments."""
        dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r']

        for arg in v:
            for char in dangerous_chars:
                if char in arg:
                    raise ValueError(f"Argument contains dangerous character '{char}': {arg}")

        return v

    @model_validator(mode='after')
    def validate_code_delivery(self) -> 'CodeExecutionPayload':
        """Ensure code is provided via exactly one method."""
        if self.code is None and self.code_file is None:
            raise ValueError("Must provide either 'code' or 'code_file'")

        if self.code is not None and self.code_file is not None:
            raise ValueError("Cannot provide both 'code' and 'code_file'")

        return self


class BuildPayload(BaseModel):
    """Payload for build/compilation tasks."""
    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(..., min_length=1, max_length=128)
    build_type: str = Field(default="release", pattern=r"^(debug|release)$")
    targets: List[str] = Field(default_factory=lambda: ["default"])
    build_args: Dict[str, str] = Field(default_factory=dict)


class MemorySyncPayload(BaseModel):
    """Payload for memory synchronization between nodes."""
    model_config = ConfigDict(extra="forbid")

    sync_type: str = Field(..., pattern=r"^(full|incremental|selective)$")
    entity_ids: List[int] = Field(default_factory=list)
    crdt_update: Optional[str] = None  # Base64-encoded CRDT update
    vector_clock: VectorClock = Field(default_factory=VectorClock)


class ResultPayload(BaseModel):
    """Payload for task execution results."""
    model_config = ConfigDict(extra="forbid")

    # Reference original task
    task_id: str = Field(..., pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")
    executing_node: str = Field(..., min_length=3, max_length=64)

    # Outcome
    status: str = Field(..., pattern=r"^(success|error|timeout|cancelled)$")
    exit_code: Optional[int] = Field(default=None, ge=0, le=255)

    # Output
    stdout: str = Field(default="", max_length=100_000)  # Limit 100KB
    stderr: str = Field(default="", max_length=100_000)
    error_message: Optional[str] = Field(default=None, max_length=10_000)

    # Performance metrics
    execution_time_ms: Optional[float] = Field(default=None, ge=0)
    memory_usage_mb: Optional[float] = Field(default=None, ge=0)
    cpu_usage_percent: Optional[float] = Field(default=None, ge=0, le=100)

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime = Field(default_factory=datetime.now)

    # Artifacts
    artifacts: List[str] = Field(default_factory=list)  # Git LFS paths

    @model_validator(mode='after')
    def validate_timing(self) -> 'ResultPayload':
        """Ensure completed_at >= started_at."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")

        return self


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_payload(data: Dict[str, Any], model_class: type[BaseModel]) -> BaseModel:
    """
    Validate untrusted data against a schema.

    Args:
        data: Untrusted dictionary
        model_class: Pydantic model to validate against

    Returns:
        Validated model instance

    Raises:
        ValidationError: If data doesn't match schema
    """
    return model_class.model_validate(data)


def sanitize_payload(payload: BaseModel) -> Dict[str, Any]:
    """
    Convert payload to safe dictionary for transmission.

    Args:
        payload: Validated Pydantic model

    Returns:
        JSON-serializable dictionary
    """
    return payload.model_dump(mode='json', exclude_none=True)


# ============================================================================
# Demo Usage
# ============================================================================

if __name__ == "__main__":
    print("GitMQ Payload Schema Validation Demo")
    print("=" * 60)

    # Demo 1: Create and validate a task
    print("\n1. Creating a code execution task...")
    task = TaskPayload(
        type=TaskType.CODE_EXECUTION,
        source_node="macpro51",
        target_node="mac-studio",
        priority=Priority.HIGH,
        payload={
            "code": "print('Hello from GitMQ cluster')",
            "code_language": "python",
            "dependencies": ["requests>=2.31.0"]
        }
    )

    print(f"   Task ID: {task.task_id}")
    print(f"   Checksum: {task.checksum}")
    print(f"   Valid: {task.verify_checksum()}")

    # Demo 2: Validate untrusted data
    print("\n2. Validating untrusted payload...")
    untrusted = {
        "type": "health_check",
        "source_node": "macbook-air",
        "target_node": "macpro51",
        "payload": {"check_disk": True}
    }

    try:
        validated_task = validate_payload(untrusted, TaskPayload)
        print(f"   ✓ Valid task: {validated_task.task_id}")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")

    # Demo 3: Detect malicious payload
    print("\n3. Detecting malicious payload...")
    malicious = {
        "type": "code_execution",
        "source_node": "evil-node",
        "target_node": "macpro51",
        "payload": {
            "code": "import os; os.system('rm -rf /')",  # Dangerous code
            "arguments": ["--flag; cat /etc/passwd"]  # Shell injection attempt
        },
        "timestamp": "2099-01-01T00:00:00Z"  # Future timestamp
    }

    try:
        malicious_task = validate_payload(malicious, TaskPayload)
        print(f"   ✗ SECURITY FAILURE: Malicious task accepted!")
    except Exception as e:
        print(f"   ✓ Security working: {e}")

    # Demo 4: Code execution payload
    print("\n4. Code execution payload with dependencies...")
    code_payload = CodeExecutionPayload(
        code="import requests\nprint(requests.__version__)",
        code_language="python",
        dependencies=["requests>=2.31.0", "numpy>=1.24.0"],
        entry_point="main.py",
        expected_exit_code=0
    )

    print(f"   Language: {code_payload.code_language}")
    print(f"   Dependencies: {len(code_payload.dependencies)}")

    # Demo 5: Result payload
    print("\n5. Task result payload...")
    result = ResultPayload(
        task_id=task.task_id,
        executing_node="mac-studio",
        status="success",
        exit_code=0,
        stdout="Hello from GitMQ cluster\n",
        execution_time_ms=42.5,
        memory_usage_mb=15.2,
        cpu_usage_percent=8.3
    )

    print(f"   Status: {result.status}")
    print(f"   Execution time: {result.execution_time_ms}ms")
    print(f"   Memory: {result.memory_usage_mb}MB")

    print("\n" + "=" * 60)
    print("All demonstrations complete!")
