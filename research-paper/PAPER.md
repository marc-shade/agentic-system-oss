# A 24/7 Autonomous Agentic System with Persistent Memory and Self-Improvement Capabilities

**Marc Shade**
2 Acre Studios
marc@2acrestudios.com

December 2025

---

## Abstract

We present a comprehensive framework for building autonomous agentic AI systems capable of continuous 24/7 operation. Our system addresses four fundamental challenges in agentic AI: (1) memory persistence across sessions, (2) reliable multi-agent coordination, (3) quality assurance without human oversight, and (4) verifiable capability claims. We introduce a 4-tier memory architecture inspired by human cognitive systems, featuring working, episodic, semantic, and procedural memory with autonomous curation. The system implements a relay race protocol for structured multi-agent task execution with circuit breakers for fault tolerance. We propose AVIR (AI-Verified Independent Replication), a protocol enabling AI systems to independently verify capability claims. Empirical evaluation on Apple M2 Max hardware demonstrates 467 entity creations/second, 89 semantic searches/second, and 76ms agent handoff latency. The system has operated continuously for over six months, demonstrating measurable self-improvement including a 13% increase in task success rate. All components are released as open source to enable independent verification.

**Keywords:** autonomous agents, persistent memory, multi-agent systems, Model Context Protocol, self-improvement, verification

---

## 1 Introduction

Large language models (LLMs) have demonstrated remarkable capabilities in reasoning, planning, and task execution [1, 2]. Recent work has explored extending these capabilities through tool use [3, 4], multi-agent coordination [5, 6], and memory augmentation [7]. However, building truly autonomous systems that operate continuously without human intervention remains challenging.

We identify four fundamental requirements for autonomous agentic systems:

1. **Persistent Memory**: LLMs lack native memory across sessions, limiting learning and context retention over time.

2. **Reliable Coordination**: Multi-agent systems require robust mechanisms to prevent conflicts, handle failures, and ensure task completion.

3. **Quality Assurance**: Autonomous operation necessitates automated quality enforcement to maintain production-ready outputs.

4. **Verifiable Claims**: The field lacks standardized methods for independently verifying system capability claims.

This paper presents an integrated system addressing all four requirements. Our contributions include:

- A 4-tier memory architecture with autonomous curation inspired by human memory consolidation
- A relay race protocol with circuit breakers for fault-tolerant multi-agent execution
- Ember, an automated quality enforcement mechanism
- AVIR, a protocol for AI-verified independent replication of capability claims
- Open-source release of all components with comprehensive benchmarks

### 1.1 System Overview

Our system builds on the Model Context Protocol (MCP) [8], which provides a standardized interface for AI models to access external tools and data. The architecture consists of eight MCP servers providing specialized capabilities:

| Server | Function |
|--------|----------|
| enhanced-memory | 4-tier persistent memory with versioning |
| agent-runtime | Task orchestration and relay pipelines |
| safla | High-performance vector embeddings |
| ember | Quality enforcement |
| sequential-thinking | Chain-of-thought reasoning |
| research-paper | Academic literature integration |
| video-transcript | Multimedia knowledge extraction |
| llm-council | Multi-provider deliberation |

---

## 2 Related Work

### 2.1 Memory-Augmented Language Models

MemGPT [7] introduced virtual context management, treating LLM context as a memory hierarchy analogous to operating system memory management. Our work extends this concept with explicit tier separation and autonomous promotion/demotion between tiers.

Retrieval-Augmented Generation (RAG) [9] demonstrated the value of integrating external knowledge during generation. We incorporate RAG within our semantic memory tier while adding causal relationship tracking and emotional salience scoring.

### 2.2 Agentic Frameworks

ReAct [4] established the paradigm of interleaving reasoning and acting, enabling models to use tools while maintaining interpretable reasoning traces. Our system adopts this pattern within individual agents while adding coordination mechanisms for multi-agent scenarios.

AutoGen [5] introduced conversable agents that coordinate through natural language dialogue. We build on this foundation with structured handoff protocols and explicit quality checkpoints between agents.

LangChain [10] and similar frameworks provide infrastructure for building agent applications. Our system focuses specifically on long-running autonomous operation with persistent state.

### 2.3 Tool-Using Language Models

Toolformer [3] demonstrated that language models can learn to use tools through self-supervision. Our system provides tools through MCP servers, enabling modular capability extension without model retraining.

### 2.4 Self-Improving Systems

The concept of recursive self-improvement has been explored theoretically [11]. Our system implements practical self-improvement through configuration optimization, pattern learning, and skill evolution, with safeguards to prevent harmful modifications.

