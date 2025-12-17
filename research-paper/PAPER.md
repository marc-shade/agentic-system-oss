# A 24/7 Autonomous Agentic AI System with Persistent Memory and Self-Improvement

**Marc Shade**
2 Acre Studios
December 2025

---

## Abstract

We present a comprehensive autonomous agentic AI system designed for continuous 24/7 operation with persistent memory, multi-agent coordination, and self-improvement capabilities. The system integrates multiple Model Context Protocol (MCP) servers to provide AI agents with persistent 4-tier memory, task orchestration with circuit breakers, high-performance vector embeddings, and quality enforcement mechanisms. We introduce the AVIR (AI-Verified Independent Replication) protocol for standardized system verification across different AI providers. Benchmark results demonstrate 435 ops/s for memory entity creation, 81 ops/s for semantic search, and sub-150ms agent relay handoffs. The system has been running autonomously for over 6 months, accumulating learnings and demonstrating emergent self-improvement behaviors. All components are released as open source to enable independent verification and replication.

**Keywords:** Autonomous AI, Agentic Systems, Persistent Memory, Multi-Agent Coordination, Model Context Protocol, Self-Improvement

---

## 1. Introduction

The emergence of large language models (LLMs) has enabled a new paradigm of AI systems that can reason, plan, and execute complex tasks autonomously. However, several fundamental challenges remain:

1. **Memory Persistence**: LLMs lack persistent memory across sessions, limiting their ability to learn and accumulate knowledge over time.

2. **Coordination**: Multi-agent systems require robust coordination mechanisms to prevent conflicts and ensure reliable execution.

3. **Quality Assurance**: Autonomous systems need guardrails to maintain production-quality outputs without human oversight.

4. **Verification**: Claims about AI system capabilities are difficult to independently verify and replicate.

This paper presents an autonomous agentic system that addresses these challenges through a novel architecture combining:

- **4-Tier Memory System**: Working, episodic, semantic, and procedural memory with automatic curation and promotion
- **Relay Race Protocol**: Structured agent handoffs with circuit breakers for fault tolerance
- **Quality Enforcement**: Ember, a "conscience keeper" that enforces production-only policies
- **AVIR Protocol**: Standardized verification enabling AI systems to independently validate capabilities

The system has been operating continuously for over 6 months on distributed Mac/Linux hardware, demonstrating sustained autonomous operation with measurable self-improvement.

### 1.1 Contributions

1. A complete architecture for 24/7 autonomous AI operation with persistent state
2. A 4-tier memory system with automatic curation inspired by human memory consolidation
3. The AVIR protocol for AI-verified independent replication of system capabilities
4. Open-source release of all components for independent verification

---

## 2. System Architecture

### 2.1 Overview

The system consists of three primary layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                       │
│  ├─ Claude Code CLI    : Primary AI interface               │
│  ├─ Temporal           : Long-running workflow state        │
│  └─ AutoKitteh         : Event-driven automation            │
├─────────────────────────────────────────────────────────────┤
│                    MCP Server Layer                          │
│  ├─ enhanced-memory    : 4-tier persistent memory           │
│  ├─ agent-runtime      : Task orchestration & relay race    │
│  ├─ safla              : High-speed vector embeddings       │
│  ├─ ember              : Quality enforcement                │
│  ├─ sequential-thinking: Chain-of-thought reasoning         │
│  └─ research-paper     : Academic paper integration         │
├─────────────────────────────────────────────────────────────┤
│                    Storage Layer                             │
│  ├─ Qdrant             : Vector database                    │
│  ├─ SQLite             : Structured data                    │
│  └─ Redis              : Cache and message queues           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Model Context Protocol (MCP)

MCP provides a standardized interface for AI models to access external tools and data sources. Each MCP server exposes a set of tools that the AI can invoke during reasoning. This architecture enables:

- **Modularity**: Components can be developed and deployed independently
- **Extensibility**: New capabilities added without modifying core AI
- **Standardization**: Common protocol across different AI providers

### 2.3 Distributed Execution

The system operates across multiple nodes with specialized roles:

| Node | Role | Capabilities |
|------|------|--------------|
| Orchestrator | System coordination | Task routing, memory consolidation |
| Researcher | Information gathering | Paper search, web analysis |
| Developer | Implementation | Code generation, testing |
| Builder | Compilation | Container builds, CI/CD |

Nodes communicate through a dedicated chat protocol with persona-aware context preservation.

---

## 3. Memory System

### 3.1 4-Tier Architecture

The memory system implements a hierarchy inspired by human cognitive architecture:

**Tier 1: Working Memory**
- Volatile, high-access storage for active context
- TTL-based expiration (default: 60 minutes)
- Automatic promotion to episodic memory based on access frequency

**Tier 2: Episodic Memory**
- Time-stamped experiences and events
- Significance scoring (0.0-1.0) for importance weighting
- Emotional valence tagging for affect-aware retrieval

**Tier 3: Semantic Memory**
- Abstract concepts and relationships
- Confidence-scored knowledge
- Graph-based concept linking

**Tier 4: Procedural Memory**
- Executable skills and procedures
- Success rate tracking
- Automatic refinement through execution feedback

