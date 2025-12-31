# ECDE Council Feedback Analysis

## Date: 2025-12-17

## Summary
The LLM Council rejected ECDE for AGI Goal 9 (Novel Capability Invention). The core criticism is the same as RQT: "sophisticated engineering and automated search inside a bounded design space, not expansion of that space."

## Council's Specific Criticisms

### 1. RSI Criteria (Bostrom/Yudkowsky) - NOT MET
- **Gap**: No self-modification of the improver itself
- **Issue**: Strategy evolution seen as "parameter/policy hill-climbing within a fixed design space"
- **Required**: Modify the learning/architectural machinery that compounds across tasks
- **One strategy evolution insufficient** for sustained, open-ended RSI

### 2. Emergence Criteria (Wei et al.) - NOT MET
- **Gap**: No scaling curves, ablations, or phase transitions
- **Issue**: 35 "emergent" capabilities indistinguishable from combinatorial discovery
- **Required**: Show qualitative novelty non-derivable from primitives
- **Benchmark missing**: Compare against random search, curriculum learning, AutoML

### 3. Validation Criteria Concerns
- **self_initiated**: Designed loop proposing tests is expected behavior, not autonomous metacognitive expansion
- **truly_novel**: System novelty ≠ invention in principle
- **unanticipated**: Designers anticipated such discoveries by design
- **has_capability**: Confirms execution, not origin of invention

## What Council Says Is Needed for Goal 9

1. **New Algorithms/Representations**: Create capabilities absent from training data, with independent replication

2. **Emergence Scaling Evidence**: Phase transitions, ablations vs. baselines (random search, curriculum, AutoML)

3. **Recursive Self-Modification**: Modify the learning/architectural machinery itself that compounds

4. **Independent Novelty Audits**: External verification that capabilities aren't derivable from primitives

## Core Philosophical Issue

The council's standard creates a potential paradox:
- If system can do X → designers anticipated X → X not novel
- If system can't do X → no capability demonstrated → fail

This suggests Goal 9 may require:
1. **Design space expansion** (new architectural components)
2. **External novelty verification** (not self-reported)
3. **Scaling law evidence** (capability phase transitions)

## Potential Paths Forward

### Option A: Meta-Architectural Evolution
- System that modifies its own architecture, not just parameters
- Introduces new computational primitives during operation
- Requires careful sandboxing for safety

### Option B: Cross-Domain Transfer Evidence
- Show capability discovered in domain A unexpectedly transfers to domain B
- Demonstrates learning beyond the specific training context
- Harder to argue as "derivable from primitives"

### Option C: External Novelty Oracle
- Build separate system that audits novelty claims
- Attempts to derive "emergent" capabilities from primitives
- Failed derivation = evidence of genuine novelty

### Option D: Scaling Experiments
- Run ECDE at multiple scales
- Look for capability phase transitions
- Compare against baselines (random search, etc.)

## Conclusion

ECDE represents strong capability discovery engineering but the council requires a higher bar:
- **Discovery** (finding what's latent) vs **Invention** (creating genuinely new)
- ECDE does discovery; Goal 9 requires invention

The council's feedback suggests that satisfying Goal 9 may require AGI-level capabilities themselves, creating a potential chicken-and-egg problem for AGI validation.

## Status
- ECDE: Rejected for Goal 9
- RQT: Previously rejected for Goal 9
- Recommendation: Pursue Option D (scaling experiments) or Option B (cross-domain transfer)
