# GitMQ Cluster Enhancement - Implementation Roadmap

**Generated**: 2025-11-16
**Based On**: Multi-agent analysis (Research, Deep Thinker, Codex, Gemini perspectives)

---

## 🚨 PHASE 0: CRITICAL SECURITY FIXES (Week 1)

**MUST DO IMMEDIATELY - System is vulnerable**

### Task 0.1: Remove shell=True Vulnerability
**File**: `cluster-deployment/github_node_daemon.py:264`
**Current Code** (UNSAFE):
```python
result = subprocess.run(
    command,
    shell=True,  # ← CRITICAL VULNERABILITY
    capture_output=True,
    ...
)
```

**Fix**:
```python
# Use shlex.split() for safe argument parsing
import shlex
from pathlib import Path

def execute_code(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute code with mandatory sandboxing"""

    # Extract code payload
    code_payload = task_data.get("code_payload")
    if not code_payload:
        return {"status": "error", "error": "No code payload"}

    # Receive code to temp location
    temp_dir = Path(tempfile.mkdtemp(prefix="gitMQ_sandbox_"))
    code_file = temp_dir / code_payload['filename']

    try:
        # Write code
        transfer_mgr = CodeTransferManager()
        transfer_mgr.receive_code(code_payload, code_file)

        # MANDATORY: Use sandbox
        from intelligent_agents.sandbox_testing_environment import SandboxedTestingEnvironment

        sandbox = SandboxedTestingEnvironment()
        result = sandbox.run_tests(
            code_file=str(code_file),
            timeout_seconds=task_data.get('timeout_seconds', 300)
        )

        return {
            "status": "success" if result.status == TestStatus.PASSED else "failed",
            "test_result": asdict(result)
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
```

**Estimated Time**: 4 hours
**Blocker**: None

---

### Task 0.2: Add Cryptographic Message Signatures
**File**: `cluster-deployment/auth.py` (new)

**Implementation**:
```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64
import json

class MessageAuthenticator:
    """Sign and verify cluster messages"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.keys_dir = Path.home() / ".ssh" / "cluster-keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        # Load or generate keypair
        private_key_file = self.keys_dir / f"{node_id}_private.pem"
        if private_key_file.exists():
            self.private_key = self._load_private_key(private_key_file)
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            self._save_private_key(private_key_file, self.private_key)

        self.public_key = self.private_key.public_key()

        # Load public keys from other nodes
        self.public_keys = self._load_all_public_keys()

    def sign_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add signature to payload"""
        payload_copy = payload.copy()
        payload_copy.pop('_signature', None)  # Remove old signature

        payload_bytes = json.dumps(payload_copy, sort_keys=True).encode()
        signature = self.private_key.sign(payload_bytes)

        payload['_signature'] = base64.b64encode(signature).decode()
        payload['_signed_by'] = self.node_id
        payload['_signed_at'] = datetime.now().isoformat()

        return payload

    def verify_payload(self, payload: Dict[str, Any]) -> bool:
        """Verify payload signature"""
        if '_signature' not in payload:
            raise ValueError("Payload not signed")

        signed_by = payload.get('_signed_by')
        signature_b64 = payload.pop('_signature')
        payload.pop('_signed_by', None)
        payload.pop('_signed_at', None)

        signature = base64.b64decode(signature_b64)
        payload_bytes = json.dumps(payload, sort_keys=True).encode()

        public_key = self.public_keys.get(signed_by)
        if not public_key:
            raise ValueError(f"Unknown signing node: {signed_by}")

        try:
            public_key.verify(signature, payload_bytes)
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
```

**Integration**:
```python
# In github_node_daemon.py
from cluster_deployment.auth import MessageAuthenticator

class GitHubNodeDaemon:
    def __init__(self, ...):
        ...
        self.auth = MessageAuthenticator(self.node_id)

    def execute_task(self, task: Dict[str, Any]):
        # Verify signature before executing
        if not self.auth.verify_payload(task):
            logger.error(f"Invalid signature on task {task['task_id']}")
            return {"status": "error", "error": "Invalid signature"}

        # Execute
        return self._execute_task_impl(task)
```

