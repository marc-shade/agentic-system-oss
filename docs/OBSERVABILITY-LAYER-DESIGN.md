# AGI Observability Layer Design
## Solving the "Who Watches the Watchers" Problem

**Status**: Design Proposal
**Date**: 2025-12-03
**Based on**: Research synthesis from OpenTelemetry GenAI SIG, meta-learning safety papers, circuit breaker patterns

---

## 1. Problem Statement

On 2025-12-02 at 20:35:16, the AGI self-evaluation system detected a regression (44.6% execution time increase) and automatically triggered a `git reset --hard HEAD~1`. This safety mechanism inadvertently destroyed critical infrastructure:

- `memory-consolidation-daemon.py` - deleted (untracked file)
- Session memory integration - broken

**Root Cause**: The safety system designed to prevent regressions became the source of failure. Classic recursive safety problem.

**Key Insight**: "Quis custodiet ipsos custodes?" - Who watches the watchers?

---

## 2. Research Findings

### 2.1 OpenTelemetry AI Agent Observability (2025)

The OpenTelemetry GenAI SIG is defining semantic conventions for AI agents:

- **Agent Applications**: Individual AI-driven entities performing autonomous tasks
- **Agent Frameworks**: Infrastructure for developing and deploying agents
- **Key Principle**: Telemetry serves dual purposes - diagnostics AND continuous improvement feedback loops

**Recommendation**: Adopt OpenTelemetry semantic conventions for all AGI loop operations.

### 2.2 Circuit Breaker Pattern (Bansal 2024, 703 citations)

Circuit breakers prevent cascading failures through three states:

```
CLOSED → (failures exceed threshold) → OPEN → (timeout) → HALF-OPEN → (test succeeds) → CLOSED
                                         ↑                     |
                                         └── (test fails) ─────┘
```

**Application to AGI**: Self-evaluation rollback should have a circuit breaker that prevents repeated destructive operations.

### 2.3 Meta-Learning Safety Validation (SAVME 2023)

The SAVME paper introduces Bayesian meta-learning for safety validation:
- Learn distributions over parameters prone to triggering failures
- Multi-armed bandit framework for selecting validation strategies
- 18x speedup compared to traditional methods

**Application to AGI**: Learn which modification types are likely to regress, adjust confidence thresholds dynamically.

### 2.4 Constrained Meta-Reinforcement Learning (Cho & Sun 2023)

Key insight: Safety constraints must be differentiable and integrated into the learning loop, not just post-hoc checks.

**Application to AGI**: Rollback decisions should consider collateral damage (untracked files) as part of the cost function.

### 2.5 Runtime State Verification (Gomez Rivera & Tosh 2022)

Self-configurable runtime integrity through reinforcement learning enables:
- Fine-grained continuous runtime state assurance
- Detection of false sequential attacks

**Application to AGI**: Independent runtime verification of self-evaluation decisions before execution.

---

## 3. Proposed Architecture

### 3.1 Three-Layer Observability Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: IMMUTABLE AUDIT                     │
│  (Write-Once Log, External Storage, Cannot be Modified by AGI)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LAYER 2: CIRCUIT BREAKER GUARDIAN               │
│  (Independent Process, Veto Power over Destructive Operations)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: AGI OPERATIONS                      │
│     (Self-Evaluation, Rollback, Memory Consolidation, etc.)     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

#### Layer 1: AGI Operations (Existing)
- Self-evaluation system
- Darwin Godel Machine
- Memory consolidation daemon
- Autonomous improvement loops

**Enhancement**: All operations emit OpenTelemetry spans with semantic conventions.

#### Layer 2: Circuit Breaker Guardian (NEW)
- **Independent process** - not controlled by AGI loop
- **Veto authority** - can block destructive operations
- **Pre-action checks**:
  - Untracked file inventory
  - Confidence threshold validation
  - Rate limiting on destructive ops
- **State machine**: CLOSED → OPEN → HALF-OPEN

#### Layer 3: Immutable Audit Layer (NEW)
- **Write-once storage** - append-only log
- **External to AGI filesystem** - stored on separate mount/cloud
- **Cryptographic integrity** - hash chains prevent tampering
- **Records**:
  - All self-evaluation decisions
  - All rollback operations
  - Pre/post state snapshots
  - Untracked file manifests

---

## 4. Detailed Component Designs

### 4.1 Pre-Rollback Safety Protocol

