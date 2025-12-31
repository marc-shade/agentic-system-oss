# AVIR Protocol Tweet Thread

## Thread for @marc_shade

---

**Tweet 1/10 (Hook)**

We've open-sourced AVIR - a protocol that solves a fundamental problem in AI evaluation:

"An AI verifying its own benchmarks is like a student grading their own test."

Here's how we eliminate self-verification bias. Thread

https://github.com/marc-shade/avir-protocol

---

**Tweet 2/10 (The Problem)**

The AI evaluation problem:

- Claude reviews Claude's output
- GPT-4 grades GPT-4's work
- Gemini validates Gemini's claims

This creates an invisible ceiling on trustworthy AI assessment.

AVIR fixes this with cross-provider verification.

---

**Tweet 3/10 (Core Solution)**

How AVIR works:

Multiple AI providers evaluate EACH OTHER's outputs - never their own.

The result? An NxN verification matrix where every cell is an independent assessment.

No provider ever grades itself.

---

**Tweet 4/10 (Double-Blind)**

We go further with double-blind protocol:

Verifiers don't know WHICH provider generated the output they're evaluating.

This prevents:
- Unconscious favoritism
- Optimization for specific evaluators
- Gaming the verification system

---

**Tweet 5/10 (Context Isolation)**

Context pollution is real.

AVIR runs verifications in isolated environments:

L1: Process isolation
L2: Container isolation (5 runs)
L3: Single-blind + multi-provider
L4: Double-blind + TEE (Trusted Execution Environment)

Pick your rigor level.

---

**Tweet 6/10 (Consensus Mechanism)**

How do we determine truth?

Consensus-based verdicts:
- Collect all cross-provider assessments
- Exclude self-verification (diagonal)
- Require ≥80% agreement for VERIFIED status

Disagreement triggers deeper analysis.

---

**Tweet 7/10 (Cryptographic Proof)**

Every AVIR verification produces:

- Ed25519 signed attestation
- Tamper-evident hash chain
- Provider isolation proofs
- Reproducible verification IDs

You can audit any claim back to its source.

---

**Tweet 8/10 (Why This Matters)**

For AGI safety research, this is critical.

We can't trust systems to verify their own capabilities.

AVIR enables:
- Independent replication of AI claims
- Adversarial evaluation without bias
- Trustworthy benchmark results

---

**Tweet 9/10 (Supported Providers)**

Currently supported:

- Claude (Anthropic)
- GPT-4 / Codex (OpenAI)
- Gemini (Google)
- Ollama (local models)

Adding a new provider? ~50 lines of Python.

---

**Tweet 10/10 (Call to Action)**

AVIR is MIT licensed and ready for research use.

We're looking for:
- AI safety researchers to test it
- Labs to run independent verifications
- Contributors to add new providers

Start here: https://github.com/marc-shade/avir-protocol

Let's make AI evaluation trustworthy.

---

## Alt Versions

**Shorter Hook (Tweet 1 alt)**

Open-sourced: AVIR Protocol

Cross-provider AI verification that eliminates self-grading bias.

Claude verifies GPT. GPT verifies Gemini. Gemini verifies Claude.

No AI grades its own work.

https://github.com/marc-shade/avir-protocol

---

**Academic Hook (Tweet 1 alt)**

Announcing AVIR: AI-Verified Independent Replication

A formal protocol for cross-provider verification with:
- Double-blind evaluation
- Cryptographic attestation
- Consensus-based verdicts

Designed for AGI safety research.

Paper + code: https://github.com/marc-shade/avir-protocol

---

## Hashtags (use sparingly)

#AIResearch #AISafety #OpenSource #MachineLearning #AGI #AIEvaluation

---

## Image Suggestions

1. **Verification Matrix**: NxN grid showing Claude/GPT/Gemini with diagonal crossed out
2. **Verification Levels**: L1→L2→L3→L4 pyramid showing increasing rigor
3. **Flow Diagram**: Output → Isolation → Cross-verify → Consensus → Attestation
4. **Before/After**: Self-grading (X) vs AVIR cross-grading (checkmark)