**Estimated Time**: 6 hours
**Blocker**: Requires key distribution mechanism

---

### Task 0.3: Add Input Validation Schema
**File**: `cluster-deployment/payload_schema.py` (new)

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    HEALTH_CHECK = "health_check"
    CODE_EXECUTION = "code_execution"
    BUILD = "build"
    TEST = "test"
    APPROVAL_REQUIRED = "approval_required"

class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class ExecutionContext(BaseModel):
    """Execution constraints"""
    max_memory_mb: int = Field(default=1024, ge=128, le=32768)
    max_cpu_percent: float = Field(default=50.0, ge=1.0, le=100.0)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    sandbox_required: bool = True
    network_access: bool = False
    filesystem_access: List[str] = []
    required_packages: List[str] = []

class TaskPayload(BaseModel):
    """Validated task payload"""
    task_id: str = Field(..., regex="^[a-f0-9-]{36}$")  # UUID format
    type: TaskType
    timestamp: datetime
    source_node: str = Field(..., min_length=3, max_length=64)
    target_node: str = Field(..., min_length=3, max_length=64)
    priority: TaskPriority = TaskPriority.NORMAL

    execution_context: ExecutionContext = ExecutionContext()
    payload: Dict[str, Any]
    checksum: str = Field(..., regex="^sha256:[a-f0-9]{64}$")

    @validator('timestamp')
    def timestamp_not_future(cls, v):
        if v > datetime.now():
            raise ValueError("Timestamp cannot be in future")
        if v < datetime.now() - timedelta(hours=24):
            raise ValueError("Timestamp too old (>24h)")
        return v

    @validator('payload')
    def validate_payload_size(cls, v):
        import json
        size = len(json.dumps(v))
        if size > 10_000_000:  # 10MB
            raise ValueError(f"Payload too large: {size} bytes")
        return v

    def verify_checksum(self) -> bool:
        """Verify payload checksum"""
        import hashlib
        import json

        expected = self.checksum.replace("sha256:", "")
        actual = hashlib.sha256(
            json.dumps(self.payload, sort_keys=True).encode()
        ).hexdigest()

        return expected == actual

# Usage
def validate_task(task_json: dict) -> TaskPayload:
    """Validate task before execution"""
    try:
        task = TaskPayload(**task_json)

        if not task.verify_checksum():
            raise ValueError("Checksum verification failed")

        return task

    except ValidationError as e:
        logger.error(f"Task validation failed: {e}")
        raise
```

**Estimated Time**: 4 hours
**Blocker**: None

---

## ⚡ PHASE 1: PAYLOAD TRANSPORT MODEL (Week 2)

### Task 1.1: Code Transfer Manager
**File**: `cluster-deployment/code_transfer.py` (new)

**Features**:
- Base64 encoding for small files (<50KB)
- Git LFS for medium files (50KB-10MB)
- Chunked transfer for large files (>10MB)
- SHA256 checksums
- Dependency extraction

**Implementation**: See Codex analysis above

**Estimated Time**: 8 hours
**Blocker**: Requires Git LFS installation on all nodes

---

### Task 1.2: Payload Compression
**File**: `cluster-deployment/compression.py` (new)

**Implementation**:
```python
import gzip
import base64
import zstandard as zstd
from typing import Dict, Any

