# Independent Verification Guide

This guide provides step-by-step instructions for independently verifying the Agentic System's capabilities.

## Verification Methods

### Method 1: AVIR (AI-Verified Independent Replication)

AVIR uses an independent AI (OpenAI Codex or Google Gemini) to verify the system in an isolated container.

```bash
# Run AVIR verification
cd avir
./run-verification.sh --provider codex

# Or with Gemini
./run-verification.sh --provider gemini
```

**What AVIR Does:**
1. Builds isolated container from specification
2. Deploys system with no access to original source
3. AI executes 5 standardized benchmarks
4. Generates cryptographic attestation
5. Produces verification report

### Method 2: Manual Verification

#### Step 1: Install the System

```bash
./bootstrap.sh
```

#### Step 2: Verify Services Are Running

```bash
python3 scripts/health_check.py
```

Expected output:
```
🔍 Agentic System Health Check

Services:
  ✓ Qdrant REST API (port 6333)
  ✓ Qdrant gRPC (port 6334)
  ✓ Redis (port 6379)

✓ All services healthy
```

#### Step 3: Run Benchmarks

```bash
python3 benchmarks/run_all.py
```

#### Step 4: Compare Results

| Benchmark | Target | Your Result | Pass? |
|-----------|--------|-------------|-------|
| memory_entity_creation | >348 ops/s | _____ | |
| semantic_search | >64 ops/s | _____ | |
| memory_promotion | >5.1 ops/s | _____ | |
| task_decomposition | <1500ms | _____ | |
| baton_handoff | <134ms | _____ | |

A test **passes** if within ±20% of target (±50% for latency benchmarks).

### Method 3: Component-Level Verification

If you only want to verify specific components:

#### Memory System
```bash
python3 benchmarks/test_memory.py
```

#### Task Management
```bash
python3 benchmarks/test_tasks.py
```

#### Reasoning Chains
```bash
python3 benchmarks/test_reasoning.py
```

## Submitting Verification Results

1. Open an issue using the [Verification Report template](.github/ISSUE_TEMPLATE/verification-report.md)
2. Include:
   - Your environment details
   - Benchmark results table
   - AVIR attestation hash (if used)
   - Any issues encountered
3. Attach `attestation.json` if you ran AVIR

## Verification Criteria

### VERIFIED
- All 5 benchmarks pass (within tolerance)
- System boots successfully
- Memory persists across restart

### PARTIAL
- 3-4 benchmarks pass
- Some components work but others fail
- Issues documented

### FAILED
- <3 benchmarks pass
- Unable to complete installation
- Core functionality missing

## FAQ

**Q: Do I need API keys?**
A: No API keys are required for basic verification. Some advanced features may require an Anthropic or OpenAI key.

**Q: How long does verification take?**
A: Full AVIR verification: ~5-10 minutes. Manual verification: ~15-30 minutes.

**Q: Can I verify on cloud VMs?**
A: Yes, any cloud VM with Docker and 16GB RAM should work.

**Q: The benchmarks are slower than published. Is that normal?**
A: Benchmarks have ±20% tolerance to account for hardware differences. Slower hardware will have lower scores but should still pass within tolerance.