```python
class SafeRollback:
    """Enhanced rollback with collateral damage prevention."""

    def execute_rollback(self, reason: str, confidence: float) -> bool:
        # Step 1: Guardian approval
        if not self.guardian.approve_destructive_op("rollback", confidence):
            self.audit.log("ROLLBACK_BLOCKED", reason, confidence)
            return False

        # Step 2: Inventory untracked files
        untracked = self.git.list_untracked()
        critical_patterns = ["daemon.py", "mcp", "memory", "consolidation"]
        critical_files = [f for f in untracked if any(p in f for p in critical_patterns)]

        if critical_files:
            # Step 3: Stash critical untracked files
            self.git.stash(include_untracked=True)
            self.audit.log("STASHED_CRITICAL", critical_files)

        # Step 4: Create pre-rollback snapshot
        snapshot_id = self.audit.create_snapshot()

        # Step 5: Execute rollback
        self.git.reset("--hard", "HEAD~1")

        # Step 6: Restore critical files from stash
        if critical_files:
            self.git.stash_pop()
            self.audit.log("RESTORED_CRITICAL", critical_files)

        # Step 7: Audit completion
        self.audit.log("ROLLBACK_COMPLETE", snapshot_id, reason)
        return True
```

### 4.2 Circuit Breaker Guardian

```python
class CircuitBreakerGuardian:
    """Independent safety guardian with veto power."""

    FAILURE_THRESHOLD = 3
    RECOVERY_TIMEOUT = 300  # seconds
    MIN_CONFIDENCE_DESTRUCTIVE = 0.7  # 70% minimum for destructive ops

    def __init__(self):
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure = None
        self.blocked_operations = []

    def approve_destructive_op(self, op_type: str, confidence: float) -> bool:
        # Check circuit state
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.RECOVERY_TIMEOUT:
                self.state = "HALF_OPEN"
            else:
                return False  # Block all destructive ops

        # Check confidence threshold
        if confidence < self.MIN_CONFIDENCE_DESTRUCTIVE:
            self.record_failure(f"Low confidence: {confidence}")
            return False

        # Check rate limiting (max 1 destructive op per 60s)
        recent_ops = self.get_recent_destructive_ops(60)
        if len(recent_ops) > 0:
            return False

        # Half-open test
        if self.state == "HALF_OPEN":
            # Allow one operation as a test
            self.state = "CLOSED"
            self.failure_count = 0

        return True

    def record_failure(self, reason: str):
        self.failure_count += 1
        self.last_failure = time.time()

        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = "OPEN"
            self.alert("Circuit OPEN - blocking destructive operations")
```

### 4.3 OpenTelemetry Instrumentation

```python
from opentelemetry import trace
from opentelemetry.semconv.ai import GenAISpanAttributes

tracer = trace.get_tracer("agi.self_evaluation")

class InstrumentedSelfEvaluation:
    """Self-evaluation with full OpenTelemetry tracing."""

    def evaluate_modification(self, modification: str) -> Decision:
        with tracer.start_as_current_span("agi.evaluate_modification") as span:
            # Standard GenAI attributes
            span.set_attribute("gen_ai.system", "agi_self_evaluation")
            span.set_attribute("gen_ai.operation.name", "evaluate")

            # Custom AGI attributes
            span.set_attribute("agi.modification.description", modification)
            span.set_attribute("agi.baseline.snapshot_id", self.baseline_id)

            # Measure performance
            baseline = self.get_baseline()
            current = self.measure_current()

            span.set_attribute("agi.baseline.execution_time_ms", baseline.exec_time)
            span.set_attribute("agi.current.execution_time_ms", current.exec_time)
            span.set_attribute("agi.delta.execution_time_percent",
                              (current.exec_time - baseline.exec_time) / baseline.exec_time * 100)

            # Make decision
            decision = self.compare(baseline, current)

            span.set_attribute("agi.decision", decision.action)
            span.set_attribute("agi.decision.confidence", decision.confidence)
            span.set_attribute("agi.decision.reasoning", decision.reasoning)

            # Add event for audit
            span.add_event("evaluation_complete", {
                "decision": decision.action,
                "confidence": decision.confidence,
                "untracked_files_at_risk": len(self.list_untracked())
            })

            return decision
```

### 4.4 Immutable Audit Log

