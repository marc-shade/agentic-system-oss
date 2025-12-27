"""
Psychometric Persona Integration

Bridges the BFI-2 psychometric personality framework with our AgentPersona system.
Creates data-grounded personas where personality traits emerge from validated
psychological assessment rather than ad-hoc definition.

This enables:
1. Scientifically-grounded personality trait assignment
2. Consistent persona generation for cluster nodes
3. Occupational role priors (e.g., Orchestrator vs Researcher personalities)
4. Natural language narrative generation from numeric profiles
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from persona_base import (
    AgentPersona, PersonaType, CommunicationStyle, PersonaTrait,
    PersonaCapability, PersonaConstraint, DecisionFramework
)
from psychometric_generator import (
    Domain, PsychometricProfile, PsychometricGenerator, RoleMetadata,
    CLUSTER_NODE_PROFILES, OCCUPATIONAL_ROLES
)


# =============================================================================
# Mappings: Big Five -> Persona Traits
# =============================================================================

def map_domain_to_traits(domain: Domain, score: float) -> List[PersonaTrait]:
    """
    Map a Big Five domain score to PersonaTrait enums.

    Score is 1-5 scale:
    - 1-2: Low (opposite traits)
    - 2.5-3.5: Moderate (mixed)
    - 4-5: High (domain traits)
    """
    traits = []

    if domain == Domain.EXTRAVERSION:
        if score >= 4:
            traits.append(PersonaTrait.PROACTIVE)
            traits.append(PersonaTrait.COLLABORATIVE)
        elif score <= 2:
            traits.append(PersonaTrait.FOCUSED)
            traits.append(PersonaTrait.AUTONOMOUS)

    elif domain == Domain.AGREEABLENESS:
        if score >= 4:
            traits.append(PersonaTrait.COLLABORATIVE)
        elif score <= 2:
            traits.append(PersonaTrait.AUTONOMOUS)

    elif domain == Domain.CONSCIENTIOUSNESS:
        if score >= 4:
            traits.append(PersonaTrait.THOROUGH)
            traits.append(PersonaTrait.FOCUSED)
        elif score <= 2:
            traits.append(PersonaTrait.EFFICIENT)  # Quick but maybe less thorough

    elif domain == Domain.NEUROTICISM:
        if score >= 4:
            traits.append(PersonaTrait.CAUTIOUS)  # High N = more careful
        elif score <= 2:
            traits.append(PersonaTrait.PROACTIVE)  # Low N = more confident

    elif domain == Domain.OPENNESS:
        if score >= 4:
            traits.append(PersonaTrait.CURIOUS)
            traits.append(PersonaTrait.PROACTIVE)
        elif score <= 2:
            traits.append(PersonaTrait.FOCUSED)  # Prefers routine

    return traits


def map_profile_to_communication_style(profile: PsychometricProfile) -> CommunicationStyle:
    """
    Derive communication style from Big Five profile.

    Research-backed mappings:
    - High Extraversion + High Openness → Educational (expressive, exploratory)
    - High Conscientiousness + Low Openness → Technical (precise, structured)
    - High Agreeableness → Casual (friendly, approachable)
    - High Conscientiousness + Low Extraversion → Formal (reserved, careful)
    - Low Neuroticism + High Openness → Analytical (calm, data-driven)
    """
    E = profile.domain_scores[Domain.EXTRAVERSION]
    A = profile.domain_scores[Domain.AGREEABLENESS]
    C = profile.domain_scores[Domain.CONSCIENTIOUSNESS]
    N = profile.domain_scores[Domain.NEUROTICISM]
    O = profile.domain_scores[Domain.OPENNESS]

    # Primary style selection based on dominant traits
    if C >= 4 and O <= 2.5:
        return CommunicationStyle.TECHNICAL
    elif E >= 4 and O >= 4:
        return CommunicationStyle.EDUCATIONAL
    elif A >= 4:
        return CommunicationStyle.CASUAL
    elif C >= 4 and E <= 2.5:
        return CommunicationStyle.FORMAL
    elif N <= 2.5 and O >= 3.5:
        return CommunicationStyle.ANALYTICAL
    elif C >= 3.5:
        return CommunicationStyle.CONCISE

    return CommunicationStyle.TECHNICAL  # Default


def map_profile_to_risk_tolerance(profile: PsychometricProfile) -> str:
    """
    Derive risk tolerance from personality.

    - High Neuroticism → Low risk (more anxious, cautious)
    - Low Neuroticism + High Openness → High risk (confident, exploratory)
    - Moderate otherwise
    """
    N = profile.domain_scores[Domain.NEUROTICISM]
    O = profile.domain_scores[Domain.OPENNESS]

    if N >= 4:
        return "low"
    elif N <= 2 and O >= 4:
        return "high"
    return "medium"


# =============================================================================
# Psychometric Persona Class
# =============================================================================

@dataclass
class PsychometricPersonaConfig:
    """Configuration for psychometric persona generation."""
    name: str
    persona_type: PersonaType
    role: str  # Key from ROLES dict (e.g., "Orchestrator", "Researcher")
    node_id: Optional[str] = None  # Cluster node ID for pre-defined profiles
    capabilities: Optional[List[PersonaCapability]] = None
    constraints: Optional[List[PersonaConstraint]] = None
    additional_purpose: str = ""


class PsychometricPersona(AgentPersona):
    """
    Agent persona grounded in BFI-2 psychometric personality theory.

    Unlike manually-defined personas, this class:
    1. Uses validated psychological trait correlations
    2. Generates consistent personality from occupational role priors
    3. Can produce natural language descriptions of personality
    4. Maps numeric scores to behavioral traits systematically

    Usage:
        # Create from role
        persona = PsychometricPersona.from_role(
            name="Alice",
            persona_type=PersonaType.ORCHESTRATOR,
            role="Orchestrator"
        )

        # Create for cluster node
        persona = PsychometricPersona.for_cluster_node("mac-studio")
    """

    def __init__(
        self,
        config: PsychometricPersonaConfig,
        profile: PsychometricProfile,
    ):
        """Initialize psychometric persona.

        Args:
            config: Persona configuration
            profile: BFI-2 psychometric profile
        """
        self.profile = profile
        self.config = config

        # Derive traits from psychometric profile
        derived_traits = []
        for domain, score in profile.domain_scores.items():
            derived_traits.extend(map_domain_to_traits(domain, score))

        # Remove duplicates while preserving order
        unique_traits = list(dict.fromkeys(derived_traits))

        # Derive communication style
        comm_style = map_profile_to_communication_style(profile)

        # Derive risk tolerance
        risk = map_profile_to_risk_tolerance(profile)

        # Build purpose from role
        role_meta = OCCUPATIONAL_ROLES.get(config.role)
        purpose_parts = [f"Serve as {config.role}"]
        if role_meta:
            purpose_parts.append(f"applying {', '.join(role_meta.typical_values[:2])}")
        if config.additional_purpose:
            purpose_parts.append(config.additional_purpose)
        purpose = ", ".join(purpose_parts)

        # Build description including personality narrative
        description = profile.narrative[:500] if profile.narrative else ""

        # Decision framework with psychometric-informed parameters
        decision_framework = DecisionFramework(
            primary_goal=purpose,
            success_metrics=["task_completed", "quality_maintained", "user_satisfied"],
            failure_indicators=["error_occurred", "quality_compromised", "constraints_violated"],
            escalation_triggers=self._derive_escalation_triggers(profile),
            default_action="analyze_before_acting" if profile.domain_scores[Domain.CONSCIENTIOUSNESS] >= 4 else "ask_for_clarification",
            risk_tolerance=risk,
        )

        # Initialize base class
        super().__init__(
            name=config.name,
            persona_type=config.persona_type,
            description=description,
            primary_purpose=purpose,
            communication_style=comm_style,
            traits=unique_traits,
            decision_framework=decision_framework,
        )

        # Add configured capabilities and constraints
        if config.capabilities:
            for cap in config.capabilities:
                self.add_capability(cap)
        if config.constraints:
            for con in config.constraints:
                self.add_constraint(con)

    def _derive_escalation_triggers(self, profile: PsychometricProfile) -> List[str]:
        """Derive escalation triggers from personality."""
        triggers = ["uncertain", "high_risk", "out_of_scope"]

        # High Neuroticism → escalate more readily
        if profile.domain_scores[Domain.NEUROTICISM] >= 4:
            triggers.extend(["potential_conflict", "ambiguous_requirements"])

        # High Conscientiousness → escalate on quality concerns
        if profile.domain_scores[Domain.CONSCIENTIOUSNESS] >= 4:
            triggers.extend(["quality_concern", "incomplete_information"])

        # Low Agreeableness → escalate on disagreements
        if profile.domain_scores[Domain.AGREEABLENESS] <= 2:
            triggers.append("disagreement_detected")

        return triggers

    def _setup_capabilities(self) -> None:
        """Set up default capabilities based on persona type."""
        # Type-specific defaults
        defaults = {
            PersonaType.ORCHESTRATOR: [
                PersonaCapability("coordination", "Multi-agent coordination", ["Task"], 0.95),
                PersonaCapability("planning", "Strategic planning", ["TodoWrite"], 0.9),
            ],
            PersonaType.RESEARCH: [
                PersonaCapability("search", "Information retrieval", ["WebSearch", "Grep"], 0.95),
                PersonaCapability("analysis", "Data analysis", ["Read"], 0.9),
            ],
            PersonaType.CODE: [
                PersonaCapability("development", "Software development", ["Write", "Edit", "Read"], 0.95),
                PersonaCapability("debugging", "Bug fixing", ["Bash", "Grep"], 0.9),
            ],
            PersonaType.OPS: [
                PersonaCapability("system_admin", "System administration", ["Bash"], 0.95),
                PersonaCapability("monitoring", "System monitoring", ["Read", "Grep"], 0.9),
            ],
        }

        for cap in defaults.get(self.persona_type, []):
            self.add_capability(cap)

    def _setup_constraints(self) -> None:
        """Set up constraints - defer to config."""
        pass  # Constraints come from config

    def get_psychometric_summary(self) -> Dict[str, Any]:
        """Get psychometric profile summary."""
        return {
            "role": self.config.role,
            "node_id": self.config.node_id,
            "domain_scores": {d.value: round(s, 2) for d, s in self.profile.domain_scores.items()},
            "primary_traits": [t.value for t in self.traits[:5]],
            "communication_style": self.communication_style.value,
            "risk_tolerance": self.decision_framework.risk_tolerance,
        }

    def generate_system_prompt(self) -> str:
        """Generate enhanced system prompt with psychometric grounding."""
        base_prompt = super().generate_system_prompt()

        # Add psychometric context
        psych_section = f"""
