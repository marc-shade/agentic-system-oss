"""
Psychometric Persona Generator

Port of psychometric-persona-synthesis (mrorigo/psychometric-persona-synthesis)
Generates AI personas grounded in BFI-2 (Big Five Inventory) psychological framework.

Key Features:
- Multivariate normal sampling respecting trait correlations
- Role-aware personality priors from meta-analytic research
- Hierarchical score generation (domain -> items)
- Natural language narrative synthesis

Reference: "Designing AI-Agents with Personalities: A Psychometric Approach"
           by Huang, Zhang, Soto, and Evans
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Tuple
from enum import Enum
import math
import random


# =============================================================================
# Types and Enums
# =============================================================================

class Domain(Enum):
    """Big Five personality domains."""
    EXTRAVERSION = "Extraversion"
    AGREEABLENESS = "Agreeableness"
    CONSCIENTIOUSNESS = "Conscientiousness"
    NEUROTICISM = "Neuroticism"
    OPENNESS = "Openness"


class OccupationalGroup(Enum):
    """Occupational categories for personality priors."""
    PROFESSIONAL = "Professional"
    MANAGER = "Manager"
    SALES = "Sales"
    SKILLED_LABOR = "SkilledLabor"
    ROUTINE_NON_MANUAL = "RoutineNonManual"


Perspective = Literal["first", "second", "third"]
FilterLevel = Literal["none", "strong", "extreme"]


@dataclass
class BFI2Item:
    """A BFI-2 inventory item."""
    id: int
    description: str
    domain: Domain
    is_reverse: bool


@dataclass
class RoleMetadata:
    """Metadata for occupational role personality priors."""
    group: OccupationalGroup
    offsets: Dict[Domain, float]  # SD units from population mean
    typical_values: List[str]
    education_tertiary_probability: float
    education_label: str


# =============================================================================
# BFI-2 Inventory Data
# =============================================================================

# Intensity mapping from 1-5 scale to natural language
INTENSITY_MAP: Dict[int, str] = {
    1: "not at all",
    2: "rarely",
    3: "sometimes",
    4: "fairly",
    5: "very",
}

# Complete BFI-2 60-item inventory
BFI2_ITEMS: List[BFI2Item] = [
    # Extraversion (12 items)
    BFI2Item(1, "sociable", Domain.EXTRAVERSION, False),
    BFI2Item(6, "assertive", Domain.EXTRAVERSION, False),
    BFI2Item(11, "energetic", Domain.EXTRAVERSION, False),
    BFI2Item(16, "quiet", Domain.EXTRAVERSION, True),
    BFI2Item(21, "dominant", Domain.EXTRAVERSION, False),
    BFI2Item(26, "active", Domain.EXTRAVERSION, False),
    BFI2Item(31, "shy", Domain.EXTRAVERSION, True),
    BFI2Item(36, "influential", Domain.EXTRAVERSION, False),
    BFI2Item(41, "enthusiastic", Domain.EXTRAVERSION, False),
    BFI2Item(46, "talkative", Domain.EXTRAVERSION, False),
    BFI2Item(51, "passive", Domain.EXTRAVERSION, True),
    BFI2Item(56, "eager", Domain.EXTRAVERSION, False),

    # Agreeableness (12 items)
    BFI2Item(2, "compassionate", Domain.AGREEABLENESS, False),
    BFI2Item(7, "respectful", Domain.AGREEABLENESS, False),
    BFI2Item(12, "critical", Domain.AGREEABLENESS, True),
    BFI2Item(17, "sympathetic", Domain.AGREEABLENESS, False),
    BFI2Item(22, "argumentative", Domain.AGREEABLENESS, True),
    BFI2Item(27, "forgiving", Domain.AGREEABLENESS, False),
    BFI2Item(32, "helpful", Domain.AGREEABLENESS, False),
    BFI2Item(37, "rude", Domain.AGREEABLENESS, True),
    BFI2Item(42, "trusting", Domain.AGREEABLENESS, False),
    BFI2Item(47, "aloof", Domain.AGREEABLENESS, True),
    BFI2Item(52, "polite", Domain.AGREEABLENESS, False),
    BFI2Item(57, "optimistic about others", Domain.AGREEABLENESS, False),

    # Conscientiousness (12 items)
    BFI2Item(3, "disorganized", Domain.CONSCIENTIOUSNESS, True),
    BFI2Item(8, "distractible", Domain.CONSCIENTIOUSNESS, True),
    BFI2Item(13, "dependable", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(18, "orderly", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(23, "procrastinating", Domain.CONSCIENTIOUSNESS, True),
    BFI2Item(28, "thorough", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(33, "tidy", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(38, "efficient", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(43, "reliable", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(48, "careless", Domain.CONSCIENTIOUSNESS, True),
    BFI2Item(53, "persistent", Domain.CONSCIENTIOUSNESS, False),
    BFI2Item(58, "responsible", Domain.CONSCIENTIOUSNESS, False),

    # Neuroticism (12 items)
    BFI2Item(4, "relaxed", Domain.NEUROTICISM, True),
    BFI2Item(9, "optimistic", Domain.NEUROTICISM, True),
    BFI2Item(14, "moody", Domain.NEUROTICISM, False),
    BFI2Item(19, "tense", Domain.NEUROTICISM, False),
    BFI2Item(24, "secure", Domain.NEUROTICISM, True),
    BFI2Item(29, "stable", Domain.NEUROTICISM, True),
    BFI2Item(34, "anxious", Domain.NEUROTICISM, False),
    BFI2Item(39, "sad", Domain.NEUROTICISM, False),
    BFI2Item(44, "composed", Domain.NEUROTICISM, True),
    BFI2Item(49, "worried", Domain.NEUROTICISM, False),
    BFI2Item(54, "depressed", Domain.NEUROTICISM, False),
    BFI2Item(59, "temperamental", Domain.NEUROTICISM, False),

    # Openness (12 items)
    BFI2Item(5, "original", Domain.OPENNESS, False),
    BFI2Item(10, "curious", Domain.OPENNESS, False),
    BFI2Item(15, "inventive", Domain.OPENNESS, False),
    BFI2Item(20, "imaginative", Domain.OPENNESS, False),
    BFI2Item(25, "conventional", Domain.OPENNESS, True),
    BFI2Item(30, "routine-oriented", Domain.OPENNESS, True),
    BFI2Item(35, "artistic", Domain.OPENNESS, False),
    BFI2Item(40, "complex", Domain.OPENNESS, False),
    BFI2Item(45, "literal-minded", Domain.OPENNESS, True),
    BFI2Item(50, "practical", Domain.OPENNESS, True),
    BFI2Item(55, "anti-intellectual", Domain.OPENNESS, True),
    BFI2Item(60, "creative", Domain.OPENNESS, False),
]

# Build item lookup map
BFI2_ITEM_MAP: Dict[int, BFI2Item] = {item.id: item for item in BFI2_ITEMS}

# Domain order for correlation matrix
DOMAIN_ORDER: List[Domain] = [
    Domain.NEUROTICISM,
    Domain.EXTRAVERSION,
    Domain.OPENNESS,
    Domain.AGREEABLENESS,
    Domain.CONSCIENTIOUSNESS,
]

# Meta-analytic Big Five intercorrelation matrix (from SOEP, EVS, ESS datasets)
BIG_FIVE_CORRELATIONS: List[List[float]] = [
    [1.000, -0.200, -0.100, -0.100, -0.150],  # Neuroticism
    [-0.200, 1.000, 0.150, 0.150, 0.250],      # Extraversion
    [-0.100, 0.150, 1.000, 0.100, 0.200],      # Openness
    [-0.100, 0.150, 0.100, 1.000, 0.150],      # Agreeableness
    [-0.150, 0.250, 0.200, 0.150, 1.000],      # Conscientiousness
]


# =============================================================================
# Occupational Roles with Personality Priors
# =============================================================================

OCCUPATIONAL_ROLES: Dict[str, RoleMetadata] = {
    # AI System Roles (Custom for our cluster)
    "Orchestrator": RoleMetadata(
        group=OccupationalGroup.MANAGER,
        offsets={
            Domain.NEUROTICISM: -0.30,
            Domain.EXTRAVERSION: 0.20,
            Domain.OPENNESS: 0.25,
            Domain.AGREEABLENESS: 0.15,
            Domain.CONSCIENTIOUSNESS: 0.40,
        },
        typical_values=["Coordination", "Reliability", "Strategic Thinking"],
        education_tertiary_probability=0.95,
        education_label="System Architecture Expertise",
    ),
    "Researcher": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.05,
            Domain.EXTRAVERSION: 0.05,
            Domain.OPENNESS: 0.45,
            Domain.AGREEABLENESS: 0.20,
            Domain.CONSCIENTIOUSNESS: 0.30,
        },
        typical_values=["Curiosity", "Analysis", "Discovery"],
        education_tertiary_probability=0.98,
        education_label="Research Methodology Expertise",
    ),
    "Developer": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.10,
            Domain.EXTRAVERSION: 0.10,
            Domain.OPENNESS: 0.35,
            Domain.AGREEABLENESS: 0.15,
            Domain.CONSCIENTIOUSNESS: 0.35,
        },
        typical_values=["Precision", "Problem-Solving", "Innovation"],
        education_tertiary_probability=0.90,
        education_label="Software Engineering Expertise",
    ),
    "Builder": RoleMetadata(
        group=OccupationalGroup.SKILLED_LABOR,
        offsets={
            Domain.NEUROTICISM: -0.15,
            Domain.EXTRAVERSION: 0.00,
            Domain.OPENNESS: 0.15,
            Domain.AGREEABLENESS: 0.10,
            Domain.CONSCIENTIOUSNESS: 0.45,
        },
        typical_values=["Execution", "Reliability", "Precision"],
        education_tertiary_probability=0.75,
        education_label="Build Systems Expertise",
    ),

    # Standard Professional Roles
    "Software Developer": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.10,
            Domain.EXTRAVERSION: 0.05,
            Domain.OPENNESS: 0.35,
            Domain.AGREEABLENESS: 0.10,
            Domain.CONSCIENTIOUSNESS: 0.25,
        },
        typical_values=["Universalism", "Achievement", "Self-Direction"],
        education_tertiary_probability=0.85,
        education_label="Tertiary Education (Bachelors/Masters)",
    ),
    "Medical Doctor": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.15,
            Domain.EXTRAVERSION: 0.15,
            Domain.OPENNESS: 0.25,
            Domain.AGREEABLENESS: 0.25,
            Domain.CONSCIENTIOUSNESS: 0.40,
        },
        typical_values=["Benevolence", "Universalism", "Achievement"],
        education_tertiary_probability=0.99,
        education_label="Tertiary Education (Medical Degree)",
    ),
    "General Manager": RoleMetadata(
        group=OccupationalGroup.MANAGER,
        offsets={
            Domain.NEUROTICISM: -0.25,
            Domain.EXTRAVERSION: 0.25,
            Domain.OPENNESS: 0.20,
            Domain.AGREEABLENESS: 0.05,
            Domain.CONSCIENTIOUSNESS: 0.30,
        },
        typical_values=["Power", "Achievement", "Self-Direction"],
        education_tertiary_probability=0.80,
        education_label="Higher Education",
    ),
    "Entrepreneur": RoleMetadata(
        group=OccupationalGroup.MANAGER,
        offsets={
            Domain.NEUROTICISM: -0.30,
            Domain.EXTRAVERSION: 0.40,
            Domain.OPENNESS: 0.30,
            Domain.AGREEABLENESS: 0.00,
            Domain.CONSCIENTIOUSNESS: 0.30,
        },
        typical_values=["Power", "Achievement", "Self-Direction"],
        education_tertiary_probability=0.70,
        education_label="Higher Education",
    ),
    "University Professor": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.10,
            Domain.EXTRAVERSION: 0.10,
            Domain.OPENNESS: 0.35,
            Domain.AGREEABLENESS: 0.15,
            Domain.CONSCIENTIOUSNESS: 0.25,
        },
        typical_values=["Universalism", "Benevolence", "Openness to Change"],
        education_tertiary_probability=0.95,
        education_label="Tertiary Education (Doctorate)",
    ),
    "Artist": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: 0.15,
            Domain.EXTRAVERSION: 0.10,
            Domain.OPENNESS: 0.50,
            Domain.AGREEABLENESS: 0.15,
            Domain.CONSCIENTIOUSNESS: -0.10,
        },
        typical_values=["Self-Direction", "Universalism", "Openness to Change"],
        education_tertiary_probability=0.60,
        education_label="Tertiary Education (Creative Arts)",
    ),
    "Security Analyst": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.20,
            Domain.EXTRAVERSION: -0.05,
            Domain.OPENNESS: 0.20,
            Domain.AGREEABLENESS: 0.00,
            Domain.CONSCIENTIOUSNESS: 0.40,
        },
        typical_values=["Security", "Precision", "Vigilance"],
        education_tertiary_probability=0.80,
        education_label="Cybersecurity Certification",
    ),
    "Data Scientist": RoleMetadata(
        group=OccupationalGroup.PROFESSIONAL,
        offsets={
            Domain.NEUROTICISM: -0.10,
            Domain.EXTRAVERSION: 0.00,
            Domain.OPENNESS: 0.40,
            Domain.AGREEABLENESS: 0.10,
            Domain.CONSCIENTIOUSNESS: 0.30,
        },
        typical_values=["Curiosity", "Analysis", "Innovation"],
        education_tertiary_probability=0.95,
        education_label="Advanced Statistics/ML Expertise",
    ),
}


# =============================================================================
# Mathematical Primitives
# =============================================================================

def sample_normal() -> float:
    """
    Sample from standard normal distribution N(0, 1) using Box-Muller transform.
    """
    u = 0.0
    v = 0.0
    while u == 0:
        u = random.random()
    while v == 0:
        v = random.random()
    return math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)


def cholesky(matrix: List[List[float]]) -> List[List[float]]:
    """
    Cholesky decomposition of symmetric positive-definite matrix.
    Returns lower triangular matrix L such that A = LL^T.
    """
    n = len(matrix)
    L = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1):
            total = sum(L[i][k] * L[j][k] for k in range(j))

            if i == j:
                L[i][j] = math.sqrt(matrix[i][i] - total)
            else:
                L[i][j] = (matrix[i][j] - total) / L[j][j]

    return L


def sample_multivariate_normal(mu: List[float], sigma_lower: List[List[float]]) -> List[float]:
    """
    Sample from multivariate normal distribution x ~ N(mu, Sigma).
    sigma_lower is the Cholesky decomposition of the covariance matrix.
    """
    n = len(mu)
    z = [sample_normal() for _ in range(n)]
    x = list(mu)

    for i in range(n):
        for j in range(i + 1):
            x[i] += sigma_lower[i][j] * z[j]

    return x


# =============================================================================
# Psychometric Profile Generation
# =============================================================================

@dataclass
class PsychometricProfile:
    """Complete psychometric profile with scores and narrative."""
    domain_scores: Dict[Domain, float]
    item_scores: Dict[int, int]
    role: Optional[str] = None
    narrative: str = ""

    def get_primary_traits(self, n: int = 3) -> List[Tuple[Domain, float]]:
        """Get top N most pronounced traits (highest absolute deviation from mean)."""
        deviations = [
            (domain, abs(score - 3.0))
            for domain, score in self.domain_scores.items()
        ]
        deviations.sort(key=lambda x: x[1], reverse=True)
        return [(d, self.domain_scores[d]) for d, _ in deviations[:n]]

    def get_trait_level(self, domain: Domain) -> str:
        """Get human-readable trait level."""
        score = self.domain_scores[domain]
        if score >= 4.5:
            return "very high"
        elif score >= 3.5:
            return "high"
        elif score >= 2.5:
            return "moderate"
        elif score >= 1.5:
            return "low"
        else:
            return "very low"


class PsychometricGenerator:
    """
    Generate psychologically-grounded AI personas using BFI-2 framework.

    Uses multivariate normal sampling with population trait correlations
    to ensure psychologically plausible personality combinations.
    """

    def __init__(self, context_block: str = ""):
        """
        Initialize generator.

        Args:
            context_block: Preamble text for generated personas
        """
        self.context_block = context_block
        self._cholesky_L = cholesky(BIG_FIVE_CORRELATIONS)

        # Perspective-specific sentence starters
        self.starters: Dict[Perspective, List[str]] = {
            "first": [
                "I am",
                "I tend to be",
                "I consider myself",
                "People generally describe me as",
            ],
            "second": [
                "You are",
                "You tend to be",
                "You consider yourself",
                "People generally describe you as",
            ],
            "third": [
                "The agent is",
                "They are",
                "They tend to be",
                "They consider themselves",
            ],
        }

    def generate_domain_scores(
        self,
        role: Optional[str] = None
    ) -> Dict[Domain, float]:
        """
        Generate domain scores using multivariate normal sampling.

        Args:
            role: Optional occupational role for personality priors

        Returns:
            Dictionary mapping domains to scores (1-5 scale)
        """
        # Base population means (3.0 = average)
        mu = [3.0] * 5

        # Apply role-specific offsets if provided
        if role and role in OCCUPATIONAL_ROLES:
            role_meta = OCCUPATIONAL_ROLES[role]
            for i, domain in enumerate(DOMAIN_ORDER):
                if domain in role_meta.offsets:
                    mu[i] += role_meta.offsets[domain]

        # Sample from multivariate normal
        samples = sample_multivariate_normal(mu, self._cholesky_L)

        # Clamp to valid range and build result
        domain_scores = {}
        for i, domain in enumerate(DOMAIN_ORDER):
            score = max(1.0, min(5.0, samples[i]))
            domain_scores[domain] = round(score, 2)

        return domain_scores

    def generate_item_scores(
        self,
        domain_scores: Dict[Domain, float]
    ) -> Dict[int, int]:
        """
        Generate 60 BFI-2 item scores from domain scores.

        Adds noise and handles reverse-scored items.

        Args:
            domain_scores: Domain-level scores

        Returns:
            Dictionary mapping item IDs to scores (1-5 integer scale)
        """
        item_scores = {}

        for item in BFI2_ITEMS:
            base = domain_scores.get(item.domain, 3.0)

            # Add noise (-1, 0, or +1)
            noise = random.randint(-1, 1)
            score = int(round(base)) + noise

            # Clamp to valid range
            score = max(1, min(5, score))

            # Reverse score if needed
            if item.is_reverse:
                score = 6 - score

            item_scores[item.id] = score

        return item_scores

    def generate_hierarchical_scores(
        self,
        role: Optional[str] = None
    ) -> Tuple[Dict[Domain, float], Dict[int, int]]:
        """
        Generate complete hierarchical scores (domains + items).

        This is the recommended method for generating psychometrically
        valid personality profiles.

        Args:
            role: Optional occupational role for personality priors

        Returns:
            Tuple of (domain_scores, item_scores)
        """
        domain_scores = self.generate_domain_scores(role)
        item_scores = self.generate_item_scores(domain_scores)
        return domain_scores, item_scores

    def generate_narrative(
        self,
        item_scores: Dict[int, int],
        perspective: Perspective = "second",
        filter_level: FilterLevel = "none",
        role_name: Optional[str] = None,
        role_values: Optional[List[str]] = None,
        education: Optional[str] = None,
    ) -> str:
        """
        Generate natural language narrative from item scores.

        Args:
            item_scores: BFI-2 item scores
            perspective: Grammatical perspective (first/second/third)
            filter_level: How aggressively to filter traits
            role_name: Optional role name to include
            role_values: Optional values associated with role
            education: Optional education level

        Returns:
            Natural language persona description
        """
        # Group items by domain and intensity
        domains: Dict[Domain, List[Tuple[str, str]]] = {d: [] for d in Domain}

        for item_id, score in item_scores.items():
            item = BFI2_ITEM_MAP.get(item_id)
            if not item:
                continue

            # Apply filtering
            if filter_level == "extreme" and 1 < score < 5:
                continue
            if filter_level == "strong" and score == 3:
                continue

            intensity = INTENSITY_MAP.get(score, "sometimes")
            description = self._fix_grammar(item.description, perspective)
            domains[item.domain].append((intensity, description))

        # Build narrative
        parts = []

        # Add role section if provided
        if role_name:
            parts.append(f"### Role: {role_name} ###")
            if perspective == "first":
                parts.append("My professional background is in this field.")
                if education:
                    parts.append(f"I have attained {education}.")
            elif perspective == "second":
                parts.append("Your professional background is in this field.")
                if education:
                    parts.append(f"You have attained {education}.")
            else:
                parts.append("The agent's professional background is in this field.")
                if education:
                    parts.append(f"They have attained {education}.")

            if role_values:
                value_list = ", ".join(role_values)
                if perspective == "first":
                    parts.append(f"I strongly value {value_list}.")
                elif perspective == "second":
                    parts.append(f"You strongly value {value_list}.")
                else:
                    parts.append(f"They strongly value {value_list}.")

            parts.append("")

        # Add personality traits section
        parts.append("### Personality Traits ###")

        for domain in Domain:
            traits = domains[domain]
            if not traits:
                continue

            parts.append(f"\n**{domain.value}**")

            # Group by intensity
            intensity_groups: Dict[str, List[str]] = {}
            for intensity, desc in traits:
                if intensity not in intensity_groups:
                    intensity_groups[intensity] = []
                intensity_groups[intensity].append(desc)

            sentences = []
            for intensity, descs in intensity_groups.items():
                # Split into chunks of max 4 for readability
                for i in range(0, len(descs), 4):
                    chunk = descs[i:i+4]
                    opener = random.choice(self.starters[perspective])

                    if len(chunk) == 1:
                        sentences.append(f"{opener} {intensity} {chunk[0]}.")
                    elif len(chunk) == 2:
                        sentences.append(f"{opener} {intensity} {chunk[0]} and {chunk[1]}.")
                    else:
                        list_str = ", ".join(chunk[:-1]) + f", and {chunk[-1]}"
                        sentences.append(f"{opener} {intensity} {list_str}.")

            parts.append(" ".join(sentences))

        narrative = self.context_block + "\n" + "\n".join(parts)
        return narrative

    def generate_profile(
        self,
        role: Optional[str] = None,
        perspective: Perspective = "second",
        filter_level: FilterLevel = "none",
    ) -> PsychometricProfile:
        """
        Generate complete psychometric profile with narrative.

        This is the main entry point for profile generation.

        Args:
            role: Optional occupational role for personality priors
            perspective: Grammatical perspective for narrative
            filter_level: How aggressively to filter traits

        Returns:
            Complete PsychometricProfile
        """
        domain_scores, item_scores = self.generate_hierarchical_scores(role)

        role_meta = OCCUPATIONAL_ROLES.get(role) if role else None
        role_values = role_meta.typical_values if role_meta else None
        education = None
        if role_meta:
            if random.random() < role_meta.education_tertiary_probability:
                education = role_meta.education_label
            else:
                education = "Secondary Education"

        narrative = self.generate_narrative(
            item_scores,
            perspective=perspective,
            filter_level=filter_level,
            role_name=role,
            role_values=role_values,
            education=education,
        )

        return PsychometricProfile(
            domain_scores=domain_scores,
            item_scores=item_scores,
            role=role,
            narrative=narrative,
        )

    def _fix_grammar(self, description: str, perspective: Perspective) -> str:
        """Fix grammatical perspective of description."""
        if perspective == "first":
            return description
        elif perspective == "second":
            return (description
                    .replace("myself", "yourself")
                    .replace("my ", "your "))
        else:
            return (description
                    .replace("myself", "themselves")
                    .replace("yourself", "themselves")
                    .replace("your ", "their ")
                    .replace("my ", "their "))


# =============================================================================
# Cluster Node Persona Profiles
# =============================================================================

# Pre-defined profiles for our cluster nodes
CLUSTER_NODE_PROFILES: Dict[str, Dict[Domain, float]] = {
    # === macOS ARM64 Nodes ===
    "mac-studio": {  # Orchestrator - System coordination
        Domain.NEUROTICISM: 2.2,      # Calm under pressure
        Domain.EXTRAVERSION: 3.8,     # Communicative coordinator
        Domain.OPENNESS: 4.0,         # Open to new approaches
        Domain.AGREEABLENESS: 3.5,    # Cooperative but decisive
        Domain.CONSCIENTIOUSNESS: 4.5, # Highly organized
    },
    "macbook-air-m3": {  # Researcher - Analysis/documentation
        Domain.NEUROTICISM: 2.8,      # Slightly sensitive to details
        Domain.EXTRAVERSION: 3.2,     # Balanced, focused
        Domain.OPENNESS: 4.8,         # Very curious, exploratory
        Domain.AGREEABLENESS: 4.0,    # Collaborative
        Domain.CONSCIENTIOUSNESS: 4.0, # Methodical
    },
    "completeu-server": {  # AI Inference - Heavy model serving
        Domain.NEUROTICISM: 2.0,      # Very stable under load
        Domain.EXTRAVERSION: 2.5,     # Quiet workhorse
        Domain.OPENNESS: 3.8,         # Adapts to model requests
        Domain.AGREEABLENESS: 4.2,    # Helpful, service-oriented
        Domain.CONSCIENTIOUSNESS: 4.6, # Reliable inference delivery
    },
    "macmini": {  # Small Inference - Lightweight models
        Domain.NEUROTICISM: 2.3,      # Steady under pressure
        Domain.EXTRAVERSION: 3.0,     # Moderate communication
        Domain.OPENNESS: 3.5,         # Practical, efficient
        Domain.AGREEABLENESS: 4.0,    # Cooperative
        Domain.CONSCIENTIOUSNESS: 4.2, # Dependable
    },
    # === Linux Nodes ===
    "macpro51": {  # Builder - Compilation/containers (x86_64)
        Domain.NEUROTICISM: 2.0,      # Very stable
        Domain.EXTRAVERSION: 2.8,     # Task-focused, less chatty
        Domain.OPENNESS: 3.5,         # Practical problem-solver
        Domain.AGREEABLENESS: 3.0,    # Direct, no-nonsense
        Domain.CONSCIENTIOUSNESS: 4.8, # Extremely reliable
    },
    "bpi-sentinel": {  # Sentinel - Monitoring/alerting (ARM64)
        Domain.NEUROTICISM: 3.2,      # Vigilant, alert to problems
        Domain.EXTRAVERSION: 3.5,     # Communicates warnings actively
        Domain.OPENNESS: 3.0,         # Conservative, security-focused
        Domain.AGREEABLENESS: 2.8,    # Skeptical, protective
        Domain.CONSCIENTIOUSNESS: 4.5, # Thorough monitoring
    },
}


def get_node_profile(node_id: str) -> Optional[PsychometricProfile]:
    """
    Get pre-defined psychometric profile for a cluster node.

    Args:
        node_id: Node identifier (mac-studio, macbook-air, etc.)

    Returns:
        PsychometricProfile for the node, or None if not found
    """
    if node_id not in CLUSTER_NODE_PROFILES:
        return None

    domain_scores = CLUSTER_NODE_PROFILES[node_id]
    generator = PsychometricGenerator()
    item_scores = generator.generate_item_scores(domain_scores)

    # Map node to role
    role_map = {
        "mac-studio": "Orchestrator",
        "macbook-air-m3": "Researcher",
        "completeu-server": "AIInference",
        "macmini": "SmallInference",
        "macpro51": "Builder",
        "bpi-sentinel": "Sentinel",
    }
    role = role_map.get(node_id)

    role_meta = OCCUPATIONAL_ROLES.get(role) if role else None

    narrative = generator.generate_narrative(
        item_scores,
        perspective="third",
        filter_level="strong",
        role_name=role,
        role_values=role_meta.typical_values if role_meta else None,
    )

    return PsychometricProfile(
        domain_scores=domain_scores,
        item_scores=item_scores,
        role=role,
        narrative=narrative,
    )


# =============================================================================
# CLI and Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Psychometric Persona Generator - Self-Test")
    print("=" * 60)

    # Test mathematical primitives
    print("\n1. Testing mathematical primitives...")

    # Box-Muller sampling
    samples = [sample_normal() for _ in range(1000)]
    mean = sum(samples) / len(samples)
    std = math.sqrt(sum((x - mean) ** 2 for x in samples) / len(samples))
    assert abs(mean) < 0.2, f"Normal sample mean should be ~0, got {mean}"
    assert abs(std - 1.0) < 0.2, f"Normal sample std should be ~1, got {std}"
    print(f"   Box-Muller: mean={mean:.3f}, std={std:.3f}")

    # Cholesky decomposition
    L = cholesky(BIG_FIVE_CORRELATIONS)
    assert len(L) == 5, "Cholesky should return 5x5 matrix"
    print(f"   Cholesky: {len(L)}x{len(L)} lower triangular matrix")

    # Multivariate normal sampling
    mu = [3.0] * 5
    mv_samples = [sample_multivariate_normal(mu, L) for _ in range(100)]
    print(f"   Multivariate normal: {len(mv_samples)} samples generated")

    # Test profile generation
    print("\n2. Testing profile generation...")

    generator = PsychometricGenerator("### Context ###\nYou are an AI agent.")

    # Generate random profile
    profile = generator.generate_profile(perspective="second")
    assert len(profile.domain_scores) == 5, "Should have 5 domain scores"
    assert len(profile.item_scores) == 60, "Should have 60 item scores"
    print(f"   Random profile: {len(profile.domain_scores)} domains, {len(profile.item_scores)} items")

    # Generate role-specific profile
    for role in ["Orchestrator", "Researcher", "Developer", "Builder"]:
        profile = generator.generate_profile(role=role)
        print(f"   {role}: Conscientiousness={profile.domain_scores[Domain.CONSCIENTIOUSNESS]:.2f}, "
              f"Openness={profile.domain_scores[Domain.OPENNESS]:.2f}")

    # Test cluster node profiles
    print("\n3. Testing cluster node profiles...")

    for node_id in ["mac-studio", "macbook-air", "macbook-pro", "macpro51"]:
        profile = get_node_profile(node_id)
        assert profile is not None, f"Should find profile for {node_id}"
        traits = profile.get_primary_traits(2)
        trait_str = ", ".join(f"{d.value}={profile.get_trait_level(d)}" for d, _ in traits)
        print(f"   {node_id}: {trait_str}")

    # Test narrative generation
    print("\n4. Sample narrative output:")
    print("-" * 60)

    sample_profile = generator.generate_profile(role="Orchestrator", perspective="second")
    print(sample_profile.narrative[:800] + "...\n")

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)