### 3.2 Autonomous Curation

The system implements sleep-like memory consolidation:

```python
def autonomous_memory_curation():
    # Promote high-access working memories to episodic
    promote_working_to_episodic(access_threshold=5)

    # Extract patterns from episodic to semantic
    patterns = extract_patterns(time_window_hours=24)
    promote_to_semantic(patterns, min_frequency=3)

    # Convert repeated actions to procedural skills
    actions = find_repeated_actions(time_window_hours=168)
    create_procedural_skills(actions, min_occurrences=5)

    # Compress old low-importance memories
    compress_memories(older_than_hours=168)
```

This process runs automatically every 24 hours, mimicking human sleep consolidation.

### 3.3 Causal Reasoning

The memory system tracks causal relationships between entities:

- **Causal Links**: Direct, indirect, contributory, and preventive relationships
- **Temporal Chains**: Sequences of causally-related events
- **Outcome Prediction**: Probabilistic prediction based on causal history

This enables the system to learn from experience and predict likely outcomes of actions.

### 3.4 Forgetting and Retrieval

Following the Ebbinghaus forgetting curve, memory strength decays over time:

```
strength(t) = e^(-kt)
```

Where `k` is the decay constant and `t` is time since last access. Retrieved memories receive a strength boost (spacing effect), reinforcing important information.

---

## 4. Agent Runtime

### 4.1 Task Decomposition

Goals are automatically decomposed into hierarchical tasks:

```
Goal: "Build a REST API for user authentication"
├─ Task 1: Design API endpoints
│   ├─ Subtask 1.1: Define user model
│   └─ Subtask 1.2: Specify auth flow
├─ Task 2: Implement handlers
├─ Task 3: Add database integration
├─ Task 4: Write tests
└─ Task 5: Document API
```

Decomposition strategies include sequential, parallel, and hierarchical approaches selected based on goal characteristics.

### 4.2 Relay Race Protocol

For complex multi-step tasks, agents execute in a relay race pattern:

1. **Researcher** gathers context and requirements
2. **Analyzer** evaluates approaches and trade-offs
3. **Synthesizer** combines insights into a plan
4. **Validator** checks for errors and inconsistencies
5. **Formatter** produces final output

Each agent passes a "baton" containing:
- Output summary from previous agent
- Quality score (0.0-1.0)
- L-Score (provenance tracking)
- Tokens consumed
- Entity ID for stored output

### 4.3 Circuit Breakers

To prevent cascading failures, each agent has a circuit breaker:

| State | Behavior |
|-------|----------|
| CLOSED | Normal operation |
| OPEN | Route to fallback agent |
| HALF_OPEN | Trial single request |

Circuit breakers trip after configurable failure thresholds within a sliding window, automatically recovering after a cooldown period.

---

## 5. Quality Enforcement

### 5.1 Ember: The Conscience Keeper

Ember is a quality enforcement system that ensures production-ready outputs:

**Violation Detection:**
- Placeholder content ("TODO", "Lorem ipsum")
- Mock data and hardcoded values
- Incomplete implementations
- Security vulnerabilities

**Policy Enforcement:**
```python
def check_violation(action, params, context):
    violations = []

    if contains_placeholder(params.content):
        violations.append("placeholder_content")

    if contains_mock_data(params.content):
        violations.append("mock_data")

    if is_incomplete(params.content, context):
        violations.append("incomplete_implementation")

    return ViolationReport(
        violations=violations,
        severity=calculate_severity(violations),
        suggestions=generate_fixes(violations)
    )
```

### 5.2 Learning from Outcomes

Ember learns from outcomes to improve future guidance:

- Successful patterns are reinforced
- Failed patterns are flagged for avoidance
- False positives are tracked to reduce over-flagging

---

## 6. Verification Protocol (AVIR)

### 6.1 Motivation

Claims about AI system capabilities are often difficult to verify. AVIR (AI-Verified Independent Replication) addresses this by:

1. Providing standardized benchmarks with defined tolerances
2. Enabling AI systems (not just humans) to run verification
3. Generating cryptographic attestations of results

### 6.2 Benchmark Suite

| Benchmark | Description | Target | Tolerance |
|-----------|-------------|--------|-----------|
| memory_entity_creation | Entities created per second | 435 ops/s | ±20% |
| semantic_search | Search operations per second | 81 ops/s | ±20% |
| memory_promotion | Tier promotions per second | 6.4 ops/s | ±20% |
| task_decomposition | Goal → tasks latency | 1200ms | ±25% |
| baton_handoff | Agent relay latency | 89ms | ±50% |

### 6.3 Verification Process

```bash
# Run AVIR verification with any supported AI provider
./avir/run-verification.sh --provider codex

# Output includes:
# - Benchmark results with pass/fail status
# - Hardware specifications
# - Cryptographic attestation hash
# - Suggestions for submission
```

### 6.4 Attestation Format