class PayloadCompressor:
    """Compress payloads before Git storage"""

    COMPRESSION_THRESHOLD = 10_000  # 10KB

    @staticmethod
    def compress(payload: Dict[str, Any], algorithm: str = "zstd") -> Dict[str, Any]:
        """Compress payload if > threshold"""
        import json

        payload_str = json.dumps(payload)
        size_bytes = len(payload_str.encode())

        if size_bytes < PayloadCompressor.COMPRESSION_THRESHOLD:
            return payload  # Too small to benefit

        if algorithm == "zstd":
            compressor = zstd.ZstdCompressor(level=3)
            compressed = compressor.compress(payload_str.encode())
        elif algorithm == "gzip":
            compressed = gzip.compress(payload_str.encode(), compresslevel=6)
        else:
            raise ValueError(f"Unknown compression: {algorithm}")

        compressed_b64 = base64.b64encode(compressed).decode()

        return {
            "_compressed": True,
            "_algorithm": algorithm,
            "_original_size": size_bytes,
            "_compressed_size": len(compressed),
            "_ratio": round(size_bytes / len(compressed), 2),
            "data": compressed_b64
        }

    @staticmethod
    def decompress(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Decompress payload"""
        if not payload.get('_compressed'):
            return payload

        algorithm = payload['_algorithm']
        compressed_b64 = payload['data']
        compressed = base64.b64decode(compressed_b64)

        if algorithm == "zstd":
            decompressor = zstd.ZstdDecompressor()
            decompressed = decompressor.decompress(compressed)
        elif algorithm == "gzip":
            decompressed = gzip.decompress(compressed)
        else:
            raise ValueError(f"Unknown compression: {algorithm}")

        import json
        return json.loads(decompressed.decode())
```

**Estimated Time**: 4 hours
**Blocker**: Requires `zstandard` package install

---

### Task 1.3: Chunked Transfer for Large Files
**File**: `cluster-deployment/chunked_transfer.py` (new)

**Implementation**: See Codex analysis above

**Estimated Time**: 6 hours
**Blocker**: None

---

## 🧠 PHASE 2: MEMORY SYNCHRONIZATION (Week 3)

### Task 2.1: Vector Clock Implementation
**File**: `cluster-deployment/vector_clock.py` (new)

**Implementation**:
```python
from typing import Dict
from dataclasses import dataclass, field

@dataclass
class VectorClock:
    """Lamport vector clock for causal ordering"""
    node_id: str
    clocks: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.node_id not in self.clocks:
            self.clocks[self.node_id] = 0

    def tick(self) -> Dict[str, int]:
        """Increment local clock"""
        self.clocks[self.node_id] += 1
        return self.clocks.copy()

    def merge(self, other_clocks: Dict[str, int]):
        """Merge vector clock from remote message"""
        for node, count in other_clocks.items():
            self.clocks[node] = max(self.clocks.get(node, 0), count)
        self.tick()

    def happened_before(self, other_clocks: Dict[str, int]) -> bool:
        """Check if this event happened before other"""
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        less_or_equal = all(
            self.clocks.get(node, 0) <= other_clocks.get(node, 0)
            for node in all_nodes
        )

        strictly_less = any(
            self.clocks.get(node, 0) < other_clocks.get(node, 0)
            for node in all_nodes
        )

        return less_or_equal and strictly_less

    def concurrent(self, other_clocks: Dict[str, int]) -> bool:
        """Check if events are concurrent (not causally related)"""
        return not (self.happened_before(other_clocks) or
                   self._other_happened_before(other_clocks))

    def _other_happened_before(self, other_clocks: Dict[str, int]) -> bool:
        """Check if other happened before this"""
        all_nodes = set(self.clocks.keys()) | set(other_clocks.keys())

        less_or_equal = all(
            other_clocks.get(node, 0) <= self.clocks.get(node, 0)
            for node in all_nodes
        )

        strictly_less = any(
            other_clocks.get(node, 0) < self.clocks.get(node, 0)
            for node in all_nodes
        )

        return less_or_equal and strictly_less

# Usage in daemon
class GitHubNodeDaemon:
    def __init__(self, ...):
        ...
        self.vector_clock = VectorClock(self.node_id)

    def submit_task(self, task_data):
        # Add vector clock to task
        task_data['vector_clock'] = self.vector_clock.tick()
        return task_data

    def receive_task(self, task):
        # Merge vector clock
        if 'vector_clock' in task:
            self.vector_clock.merge(task['vector_clock'])
```

**Estimated Time**: 4 hours
**Blocker**: None

---

### Task 2.2: CRDT-Based Memory Sync
**File**: `cluster-deployment/memory_sync.py` (new)

**Implementation**:
```python
from pycrdt import Doc, Map
import json

class ClusterMemorySync:
    """CRDT-based conflict-free memory synchronization"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.doc = Doc()
        self.shared_memories = self.doc.get("shared_memories", type=Map)

    def add_shared_memory(self, entity_name: str, observations: list):
        """Add memory that will sync across cluster"""
        self.shared_memories[entity_name] = {
            "observations": observations,
            "created_by": self.node_id,
            "timestamp": datetime.now().isoformat()
        }

    def get_sync_update(self) -> bytes:
        """Get binary update to push to GitHub"""
        return self.doc.get_update()

    def apply_remote_update(self, update_bytes: bytes):
        """Apply update from another node (automatic merge)"""
        self.doc.apply_update(update_bytes)

    def to_dict(self) -> dict:
        """Export current state"""
        return dict(self.shared_memories)

# GitHub integration
def push_memory_update(self):
    """Push memory update to GitHub"""
    sync = ClusterMemorySync(self.node_id)

    # Get CRDT update
    update = sync.get_sync_update()

    # Push to memory-sync branch
    self.git_write_binary(
        branch="memory-sync",
        file=f"{self.node_id}-{int(time.time())}.crdt",
        data=update
    )
    self.git_push()

def pull_memory_updates(self):
    """Pull and merge memory updates from cluster"""
    sync = ClusterMemorySync(self.node_id)

    # Fetch all CRDT files from other nodes
    files = self.git_list_files(branch="memory-sync")

    for file in files:
        if not file.startswith(self.node_id):  # Skip own updates
            update = self.git_read_binary(branch="memory-sync", file=file)
            sync.apply_remote_update(update)  # Conflict-free merge!

    # Now sync.to_dict() has all cluster memories
    return sync.to_dict()
```

**Estimated Time**: 8 hours
**Blocker**: Requires `pycrdt` package

---

### Task 2.3: Episodic Memory Consolidation
**File**: `cluster-deployment/memory_consolidation.py` (new)

**Features**:
- Auto-promote high-significance episodes to shared memory
- Cross-node episodic sync
- Pattern extraction across cluster

**Estimated Time**: 6 hours
**Blocker**: Requires Task 2.2

---

## 🤝 PHASE 3: HUMAN-IN-THE-LOOP FRAMEWORK (Week 4)

### Task 3.1: Risk Scoring Engine
**File**: `cluster-deployment/risk_assessment.py` (new)

**Implementation**:
```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RiskAssessment:
    risk_score: float  # 0.0 to 1.0
    risk_level: str    # "low" | "medium" | "high" | "critical"
    risk_factors: Dict[str, float]
    approval_tier: str  # "automatic" | "notification" | "approval_required" | "collaborative"

class RiskScoringEngine:
    """Calculate risk scores for cluster operations"""

    # Weight factors
    WEIGHTS = {
        "scope": 0.2,           # How much code/data affected
        "criticality": 0.3,     # System criticality
        "reversibility": 0.2,   # Can it be undone?
        "test_coverage": 0.15,  # Test coverage
        "novelty": 0.15         # Has this been done before?
    }

    def assess_task_risk(self, task: Dict[str, Any]) -> RiskAssessment:
        """Assess risk of executing a task"""

        risk_factors = {
            "scope": self._calculate_scope(task),
            "criticality": self._calculate_criticality(task),
            "reversibility": self._calculate_reversibility(task),
            "test_coverage": self._calculate_test_coverage(task),
            "novelty": self._calculate_novelty(task)
        }

        # Weighted risk score
        risk_score = sum(
            risk_factors[factor] * self.WEIGHTS[factor]
            for factor in risk_factors
        )

        # Classify risk level
        if risk_score < 0.2:
            risk_level = "low"
            approval_tier = "automatic"
        elif risk_score < 0.5:
            risk_level = "medium"
            approval_tier = "notification"
        elif risk_score < 0.8:
            risk_level = "high"
            approval_tier = "approval_required"
        else:
            risk_level = "critical"
            approval_tier = "collaborative"

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            approval_tier=approval_tier
        )

    def _calculate_scope(self, task: Dict[str, Any]) -> float:
        """Calculate scope risk (0.0-1.0)"""
        if task['type'] == 'code_execution':
            # Check code size
            code = task.get('payload', {}).get('code', '')
            if len(code) > 10000:
                return 0.9
            elif len(code) > 1000:
                return 0.5
            else:
                return 0.2
        return 0.3

    def _calculate_criticality(self, task: Dict[str, Any]) -> float:
        """Calculate criticality risk"""
        target = task.get('target_node', '')

        # Production systems are critical
        if 'prod' in target or 'orchestrator' in target:
            return 0.9
        elif 'builder' in target:
            return 0.5
        else:
            return 0.3

    def _calculate_reversibility(self, task: Dict[str, Any]) -> float:
        """Calculate reversibility risk"""
        # Destructive operations have high risk
        dangerous_keywords = ['delete', 'drop', 'remove', 'rm', 'truncate']

        task_str = str(task).lower()
        if any(kw in task_str for kw in dangerous_keywords):
            return 0.9

        return 0.2

    def _calculate_test_coverage(self, task: Dict[str, Any]) -> float:
        """Calculate test coverage risk"""
        # High risk if no tests
        if not task.get('payload', {}).get('tests_passed'):
            return 0.8
        return 0.1

    def _calculate_novelty(self, task: Dict[str, Any]) -> float:
        """Calculate novelty risk"""
        # Check if similar task executed before
        # This would query episodic memory
        return 0.5  # Placeholder