---

## 3 Memory Architecture

### 3.1 Four-Tier Design

Our memory system implements a hierarchy inspired by human cognitive architecture:

**Tier 1: Working Memory**
- Volatile storage for active task context
- Time-to-live (TTL) based expiration (default: 60 minutes)
- High-frequency access items automatically promoted to episodic memory

**Tier 2: Episodic Memory**
- Time-stamped records of experiences and events
- Significance scoring (0.0-1.0) for importance weighting
- Emotional valence tagging (-1.0 to +1.0) for affect-aware retrieval

**Tier 3: Semantic Memory**
- Abstract concepts and factual knowledge
- Confidence-scored assertions
- Graph-based relationship modeling between concepts

**Tier 4: Procedural Memory**
- Executable skills represented as step sequences
- Success rate tracking per skill
- Automatic refinement through execution feedback

### 3.2 Autonomous Curation

Memory consolidation runs automatically every 24 hours, implementing processes analogous to sleep-based memory consolidation in humans:

```
Algorithm 1: Memory Consolidation
Input: Time window T (default: 24 hours)
Output: Consolidation statistics

1. PROMOTE high-access working memories to episodic tier
   (threshold: 5+ accesses within T)

2. EXTRACT patterns from episodic memories
   - Cluster by semantic similarity
   - Identify recurring sequences
   - Minimum frequency threshold: 3 occurrences

3. CREATE semantic concepts from extracted patterns
   - Generate concept name and definition
   - Link to source episodic memories
   - Set initial confidence based on pattern strength

4. CONVERT repeated action sequences to procedural skills
   - Minimum occurrences: 5 within 7 days
   - Extract preconditions and postconditions
   - Initialize success rate tracker

5. COMPRESS old low-importance memories
   - Age threshold: 7 days
   - Importance threshold: 0.3
   - Retain summary, discard details
```

### 3.3 Retrieval Mechanisms

We implement hybrid retrieval combining:
- **BM25**: Sparse lexical matching for keyword queries
- **Vector Search**: Dense semantic similarity using sentence embeddings
- **Reciprocal Rank Fusion**: Combining ranked results from both methods

Additionally, we implement spreading activation for associative recall, where retrieving one memory can activate semantically or temporally linked memories.

### 3.4 Forgetting and Reinforcement

Memory strength follows an exponential decay inspired by the Ebbinghaus forgetting curve:

$$S(t) = S_0 \cdot e^{-\lambda t}$$

where $S_0$ is initial strength, $\lambda$ is the decay constant, and $t$ is time since last access. Retrieved memories receive a strength boost (spacing effect), implementing spaced repetition naturally through usage patterns.

---

## 4 Agent Runtime

### 4.1 Goal Decomposition

Natural language goals are decomposed into hierarchical task structures:

```
Goal: "Implement user authentication"
├── Task 1: Design authentication flow
│   ├── Subtask 1.1: Define user model schema
│   └── Subtask 1.2: Specify token management
├── Task 2: Implement backend handlers
│   ├── Subtask 2.1: Login endpoint
│   └── Subtask 2.2: Registration endpoint
├── Task 3: Add security measures
└── Task 4: Write test suite
```

Decomposition employs three strategies selected based on goal characteristics:
- **Sequential**: Tasks with strict ordering dependencies
- **Parallel**: Independent tasks executable concurrently
- **Hierarchical**: Complex tasks requiring recursive decomposition

### 4.2 Relay Race Protocol

For complex multi-step tasks, we implement a relay race protocol where specialized agents execute sequentially, passing a structured "baton" between stages:

| Stage | Agent Role | Responsibility |
|-------|------------|----------------|
| 1 | Researcher | Gather context, identify requirements |
| 2 | Analyzer | Evaluate approaches, assess trade-offs |
| 3 | Synthesizer | Integrate insights into coherent plan |
| 4 | Validator | Check for errors, verify constraints |
| 5 | Formatter | Produce final output |

The baton contains:
- Output summary from previous agent
- Quality score (0.0-1.0)
- Provenance chain (L-Score)
- Token budget consumed
- Entity references for stored artifacts

### 4.3 Circuit Breakers

To prevent cascading failures, each agent type has an associated circuit breaker with three states:

- **CLOSED**: Normal operation; requests pass through
- **OPEN**: Failures exceeded threshold; requests routed to fallback
- **HALF-OPEN**: Trial period; single request tests recovery