```json
{
  "version": "1.0",
  "timestamp": "2025-12-17T10:00:00Z",
  "verifier": {
    "provider": "codex",
    "model": "gpt-4",
    "session_id": "abc123"
  },
  "benchmarks": {
    "memory_entity_creation": {
      "result": 467.3,
      "target": 435,
      "passed": true
    }
  },
  "attestation_hash": "sha256:a1b2c3..."
}
```

---

## 7. Experimental Results

### 7.1 Benchmark Performance

Testing was conducted on Apple M2 Max (Mac Studio) with 32GB RAM:

| Benchmark | Result | Target | Status |
|-----------|--------|--------|--------|
| Memory Entity Creation | 467.3 ops/s | 435 ops/s | PASS |
| Semantic Search | 89.2 ops/s | 81 ops/s | PASS |
| Memory Promotion | 7.1 ops/s | 6.4 ops/s | PASS |
| Task Decomposition | 1,089ms | 1,200ms | PASS |
| Baton Handoff | 76ms | 89ms | PASS |

### 7.2 Long-Term Operation

Over 6 months of continuous operation:

- **Uptime**: 99.7% (excluding planned maintenance)
- **Memory Entities**: 47,000+ accumulated
- **Tasks Completed**: 12,000+
- **Self-Improvements**: 340+ applied optimizations

### 7.3 Self-Improvement Metrics

The system tracks its own improvement over time:

| Metric | Month 1 | Month 6 | Improvement |
|--------|---------|---------|-------------|
| Task Success Rate | 78% | 91% | +13% |
| Average Task Time | 45s | 32s | -29% |
| Memory Hit Rate | 62% | 84% | +22% |

---

## 8. Related Work

### 8.1 Memory Systems for AI

MemGPT (Packer et al., 2023) introduced virtual context management for LLMs. Our system extends this with 4-tier memory and autonomous curation.

LETTA (2024) proposed memory blocks for stateful agents. We adopt similar patterns while adding causal reasoning and emotional tagging.

### 8.2 Multi-Agent Systems

AutoGen (Wu et al., 2023) enables multi-agent conversations. Our relay race protocol provides more structured handoffs with quality tracking.

CrewAI focuses on role-based agent coordination. We add circuit breakers and provenance tracking for fault tolerance.

### 8.3 Self-Improvement

Recursive self-improvement has been explored theoretically (Schmidhuber, 2007). Our system implements practical self-improvement through:
- Configuration optimization
- Pattern learning
- Skill evolution

---

## 9. Limitations and Future Work

### 9.1 Current Limitations

1. **Hardware Requirements**: Full system requires significant resources (16GB+ RAM recommended)
2. **Provider Dependency**: Currently optimized for Claude/Anthropic models
3. **Verification Scope**: AVIR tests functional but not adversarial capabilities

### 9.2 Future Directions

1. **Federated Memory**: Sharing learned patterns across independent installations
2. **Adversarial Verification**: Testing system robustness against malicious inputs
3. **Smaller Footprints**: Optimizing for edge deployment

---

## 10. Conclusion

We have presented a comprehensive autonomous agentic AI system that addresses fundamental challenges in persistent memory, multi-agent coordination, quality assurance, and verification. The system demonstrates that long-running autonomous AI operation is practical with appropriate architectural choices.

Key contributions include:
- A 4-tier memory system with autonomous curation
- The relay race protocol for structured multi-agent tasks
- Ember, a quality enforcement mechanism
- AVIR, an AI-verified replication protocol

All components are released as open source at:
https://github.com/marc-shade/agentic-system-oss

We invite the research community to replicate, verify, and extend this work.

---

## References

1. Anthropic. (2024). Model Context Protocol Specification. https://modelcontextprotocol.io

2. Packer, C., et al. (2023). MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560

3. Wu, Q., et al. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv:2308.08155

4. Schmidhuber, J. (2007). Gödel Machines: Fully Self-Referential Optimal Universal Self-Improvers. Artificial General Intelligence, 199-226.

5. Ebbinghaus, H. (1885). Memory: A Contribution to Experimental Psychology.

6. Temporal Technologies. (2024). Temporal Workflow Engine. https://temporal.io

7. Qdrant. (2024). Vector Search Engine. https://qdrant.tech

---

## Appendix A: Installation

```bash
# One-command installation
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system-oss/master/bootstrap.sh | bash

# Or clone and run
git clone https://github.com/marc-shade/agentic-system-oss.git
cd agentic-system-oss
./bootstrap.sh
```

## Appendix B: MCP Server Reference

| Server | Tools | Purpose |
|--------|-------|---------|
| enhanced-memory | 80+ | 4-tier persistent memory |
| agent-runtime | 15+ | Task orchestration |
| safla | 4 | Vector embeddings |
| ember | 8 | Quality enforcement |
| sequential-thinking | 1 | Deep reasoning |
| research-paper | 6 | Academic search |
| video-transcript | 6 | YouTube analysis |
| llm-council | 6 | Multi-provider deliberation |

## Appendix C: AVIR Verification Commands

```bash
# Full verification suite
./avir/run-verification.sh --provider codex --full

# Single benchmark
./avir/verify.py --benchmark memory_entity_creation

# Submit results
./avir/submit-results.sh --attestation results.json
```

---

*This paper and all associated software are released under the MIT License.*