```

**Estimated Time**: 6 hours
**Blocker**: None

---

### Task 3.2: Arduino Approval Integration
**File**: `cluster-deployment/arduino_approval.py` (new)

**Implementation**:
```python
import sys
sys.path.append('/mnt/agentic-system/arduino-surface')
from arduino_interface import ArduinoInterface

class ArduinoApprovalController:
    """Human approval via Arduino hardware"""

    def __init__(self, port: str = "/dev/tty.usbmodem*"):
        self.arduino = ArduinoInterface(port)
        self.pending_approvals = {}

    def request_approval(self, task: Dict[str, Any], risk: RiskAssessment) -> str:
        """
        Request human approval via Arduino.

        Returns:
            "approved" | "denied" | "timeout"
        """
        # Display on LCD
        self.arduino.lcd_write(0, 0, "APPROVAL NEEDED")
        self.arduino.lcd_write(1, 0, f"{task['type'][:16]}")

        # Set LED color based on risk
        if risk.risk_level == "critical":
            self.arduino.set_led(0, 255, 0, 0)  # Red
        elif risk.risk_level == "high":
            self.arduino.set_led(0, 255, 165, 0)  # Orange
        else:
            self.arduino.set_led(0, 255, 255, 0)  # Yellow

        # Alert user
        self.arduino.buzzer_beep(2000, 200, 2)

        # Wait for button press (5 minute timeout)
        event = self.arduino.wait_event(timeout=300)

        if event and event['type'] == 'button_press':
            if event['button'] == 1:  # Button A = Approve
                self.arduino.set_led(0, 0, 255, 0)  # Green
                self.arduino.buzzer_beep(1000, 100, 1)
                return "approved"
            elif event['button'] == 2:  # Button B = Deny
                self.arduino.set_led(0, 255, 0, 0)  # Red
                self.arduino.buzzer_beep(500, 200, 3)
                return "denied"

        # Timeout
        self.arduino.set_led(0, 255, 0, 0)  # Red
        return "timeout"