Configuration parameters:
- Failure threshold: 5 failures within sliding window
- Window duration: 60 seconds
- Cooldown period: 300 seconds
- Fallback agent: generalist

---

## 5 Quality Enforcement

### 5.1 Ember: The Conscience Keeper

Ember is an automated quality enforcement mechanism that evaluates outputs against production-readiness criteria:

**Violation Categories:**
- Placeholder content (TODO, Lorem ipsum, example.com)
- Mock or hardcoded data
- Incomplete implementations
- Security vulnerabilities
- Missing error handling

**Enforcement Actions:**
1. Pre-flight check before file writes
2. Violation severity scoring (0.0-1.0)
3. Inline fix suggestions
4. Learning from override decisions

### 5.2 Learning from Corrections

When users override Ember's assessments, the system records:
- Original violation type
- User's correction rationale
- Context conditions
- Outcome (was user correct?)

This feedback loop enables Ember to reduce false positives over time while maintaining strict quality standards.

---

## 6 Verification Protocol (AVIR)

### 6.1 Motivation

Claims about AI system capabilities are difficult to independently verify. AVIR (AI-Verified Independent Replication) provides:

1. Standardized benchmarks with defined tolerances
2. Multi-provider verification (any capable AI can verify)
3. Cryptographic attestation of results

### 6.2 Benchmark Specification

| Benchmark | Metric | Target | Tolerance |
|-----------|--------|--------|-----------|
| memory_entity_creation | ops/second | 435 | ±20% |
| semantic_search | ops/second | 81 | ±20% |
| memory_promotion | ops/second | 6.4 | ±20% |
| task_decomposition | latency (ms) | 1200 | ±25% |
| baton_handoff | latency (ms) | 89 | ±50% |

### 6.3 Verification Process

```bash
# Execute verification with any supported AI provider
./avir/run-verification.sh --provider [claude|codex|gemini]

# Output:
# - Benchmark results with pass/fail
# - Hardware specifications
# - Attestation hash (SHA-256)
```

### 6.4 Attestation Format

```json
{
  "version": "1.0",
  "timestamp": "2025-12-17T10:00:00Z",
  "verifier": {
    "provider": "claude",
    "model": "claude-3-opus",
    "session_id": "avir-xxxxx"
  },
  "hardware": {
    "platform": "darwin",
    "processor": "Apple M2 Max",
    "memory_gb": 32
  },
  "results": {
    "memory_entity_creation": {"value": 467.3, "target": 435, "passed": true},
    "semantic_search": {"value": 89.2, "target": 81, "passed": true}
  },
  "attestation_hash": "sha256:a1b2c3d4..."
}
```

---

## 7 Evaluation

### 7.1 Experimental Setup

**Hardware:** Apple M2 Max (Mac Studio), 32GB unified memory, 1TB SSD

**Software:** Python 3.11, Claude Code CLI, Qdrant 1.7, SQLite 3.43

**Benchmarks:** Each measurement averaged over 100 iterations with 10 warm-up runs discarded.

### 7.2 Performance Results

| Benchmark | Result | Target | Status |
|-----------|--------|--------|--------|
| Memory Entity Creation | 467.3 ops/s | 435 ops/s | PASS (+7.4%) |
| Semantic Search | 89.2 ops/s | 81 ops/s | PASS (+10.1%) |
| Memory Promotion | 7.1 ops/s | 6.4 ops/s | PASS (+10.9%) |
| Task Decomposition | 1,089 ms | 1,200 ms | PASS (-9.3%) |
| Baton Handoff | 76 ms | 89 ms | PASS (-14.6%) |

### 7.3 Long-Term Operation

Over six months of continuous operation (January - June 2025):

| Metric | Value |
|--------|-------|
| Uptime | 99.7% |
| Memory Entities Created | 47,284 |
| Tasks Completed | 12,847 |
| Self-Improvement Cycles | 340 |
| Circuit Breaker Trips | 23 |

### 7.4 Self-Improvement Metrics

Comparing month 1 to month 6:

| Metric | Month 1 | Month 6 | Change |
|--------|---------|---------|--------|
| Task Success Rate | 78.2% | 91.4% | +13.2% |
| Average Task Duration | 45.3s | 32.1s | -29.1% |
| Memory Cache Hit Rate | 62.4% | 84.1% | +21.7% |
| False Positive Rate (Ember) | 12.3% | 4.7% | -7.6% |

---

## 8 Limitations and Future Work

### 8.1 Current Limitations

1. **Hardware Requirements**: Full deployment requires 16GB+ RAM for optimal performance.

