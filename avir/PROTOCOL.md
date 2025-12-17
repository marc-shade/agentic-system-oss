# AVIR Protocol Specification

## AI-Verified Independent Replication

**Version**: 1.0
**Date**: December 2024

---

## Overview

AVIR (AI-Verified Independent Replication) is a protocol for verifying agentic system capabilities through cryptographically provable AI-based replication. It provides stronger guarantees than human replication while being faster, cheaper, and more consistent.

## Protocol Phases

### Phase 1: Specification Extraction

Extract a functional specification from the original system that:
- Describes WHAT the system does (not HOW)
- Includes all capability claims
- Defines verification benchmarks
- Contains no implementation code

**Output**: `spec.yaml` - Machine-readable specification

### Phase 2: Environment Isolation

Create a completely isolated build environment:

1. **Container Isolation**
   - Fresh OS image (no shared state)
   - No network access to original system
   - No shared volumes or filesystems

2. **AI Provider Isolation**
   - Use DIFFERENT AI provider than original build
   - Example: If built with Claude, verify with Codex
   - Fresh context window (no conversation history)

3. **Cryptographic Attestation**
   - Hash of container image: `SHA256(image)`
   - Timestamp of build start: `ISO8601(now)`
   - Network isolation proof: `NONE` connectivity test

### Phase 3: Independent Build

AI agent reads ONLY the specification and builds:

1. Receives `spec.yaml`
2. Has access to standard libraries/packages
3. NO access to original source code
4. Builds complete system from scratch
5. Logs all actions for audit

### Phase 4: Verification

Run identical benchmark suite on both systems:

1. **Functional Verification**
   - All specified capabilities must work
   - Input/output behavior must match

2. **Performance Verification**
   - Benchmarks within tolerance (default: ±10%)
   - No regression in core metrics

3. **Test Suite**
   - Same test cases, same pass criteria
   - Tolerance for implementation variance

### Phase 5: Attestation

Generate cryptographic proof:

```
AVIR_ATTESTATION = {
    "protocol_version": "1.0",
    "timestamp": "ISO8601",
    "original_system": {
        "hash": "SHA256(source)",
        "provider": "claude",
        "benchmark_results": {...}
    },
    "isolated_build": {
        "container_hash": "SHA256(image)",
        "provider": "codex",
        "build_log_hash": "SHA256(logs)",
        "benchmark_results": {...}
    },
    "verification": {
        "functional_match": true/false,
        "benchmark_tolerance": "±10%",
        "tests_passed": "N/M",
        "verdict": "VERIFIED" | "FAILED"
    },
    "signature": "ED25519(attestation)"
}
```

---

## Specification Format

### spec.yaml Schema

```yaml
version: "1.0"
name: "System Name"
description: "Brief description"

capabilities:
  - name: "capability_name"
    description: "What it does"
    inputs:
      - name: "input_name"
        type: "string|number|object"
    outputs:
      - name: "output_name"
        type: "string|number|object"
    verification:
      test_cases:
        - input: {...}
          expected_output: {...}
          tolerance: "exact|approximate|behavioral"

benchmarks:
  - name: "benchmark_name"
    metric: "latency|throughput|accuracy"
    target: 100
    unit: "ms|ops/sec|percent"
    tolerance: 0.1  # ±10%

requirements:
  runtime:
    - "python>=3.10"
    - "docker|podman"
  hardware:
    min_ram: "8GB"
    min_storage: "20GB"
```

---

## Isolation Guarantees

### Container Configuration

```dockerfile
# AVIR Isolated Build Environment
FROM python:3.11-slim

# No external network (set at runtime)
# No mounted volumes from host
# Fresh filesystem

# Standard packages only
RUN pip install anthropic openai httpx pydantic

# Build user (non-root)
RUN useradd -m builder
USER builder
WORKDIR /home/builder

# Spec file will be copied in
COPY spec.yaml /home/builder/spec.yaml

# AI agent runs here
ENTRYPOINT ["python3", "build_from_spec.py"]
```

### Runtime Isolation

```bash
# Run with full isolation
podman run \
    --network=none \           # No network
    --read-only \              # Read-only root
    --tmpfs /tmp \             # Temporary only in /tmp
    --security-opt no-new-privileges \
    avir-build-env
```

---

## Verification Criteria

### Functional Match

| Criterion | Required | Notes |
|-----------|----------|-------|
| All capabilities present | Yes | Must implement every specified capability |
| Correct inputs accepted | Yes | Type and validation |
| Correct outputs produced | Yes | Within tolerance |
| Error handling | Yes | Graceful failure modes |

### Performance Match

| Metric | Tolerance | Notes |
|--------|-----------|-------|
| Latency | ±20% | p50 and p99 |
| Throughput | ±20% | Operations per second |
| Memory usage | ±50% | Peak and average |
| Storage | ±100% | Different implementations vary |

### Test Suite Match

| Test Type | Required Pass Rate |
|-----------|-------------------|
| Unit tests | ≥90% |
| Integration tests | ≥85% |
| Behavioral tests | ≥95% |

---

## Security Considerations

### Preventing Leakage

1. **No Network**: Container has no network access
2. **No Shared State**: Fresh container image
3. **Different Provider**: AI cannot access its own memories
4. **Audit Trail**: Every action logged and hashed

### Attestation Integrity

1. **Timestamped**: All operations have timestamps
2. **Hashed**: All artifacts have SHA256 hashes
3. **Signed**: Final attestation cryptographically signed
4. **Reproducible**: Same spec → same build (deterministic)

---

## Implementation Guide

### For Original System Developers

1. **Generate Specification**
   ```bash
   python3 avir/extract_spec.py --output spec.yaml
   ```

2. **Create Benchmark Suite**
   ```bash
   python3 avir/create_benchmarks.py --output benchmarks/
   ```

3. **Run Self-Verification**
   ```bash
   python3 avir/run_verification.py --mode self-test
   ```

### For Independent Verifiers

1. **Download Specification**
   ```bash
   curl -O https://github.com/repo/releases/latest/spec.yaml
   ```

2. **Run AVIR Verification**
   ```bash
   python3 avir/run_verification.py \
       --spec spec.yaml \
       --provider codex \  # Different from original
       --output attestation.json
   ```

3. **Submit Attestation**
   ```bash
   python3 avir/submit_attestation.py --file attestation.json
   ```

---

## Advantages Over Human Replication

| Aspect | Human Replication | AVIR |
|--------|------------------|------|
| Time | Weeks to months | Hours |
| Cost | High (researcher time) | Low (compute only) |
| Consistency | Variable (interpretation) | Exact (spec-driven) |
| Provability | Trust-based | Cryptographic |
| Repeatability | Difficult | Trivial |
| Auditability | Limited | Complete logs |

---

## Limitations

1. **Specification Quality**: AVIR is only as good as the spec
2. **AI Capability**: Verifying AI must be capable of building
3. **Emergent Behavior**: Hard to specify emergent properties
4. **Adversarial Specs**: Malicious specs could game verification

---

## Future Extensions

1. **Multi-Verifier Consensus**: Multiple AIs verify independently
2. **Continuous Verification**: Automated CI/CD integration
3. **Capability Discovery**: AI identifies unspecified capabilities
4. **Formal Methods**: Prove properties about specification

---

## References

- Bostrom, N. "Superintelligence" (2014) - Verification of AI systems
- Chollet, F. "On the Measure of Intelligence" (2019) - Capability assessment
- Anthropic, "Model Card for Claude" - AI system documentation standards
