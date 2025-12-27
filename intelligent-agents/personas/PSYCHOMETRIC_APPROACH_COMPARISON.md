# Psychometric vs Traditional Persona Approaches

## Overview

This document compares our original persona system (`persona_base.py`) with the newly integrated psychometric approach (`psychometric_persona.py`) based on BFI-2 psychological theory from [mrorigo/psychometric-persona-synthesis](https://github.com/mrorigo/psychometric-persona-synthesis).

## Approach Comparison

| Aspect | Original (`persona_base.py`) | Psychometric (`psychometric_persona.py`) |
|--------|------------------------------|------------------------------------------|
| **Trait Source** | Manual enumeration (8 traits) | BFI-2 psychological inventory (60 items → 5 domains) |
| **Scientific Grounding** | Ad-hoc based on intuition | Validated psychological framework with population norms |
| **Trait Correlations** | Independent traits | Correlated sampling via multivariate normal distribution |
| **Occupational Priors** | None | Meta-analytic personality offsets by role |
| **Personality Generation** | Manually specified per persona | Probabilistic sampling with role-based priors |
| **Narrative Output** | Basic system prompt template | Rich natural language personality descriptions |
| **Item-Level Detail** | Domain-level only | 60 specific behavioral descriptors |

## Architecture Diagram

```
Original System                    Psychometric System
─────────────────                  ───────────────────

PersonaType (enum)                 Domain (5 Big Five)
     │                                   │
     ▼                                   ▼
PersonaTrait (8)                   BFI2Item (60)
     │                                   │
     ▼                                   ▼
CommunicationStyle ◄─────────┬─── generate_domain_scores()
     │                       │           │
     ▼                       │           ▼
DecisionFramework ◄──────────┴─── PsychometricProfile
     │                                   │
     ▼                                   ▼
AgentPersona ◄─────────────────── PsychometricPersona
```

## Key Innovations in Psychometric Approach

### 1. Multivariate Normal Sampling
```python
# Population trait correlations (from research)
BIG_FIVE_CORRELATION_MATRIX = [
    [1.00,  0.29, 0.25, -0.34,  0.17],  # Extraversion
    [0.29,  1.00, 0.42, -0.40,  0.19],  # Agreeableness
    [0.25,  0.42, 1.00, -0.43,  0.24],  # Conscientiousness
    [-0.34, -0.40, -0.43, 1.00, -0.22], # Neuroticism
    [0.17,  0.19, 0.24, -0.22,  1.00],  # Openness
]

# Uses Cholesky decomposition for correlated sampling
samples = sample_multivariate_normal(mu, cholesky_L)
```

This ensures that generated personalities are psychologically plausible (e.g., high Extraversion correlates with high Agreeableness, low Neuroticism).

### 2. Occupational Role Priors
```python
OCCUPATIONAL_ROLES = {
    "Orchestrator": RoleMetadata(
        offsets={
            Domain.EXTRAVERSION: 0.3,        # Slightly more extraverted
            Domain.CONSCIENTIOUSNESS: 0.5,   # More conscientious
            Domain.OPENNESS: 0.4,            # More open
        },
        typical_values=["Coordination", "Reliability", "Strategic Thinking"],
    ),
}
```

This applies research-backed personality adjustments for specific roles.

### 3. Hierarchical Score Generation
```
Population Mean (3.0)
    → Role Offset (+0.5 for Orchestrator's Conscientiousness)
        → Multivariate Sampling (respects correlations)
            → Domain Scores (5)
                → Item Scores (60, with noise and reverse-scoring)
                    → Natural Language Narrative
```

### 4. Natural Language Synthesis
```python
# Input: item_scores = {1: 4, 2: 5, 3: 3, ...}
# Output: "You tend to be fairly sociable and very compassionate.
#          People generally describe you as sometimes quiet..."
```

## Mapping to Cluster Nodes

The integration provides pre-defined profiles for our cluster:

| Node | Role | Key Traits | Profile |
|------|------|------------|---------|
| mac-studio | Orchestrator | High C (4.5), High O (4.0) | Strategic, reliable, exploratory |
| macbook-air | Researcher | Very High O (4.8), High A (4.5) | Curious, collaborative, open |
| macbook-pro | Developer | High C (4.3), High O (4.2) | Thorough, focused, creative |
| macpro51 | Builder | Very High C (4.8), Low N (2.2) | Precise, calm, efficient |

## Usage Examples

### Creating from Role
```python
from psychometric_persona import PsychometricPersona, PersonaType

persona = PsychometricPersona.from_role(
    name="Alice",
    persona_type=PersonaType.ORCHESTRATOR,
    role="Orchestrator"
)
```

### Creating for Cluster Node
```python
persona = PsychometricPersona.for_cluster_node("mac-studio")
print(persona.get_psychometric_summary())
# {
#     'role': 'Orchestrator',
#     'domain_scores': {
#         'Conscientiousness': 4.5,
#         'Openness': 4.0,
#         ...
#     },
#     'communication_style': 'analytical',
#     'risk_tolerance': 'medium',
# }
```

### Getting Enhanced System Prompt
```python
prompt = persona.generate_system_prompt()
# Includes:
# - Standard capabilities and constraints
# - PSYCHOMETRIC PROFILE section with domain scores
# - PERSONALITY DESCRIPTION with natural language
```

## When to Use Each Approach

| Use Case | Recommended Approach |
|----------|---------------------|
| Quick prototype agents | Original (`persona_base.py`) |
| Production cluster nodes | Psychometric (consistent personalities) |
| Role-specific agents | Psychometric (role priors) |
| Research on agent personality | Psychometric (validated framework) |
| Simple capability-focused agents | Original (simpler) |
| Multi-agent coordination | Psychometric (diverse but consistent) |

## Implementation Files

| File | Purpose |
|------|---------|
| `psychometric_generator.py` | Core BFI-2 implementation, sampling, narrative |
| `psychometric_persona.py` | Integration with `AgentPersona` base class |
| `persona_base.py` | Original persona system (unchanged) |
| `persona_registry.py` | Registry for all personas (works with both) |

## Future Enhancements

1. **Facet-Level Modeling**: BFI-2 has 15 facets (3 per domain) for finer granularity
2. **Adaptive Personality**: Adjust profiles based on task performance
3. **Multi-Agent Composition**: Optimize team personality mixes
4. **Memory-Informed Evolution**: Learn personality adjustments from experience

## References

- Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2)
- Huang, Zhang, Soto, & Evans - "Designing AI-Agents with Personalities"
- mrorigo/psychometric-persona-synthesis GitHub repository