```

**Estimated Time**: 4 hours
**Blocker**: Requires Arduino hardware (macOS nodes only)

---

### Task 3.3: Approval Workflow GitHub Integration
**File**: Update `github_node_daemon.py`

**Implementation**:
```python
async def execute_task_with_approval(self, task: Dict[str, Any]):
    """Execute task with optional human approval"""

    # Assess risk
    risk_engine = RiskScoringEngine()
    risk = risk_engine.assess_task_risk(task)

    logger.info(f"Task risk: {risk.risk_level} ({risk.risk_score:.2f})")

    if risk.approval_tier == "automatic":
        # Low risk - execute automatically
        return self.execute_task(task)

    elif risk.approval_tier == "notification":
        # Medium risk - notify but proceed
        self.notify_human(task, risk)
        return self.execute_task(task)

    elif risk.approval_tier in ["approval_required", "collaborative"]:
        # High risk - require approval
        approval = self.request_human_approval(task, risk)

        if approval == "approved":
            return self.execute_task(task)
        else:
            return {
                "status": "denied",
                "reason": f"Human approval {approval}",
                "risk_assessment": risk
            }

def request_human_approval(self, task: Dict[str, Any], risk: RiskAssessment) -> str:
    """Request approval via GitHub + Arduino"""

    # Post approval request to GitHub
    approval_data = {
        "task_id": task['task_id'],
        "task_type": task['type'],
        "risk": risk.__dict__,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }

    self.git_commit_json(
        branch="approvals/pending",
        file=f"{task['task_id']}.json",
        data=approval_data
    )

    # If this is orchestrator node with Arduino
    if self.node_id == "mac-studio" and self.has_arduino:
        arduino_ctrl = ArduinoApprovalController()
        return arduino_ctrl.request_approval(task, risk)

    # Otherwise, wait for orchestrator to respond
    return self.wait_for_approval_response(task['task_id'], timeout=300)