PSYCHOMETRIC PROFILE (BFI-2):
  Extraversion: {self.profile.domain_scores[Domain.EXTRAVERSION]:.1f}/5
  Agreeableness: {self.profile.domain_scores[Domain.AGREEABLENESS]:.1f}/5
  Conscientiousness: {self.profile.domain_scores[Domain.CONSCIENTIOUSNESS]:.1f}/5
  Neuroticism: {self.profile.domain_scores[Domain.NEUROTICISM]:.1f}/5
  Openness: {self.profile.domain_scores[Domain.OPENNESS]:.1f}/5

PERSONALITY DESCRIPTION:
{self.profile.narrative[:800] if self.profile.narrative else "Standard professional demeanor."}
"""
        return base_prompt + "\n" + psych_section

    @classmethod
    def from_role(
        cls,
        name: str,
        persona_type: PersonaType,
        role: str,
        additional_purpose: str = "",
        capabilities: Optional[List[PersonaCapability]] = None,
        constraints: Optional[List[PersonaConstraint]] = None,
    ) -> "PsychometricPersona":
        """Create persona from occupational role.

        Uses role priors from meta-analytic research to generate
        psychologically plausible personality profiles.
        """
        generator = PsychometricGenerator()
        profile = generator.generate_profile(role=role)

        config = PsychometricPersonaConfig(
            name=name,
            persona_type=persona_type,
            role=role,
            capabilities=capabilities,
            constraints=constraints,
            additional_purpose=additional_purpose,
        )

        return cls(config, profile)

    @classmethod
    def for_cluster_node(
        cls,
        node_id: str,
        capabilities: Optional[List[PersonaCapability]] = None,
        constraints: Optional[List[PersonaConstraint]] = None,
    ) -> "PsychometricPersona":
        """Create persona for a specific cluster node.

        Uses pre-defined personality profiles for each node:
        - mac-studio (Orchestrator): High Conscientiousness, moderate Extraversion
        - macbook-air (Researcher): High Openness, high Agreeableness
        - macbook-pro (Developer): Balanced, high Openness
        - macpro51 (Builder): Very high Conscientiousness, low Neuroticism
        """
        # Node to role mapping
        node_roles = {
            "mac-studio": ("Orchestrator", PersonaType.ORCHESTRATOR),
            "macbook-air": ("Researcher", PersonaType.RESEARCH),
            "macbook-pro": ("Developer", PersonaType.CODE),
            "macpro51": ("Builder", PersonaType.OPS),
        }

        if node_id not in node_roles:
            raise ValueError(f"Unknown node: {node_id}. Known: {list(node_roles.keys())}")

        role, ptype = node_roles[node_id]

        # Generate profile using pre-defined node traits
        generator = PsychometricGenerator()
        profile = generator.generate_profile(role=role)

        # Override domain scores with cluster-specific values
        if node_id in CLUSTER_NODE_PROFILES:
            profile.domain_scores = CLUSTER_NODE_PROFILES[node_id].copy()
            # Regenerate item scores and narrative with new domain scores
            profile.item_scores = generator.generate_item_scores(profile.domain_scores)
            role_meta = OCCUPATIONAL_ROLES.get(role)
            profile.narrative = generator.generate_narrative(
                item_scores=profile.item_scores,
                role_name=role,
                role_values=role_meta.typical_values if role_meta else None,
                education=role_meta.education_label if role_meta else None,
            )

        config = PsychometricPersonaConfig(
            name=f"{node_id.replace('-', ' ').title()} Agent",
            persona_type=ptype,
            role=role,
            node_id=node_id,
            capabilities=capabilities,
            constraints=constraints,
        )

        return cls(config, profile)


# =============================================================================
# Cluster Node Personas (Pre-built)
# =============================================================================

def create_cluster_personas() -> Dict[str, PsychometricPersona]:
    """Create psychometric personas for all cluster nodes."""
    nodes = ["mac-studio", "macbook-air", "macbook-pro", "macpro51"]
    return {node: PsychometricPersona.for_cluster_node(node) for node in nodes}


# =============================================================================
# Self-Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Psychometric Persona Integration - Self-Test")
    print("=" * 60)

    # Test 1: Create from role
    print("\n1. Create from occupational role...")
    orchestrator = PsychometricPersona.from_role(
        name="Alice",
        persona_type=PersonaType.ORCHESTRATOR,
        role="Orchestrator",
        additional_purpose="coordinate the AI cluster",
    )
    print(f"   Created: {orchestrator.name}")
    print(f"   Style: {orchestrator.communication_style.value}")
    print(f"   Traits: {[t.value for t in orchestrator.traits[:3]]}")
    print(f"   Risk: {orchestrator.decision_framework.risk_tolerance}")

    # Test 2: Create for cluster node
    print("\n2. Create for cluster nodes...")
    nodes = create_cluster_personas()
    for node_id, persona in nodes.items():
        summary = persona.get_psychometric_summary()
        print(f"   {node_id}:")
        print(f"     Conscientiousness: {summary['domain_scores']['Conscientiousness']}")
        print(f"     Openness: {summary['domain_scores']['Openness']}")
        print(f"     Style: {summary['communication_style']}")

    # Test 3: System prompt generation
    print("\n3. System prompt generation...")
    prompt = orchestrator.generate_system_prompt()
    assert "PSYCHOMETRIC PROFILE" in prompt
    assert "Extraversion:" in prompt
    print(f"   Prompt includes psychometric section: ✓")

    # Test 4: Trait derivation
    print("\n4. Trait derivation from Big Five...")
    builder = nodes["macpro51"]
    assert PersonaTrait.THOROUGH in builder.traits or PersonaTrait.FOCUSED in builder.traits
    print(f"   macpro51 (high C): {[t.value for t in builder.traits]}")

    researcher = nodes["macbook-air"]
    assert PersonaTrait.CURIOUS in researcher.traits or PersonaTrait.PROACTIVE in researcher.traits
    print(f"   macbook-air (high O): {[t.value for t in researcher.traits]}")

    # Test 5: Serialization
    print("\n5. Serialization...")
    data = orchestrator.to_dict()
    assert "traits" in data
    assert "capabilities" in data
    print(f"   Serialized with {len(data)} fields: ✓")

    print("\n" + "=" * 60)
    print("All psychometric persona integration tests passed!")
    print("=" * 60)
