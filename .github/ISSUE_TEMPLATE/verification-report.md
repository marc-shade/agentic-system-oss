---
name: Verification Report
about: Submit independent verification results for the Agentic System
title: "[VERIFICATION] "
labels: verification, community
assignees: marc-shade
---

## Verification Report

### Verifier Information
- **Name/Organization**:
- **Date**:
- **Contact** (optional):

### Environment
- **OS**: (e.g., macOS 14.0, Ubuntu 22.04)
- **Hardware**: (e.g., M1 Mac Mini, 16GB RAM)
- **Python Version**:
- **Container Runtime**: (Docker/Podman/Apple Container)

### Verification Method Used
<!-- Check one -->
- [ ] **AVIR Protocol** (AI-Verified Independent Replication)
- [ ] **Full System Replication** (Manual setup and testing)
- [ ] **Component-Level Verification** (Specific components only)

### AVIR Results (if applicable)
```
Provider Used: (codex/gemini)
Attestation Hash:
Verdict: (VERIFIED/FAILED)
Tests Passed: X/5
```

### Benchmark Results

| Benchmark | Your Result | Published Target | Within Tolerance? |
|-----------|-------------|------------------|-------------------|
| memory_entity_creation | | 435 ops/s | |
| semantic_search | | 81 ops/s | |
| memory_promotion | | 6.4 ops/s | |
| task_decomposition | | 1200 ms | |
| baton_handoff | | 89 ms | |

### System Boot
- [ ] Bootstrap script completed successfully
- [ ] All MCP servers loaded
- [ ] Databases initialized
- [ ] Qdrant vector database running

### Functional Tests
- [ ] Memory persistence works (data survives restart)
- [ ] Semantic search returns relevant results
- [ ] Task management persists across sessions
- [ ] Goals/tasks survive session boundaries

### Issues Encountered
<!-- Describe any problems during verification -->

### Overall Verdict
<!-- Check one -->
- [ ] **VERIFIED** - System works as documented
- [ ] **PARTIAL** - Some components work, issues noted above
- [ ] **FAILED** - Unable to replicate claimed capabilities

### Additional Notes
<!-- Any other observations, suggestions, or comments -->

### Attachments
<!-- Please attach if available -->
- [ ] attestation.json from AVIR
- [ ] Console logs
- [ ] Screenshots