```

**Estimated Time**: 6 hours
**Blocker**: Requires Tasks 3.1 and 3.2

---

## 📊 PHASE 4: OBSERVABILITY & MONITORING (Week 5)

### Task 4.1: OpenTelemetry Integration
**File**: `cluster-deployment/tracing.py` (new)

**Implementation**: See Codex/Gemini analyses above

**Estimated Time**: 8 hours
**Blocker**: Requires OpenTelemetry collector setup

---

### Task 4.2: Distributed Metrics
**File**: `cluster-deployment/metrics.py` (new)

**Features**:
- Task execution latency (histogram)
- Queue depth (gauge)
- Success/failure rates (counter)
- Node health (gauge)

**Estimated Time**: 4 hours
**Blocker**: Requires Prometheus setup

---

### Task 4.3: Grafana Dashboard
**File**: `monitoring/dashboards/gitmq-cluster.json` (new)

**Panels**:
- Task flow visualization
- Node health matrix
- Error rate trends
- Latency percentiles

**Estimated Time**: 4 hours
**Blocker**: Requires Tasks 4.1 and 4.2

---

## 🔧 PHASE 5: FAILURE RECOVERY (Week 6)

### Task 5.1: Task Reaper
**File**: `cluster-deployment/failure_recovery.py` (new)

**Implementation**: See Codex analysis above

**Estimated Time**: 6 hours
**Blocker**: None

---

### Task 5.2: Dead Letter Queue
**File**: `cluster-deployment/dead_letter_queue.py` (new)

**Features**:
- Store unprocessable tasks
- Manual review interface
- Retry with modifications

**Estimated Time**: 4 hours
**Blocker**: None

---

### Task 5.3: Circuit Breaker
**File**: `cluster-deployment/circuit_breaker.py` (new)

**Implementation**:
```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker for node communication"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0

    def record_success(self):
        """Record successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            # Service recovered!
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def is_open(self) -> bool:
        """Check if circuit breaker is open (rejecting requests)"""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
                return False
            return True

        return False
```

**Estimated Time**: 4 hours
**Blocker**: None

---

## 🎯 PHASE 6: ADVANCED FEATURES (Week 7+)

### Task 6.1: Dependency Manager
**File**: `cluster-deployment/dependency_manager.py` (new)

**Implementation**: See Codex analysis

**Estimated Time**: 8 hours

---

### Task 6.2: Consensus Protocol
**File**: `cluster-deployment/consensus.py` (new)

**Implementation**: Simplified Raft or use existing library

**Estimated Time**: 16 hours

---

### Task 6.3: GitHub Webhooks
**File**: `cluster-deployment/webhook_server.py` (new)

**Reduces latency from 30s to <1s**

**Estimated Time**: 6 hours

---

## 📋 Summary Timeline

| Phase | Duration | Effort | Priority |
|-------|----------|--------|----------|
| Phase 0: Security Fixes | 1 week | 14 hours | P0 - CRITICAL |
| Phase 1: Transport Model | 1 week | 18 hours | P0 - CRITICAL |
| Phase 2: Memory Sync | 1 week | 18 hours | P1 - HIGH |
| Phase 3: Human-in-Loop | 1 week | 16 hours | P1 - HIGH |
| Phase 4: Observability | 1 week | 16 hours | P2 - MEDIUM |
| Phase 5: Failure Recovery | 1 week | 14 hours | P2 - MEDIUM |
| Phase 6: Advanced Features | 2+ weeks | 30+ hours | P3 - LOW |

**Total Estimated Effort**: ~126 hours (3+ weeks of full-time work)

---

## 🚀 Quick Start: Immediate Actions

**DO THIS TODAY:**

1. **Fix shell=True** (30 minutes)
   ```bash
   cd /mnt/agentic-system/cluster-deployment
   # Edit github_node_daemon.py line 264
   # Replace shell=True with proper argument parsing
   ```

2. **Add basic validation** (1 hour)
   ```bash
   pip3 install pydantic
   # Create payload_schema.py with TaskPayload model
   ```

3. **Create security audit log** (30 minutes)
   ```bash
   # Create audit-trail branch in GitHub
   git checkout -b audit-trail
   mkdir audit
   # Start logging all task executions
   ```

**Total time to basic security**: ~2 hours

---

## 📚 Research Papers to Implement

Based on Research Agent findings:

1. **Message Chains** (OOPSLA 2023) → Task 2.1 (Vector Clocks)
2. **SHIMI Memory Sync** (arXiv 2504.06135) → Task 2.2 (CRDT)
3. **CP-WBFT Consensus** (arXiv 2511.10400) → Task 6.2
4. **HULA Framework** (arXiv 2506.11009) → Task 3.1-3.3
5. **Zep Temporal Knowledge** (arXiv 2501.13956) → Future enhancement

---

## 🎓 Learning Resources

**To Implement CRDTs:**
- Library: `pycrdt` (Python CRDT library)
- Tutorial: https://crdt.tech/

**To Implement Vector Clocks:**
- Paper: "Time, Clocks, and the Ordering of Events" (Lamport 1978)
- Tutorial: https://en.wikipedia.org/wiki/Vector_clock

**To Implement Circuit Breakers:**
- Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Library: `pybreaker`

**To Implement OpenTelemetry:**
- Docs: https://opentelemetry.io/docs/instrumentation/python/
- Example: See Gemini analysis above

---

**Next Step**: Review this roadmap and decide which phase to start with. Recommend starting with Phase 0 (security) IMMEDIATELY.