2. **Model Dependency**: Currently optimized for Anthropic Claude models; other providers may require adaptation.

3. **Verification Scope**: AVIR tests functional capabilities but not adversarial robustness.

4. **Single-Node Focus**: Current architecture optimized for single-machine deployment; distributed operation requires additional coordination.

### 8.2 Future Directions

1. **Federated Learning**: Enable knowledge sharing across independent installations while preserving privacy.

2. **Adversarial Testing**: Extend AVIR to include robustness benchmarks against malicious inputs.

3. **Edge Deployment**: Optimize for resource-constrained environments.

4. **Multi-Modal Memory**: Extend memory system to handle images, audio, and video natively.

---

## 9 Conclusion

We have presented a comprehensive framework for autonomous agentic AI systems addressing fundamental challenges in memory persistence, multi-agent coordination, quality assurance, and verification. The system demonstrates that long-running autonomous operation is practical with appropriate architectural choices.

Our 4-tier memory system with autonomous curation provides persistent learning capabilities previously unavailable to LLM-based systems. The relay race protocol with circuit breakers enables reliable multi-agent task execution. Ember ensures production-quality outputs without human oversight. AVIR enables independent verification of capability claims.

Six months of continuous operation demonstrates the system's reliability and measurable self-improvement. All components are released as open source at https://github.com/marc-shade/agentic-system-oss.

We invite the research community to replicate, verify, and extend this work.

---

## References

[1] J. Wei, X. Wang, D. Schuurmans, M. Bosma, B. Ichter, F. Xia, E. Chi, Q. Le, and D. Zhou, "Chain-of-thought prompting elicits reasoning in large language models," in *Advances in Neural Information Processing Systems*, vol. 35, 2022. arXiv:2201.11903

[2] OpenAI, "GPT-4 technical report," arXiv:2303.08774, 2023.

[3] T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, "Toolformer: Language models can teach themselves to use tools," arXiv:2302.04761, 2023.

[4] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *International Conference on Learning Representations*, 2023. arXiv:2210.03629

[5] Q. Wu, G. Bansal, J. Zhang, Y. Wu, S. Zhang, E. Zhu, B. Li, L. Jiang, X. Zhang, and C. Wang, "AutoGen: Enabling next-gen LLM applications via multi-agent conversation framework," arXiv:2308.08155, 2023.

[6] Y. Hong, W. Zheng, H. Liu, K. Zhu, J. Liu, and F. Wu, "MetaGPT: Meta programming for multi-agent collaborative framework," arXiv:2308.00352, 2023.

[7] C. Packer, V. Fang, S. G. Patil, K. Lin, S. Wooders, and J. Gonzalez, "MemGPT: Towards LLMs as operating systems," arXiv:2310.08560, 2023.

[8] Anthropic, "Model Context Protocol specification," https://modelcontextprotocol.io, 2024.

[9] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems*, vol. 33, 2020.

[10] H. Chase, "LangChain," https://langchain.com, 2022.

[11] J. Schmidhuber, "Gödel machines: Fully self-referential optimal universal self-improvers," in *Artificial General Intelligence*, pp. 199-226, 2007.

[12] Qdrant, "Vector search engine," https://qdrant.tech, 2024.

[13] Temporal Technologies, "Temporal workflow engine," https://temporal.io, 2024.

---

## Appendix A: Installation

```bash
# One-command installation
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system-oss/master/bootstrap.sh | bash

# Verify installation
python3 scripts/health_check.py
```

## Appendix B: MCP Server Tools

| Server | Tool Count | Key Functions |
|--------|------------|---------------|
| enhanced-memory | 80+ | create_entities, search_nodes, memory_curation |
| agent-runtime | 15+ | create_goal, decompose_goal, advance_relay |
| safla | 4 | generate_embeddings, store_memory |
| ember | 8 | check_violation, consult, learn_from_outcome |
| sequential-thinking | 1 | sequentialthinking |
| research-paper | 6 | search_arxiv, search_semantic_scholar |
| video-transcript | 6 | fetch_youtube_transcript, extract_concepts |
| llm-council | 6 | council_deliberate, council_run_pattern |

## Appendix C: AVIR Commands

```bash
# Full verification
./avir/run-verification.sh --provider codex --full

# Single benchmark
python3 avir/verify.py --benchmark memory_entity_creation

# Submit attestation
./avir/submit-results.sh --attestation results.json
```

---

*Released under the MIT License. Code available at https://github.com/marc-shade/agentic-system-oss*
