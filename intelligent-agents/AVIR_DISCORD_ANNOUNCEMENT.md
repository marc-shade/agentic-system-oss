# AVIR Discord Announcements

## Short Version (for general channels)

```
🔬 **Open Source Release: AVIR Protocol**

We open-sourced a protocol that solves a fundamental problem in AI eval:
*"An AI grading its own benchmarks is like a student grading their own test."*

**AVIR** enforces cross-provider verification:
• Claude outputs verified by GPT-4/Gemini (never by Claude)
• Double-blind protocol - verifiers don't know the source
• 80%+ consensus required for VERIFIED status
• Ed25519 cryptographic attestation

Supports: Claude, GPT-4, Gemini, Ollama (local models)

🔗 https://github.com/marc-shade/avir-protocol

Looking for researchers to test it. Questions welcome!
```

---

## Technical Version (for ML/AI-safety channels)

```
📢 **AVIR: Cross-Provider Verification Protocol** [MIT License]

Addressing self-verification bias in AI evaluation.

**Problem**: When Claude evaluates Claude (or GPT→GPT), architectural biases and shared failure modes undermine credibility.

**Solution**: AVIR enforces independence through:

1. **Cross-Provider Matrix**
   ```
              Verifier
           Claude  GPT-4  Gemini
   Output  ┌──────┬──────┬──────┐
   Claude  │  ❌  │  ✓   │  ✓   │
   GPT-4   │  ✓   │  ❌  │  ✓   │
   Gemini  │  ✓   │  ✓   │  ❌  │
   ```

2. **Isolation Levels**: Process → Container → TEE

3. **Blind Modes**: Single-blind, Double-blind

4. **Consensus**: ≥80% agreement for VERIFIED

5. **Attestation**: Ed25519 signature chains

**Verification Levels**:
• L1: Basic (1 provider, process)
• L2: Medium (1 provider, container)
• L3: High (2+ providers, single-blind)
• L4: Maximum (3+ providers, double-blind, TEE)

**Repo**: https://github.com/marc-shade/avir-protocol

Seeking collaborators for testing and provider integrations.
```

---

## AI Safety Channel Version

```
🛡️ **AVIR Protocol - Independent AI Verification**

As AI capabilities advance, we need verification methods that don't rely on the systems being evaluated.

**The Problem**: Self-verification creates unfalsifiable capability claims. Claude verifying Claude is a conflict of interest, even unintentionally.

**AVIR Solution**:
- Cross-provider verification (A never grades A)
- Double-blind evaluation (source unknown to verifier)
- Context isolation (process/container/TEE)
- Consensus mechanism (80%+ agreement)
- Cryptographic attestation (Ed25519)

**Why it matters for safety**:
- Independent confirmation before high-stakes deployment
- Audit trail for capability claims
- External parties can verify without trusting the lab

MIT licensed, FAIR compliant.
https://github.com/marc-shade/avir-protocol

Looking for AI safety researchers to stress-test the protocol.
```

---

## Target Discord Servers

1. **Eleuther AI** - Research focus, open-source friendly
2. **ML Collective** - Academic researchers
3. **Latent Space** - AI practitioners and builders
4. **LAION** - Open dataset/model community
5. **Nous Research** - Open-source LLM development
6. **AI Safety Camp** - Safety-focused researchers
7. **MATS** - ML Alignment Theory Scholars
8. **AI Alignment Forum Discord** - Alignment researchers

---

## Response Templates

**"Why not just use multiple runs of the same model?"**
> Multiple runs don't address architectural bias. If Claude has a systematic blind spot, 100 Claude instances will all share it. Cross-provider verification catches these because different architectures have different failure modes.

**"Doesn't this just shift trust to the verification protocol?"**
> Yes, but the protocol is auditable, open-source, and uses cryptographic attestation. Trust in math > trust in a black box model evaluating itself.

**"What about when providers disagree?"**
> Below 80% consensus = CONTESTED status, flagged for human review. This is a feature - it surfaces cases where evaluation is genuinely ambiguous or providers have different capabilities.

**"How do you handle prompt sensitivity?"**
> Double-blind mode means verifiers receive standardized evaluation prompts without knowing the source. This prevents gaming based on known evaluator preferences.