```python
import hashlib
import json
from pathlib import Path

class ImmutableAuditLog:
    """Append-only audit log with cryptographic integrity."""

    def __init__(self, log_path: str = "/var/log/agi-audit/"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.chain_file = self.log_path / "hash_chain.json"
        self.last_hash = self._load_last_hash()

    def log(self, event_type: str, *args, **kwargs):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": {"args": args, "kwargs": kwargs},
            "previous_hash": self.last_hash
        }

        # Compute hash of entry
        entry_json = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["hash"] = entry_hash

        # Write to date-based log file (append-only)
        date_file = self.log_path / f"{datetime.utcnow().date()}.jsonl"
        with open(date_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Update chain
        self.last_hash = entry_hash
        self._save_last_hash()

        return entry_hash

    def verify_integrity(self) -> bool:
        """Verify the entire audit chain hasn't been tampered with."""
        previous_hash = None

        for log_file in sorted(self.log_path.glob("*.jsonl")):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line)

                    # Verify chain
                    if entry["previous_hash"] != previous_hash:
                        return False

                    # Verify hash
                    stored_hash = entry.pop("hash")
                    computed_hash = hashlib.sha256(
                        json.dumps(entry, sort_keys=True).encode()
                    ).hexdigest()

                    if computed_hash != stored_hash:
                        return False

                    previous_hash = stored_hash

        return True
```

---

## 5. Implementation Plan

### Phase 1: Immediate Safety (Week 1)
1. Add `git stash --include-untracked` before any rollback
2. Raise minimum confidence threshold to 70% for destructive ops
3. Add untracked file inventory to pre-rollback checks
4. Track all critical files in git

### Phase 2: Circuit Breaker Guardian (Week 2-3)
1. Implement CircuitBreakerGuardian as independent systemd service
2. Add Unix socket IPC for AGI → Guardian communication
3. Implement rate limiting on destructive operations
4. Add alerting when circuit opens

### Phase 3: OpenTelemetry Integration (Week 3-4)
1. Instrument self-evaluation system with OTel traces
2. Add custom AGI semantic conventions
3. Export to existing Prometheus/Grafana stack
4. Create AGI-specific dashboards

### Phase 4: Immutable Audit Layer (Week 4-5)
1. Deploy append-only audit log to separate storage
2. Implement hash chain integrity
3. Add pre/post rollback snapshots
4. Create integrity verification cron job

### Phase 5: Meta-Learning Safety (Future)
1. Train model on historical rollback decisions
2. Learn which modification types are regression-prone
3. Dynamic confidence threshold adjustment
4. Proactive file protection suggestions

---

## 6. Key Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `agi.rollback.count` | Number of rollbacks | >3 per hour |
| `agi.rollback.confidence` | Decision confidence | <0.5 |
| `agi.circuit.state` | Guardian circuit state | OPEN |
| `agi.untracked.critical` | Critical untracked files | >0 |
| `agi.audit.integrity` | Hash chain validity | false |
| `agi.stash.restores` | Files restored from stash | >0 |

---

## 7. References

1. [OpenTelemetry AI Agent Observability](https://opentelemetry.io/blog/2025/ai-agent-observability/) - GenAI SIG semantic conventions
2. [LLM Observability with OpenTelemetry](https://opentelemetry.io/blog/2024/llm-observability/) - Implementation patterns
3. Bansal (2024) "Circuit Breaker" - Microservices resilience patterns
4. Schlichting et al. (2023) "SAVME: Efficient Safety Validation for Autonomous Systems Using Meta-Learning" - Bayesian safety validation
5. Cho & Sun (2023) "Constrained Meta-Reinforcement Learning for Adaptable Safety Guarantee" - Differentiable safety constraints
6. Dev et al. (2024) "Building Guardrails in AI Systems with Threat Modeling" - AI threat analysis frameworks

---

## 8. Conclusion

The incident on 2025-12-02 revealed a fundamental gap in our observability architecture: the safety system itself was not being watched. By implementing a three-layer architecture (AGI Operations → Circuit Breaker Guardian → Immutable Audit), we can ensure that:

1. **Destructive operations require explicit approval** from an independent guardian
2. **Critical files are protected** before any rollback via stashing
3. **All decisions are audited** with cryptographic integrity
4. **Circuit breakers prevent cascading failures** when the safety system misbehaves
5. **OpenTelemetry provides visibility** into the decision-making process

This transforms our observability from "trust but verify" to "verify then trust" - the watchers are now being watched.
