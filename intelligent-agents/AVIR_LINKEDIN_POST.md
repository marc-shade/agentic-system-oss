# AVIR Protocol LinkedIn Post

## Post for Marc Shade / 2 Acre Studios

---

### Main Post

**An AI verifying its own benchmarks is like a student grading their own test.**

This fundamental problem in AI evaluation has been largely ignored. Until now.

I'm excited to announce that we've open-sourced the AVIR Protocol (AI-Verified Independent Replication) - a framework designed to eliminate self-verification bias in AI systems.

**The Problem**

When Claude evaluates Claude's output, or GPT-4 grades GPT-4's work, we introduce systematic bias that undermines the credibility of AI evaluation. This matters especially as we approach more capable AI systems where trustworthy assessment becomes critical.

**How AVIR Works**

AVIR implements cross-provider verification where multiple AI providers evaluate each other's outputs - never their own. The core principles:

1. **Cross-Provider Verification**: Claude evaluates GPT. GPT evaluates Gemini. Gemini evaluates Claude. The diagonal of the verification matrix (self-assessment) is always excluded.

2. **Double-Blind Protocol**: Verifiers don't know which provider generated the output they're evaluating, preventing unconscious favoritism or optimization for specific evaluators.

3. **Context Isolation**: Verifications run in isolated environments ranging from process-level isolation (L1) to Trusted Execution Environments (L4), preventing context pollution.

4. **Consensus-Based Verdicts**: Results require 80%+ agreement across independent assessments. Disagreement triggers deeper analysis rather than being averaged away.

5. **Cryptographic Attestation**: Every verification produces Ed25519 signed attestations with tamper-evident hash chains. You can audit any claim back to its source.

**Verification Levels**

- L1: Single provider, single run (basic sanity check)
- L2: Single provider, 5 runs in container (consistency)
- L3: 2+ providers with single-blind verification (independence)
- L4: 3+ providers with double-blind + TEE isolation (maximum rigor)

**Currently Supported Providers**

- Claude (Anthropic)
- GPT-4 / Codex (OpenAI)
- Gemini (Google)
- Ollama (local/open-source models)

Adding new providers requires approximately 50 lines of Python.

**Why This Matters**

For AGI safety research, we cannot rely on systems verifying their own capabilities. AVIR provides a principled approach to independent replication that scales with AI capability advancement.

The protocol is MIT licensed and designed for research use. We're actively seeking:

- AI safety researchers to test and validate the approach
- Research labs to run independent verifications
- Contributors to extend provider support and isolation mechanisms

Repository: https://github.com/marc-shade/avir-protocol

I'd welcome feedback from the AI research community on this approach. What verification challenges have you encountered in your work?

---

### Shorter Version (if needed)

**An AI verifying its own benchmarks is like a student grading their own test.**

We've open-sourced AVIR - a protocol for cross-provider AI verification that eliminates self-assessment bias.

How it works:
- Multiple AI providers evaluate each other (never themselves)
- Double-blind protocol prevents favoritism
- Consensus requires 80%+ agreement
- Cryptographic attestation for auditability

Supported: Claude, GPT-4, Gemini, Ollama

Designed for AGI safety research where trustworthy evaluation matters most.

MIT licensed: https://github.com/marc-shade/avir-protocol

Looking for researchers and labs to test this approach. What verification challenges have you faced?

---

### Hashtags (add at end)

#AIResearch #AISafety #OpenSource #MachineLearning #AGI #AIEvaluation #Anthropic #OpenAI #Google #Research

---

### Suggested Image

Create a simple diagram showing:

```
       AVIR Verification Matrix

           Claude  GPT-4  Gemini
Claude       X       v       v
GPT-4        v       X       v
Gemini       v       v       X

X = Excluded (no self-grading)
v = Cross-verification
```

Or a flow diagram:

```
Output Generation --> Context Isolation --> Cross-Provider Verification --> Consensus (80%+) --> Cryptographic Attestation
```

---

### Engagement Tips

1. Post during business hours (Tue-Thu, 9-11am)
2. Respond to comments within first hour
3. Tag relevant researchers/organizations if appropriate
4. Share to relevant LinkedIn groups (AI Safety, ML Research)
