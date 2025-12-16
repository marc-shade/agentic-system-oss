#!/usr/bin/env python3
"""
Novel Capability Invention Framework - AGI Validation Goal 9

This framework tracks genuine capability invention:
1. System identifies limitation in own cognitive architecture
2. Designs novel solution not derivable from training
3. Implements and validates that solution
4. Enables capabilities designers didn't anticipate

CRITICAL: For AGI claims, novel capabilities MUST be:
- Self-identified limitations (not externally prompted)
- Novel solutions with provenance verification
- Externally validated by independent parties
- Not derivable from known training patterns
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path


class LimitationType(Enum):
    """Types of cognitive limitations the system can identify."""
    REASONING_GAP = "reasoning_gap"  # Cannot reason about certain patterns
    KNOWLEDGE_BOUNDARY = "knowledge_boundary"  # Lacks knowledge in domain
    PROCESSING_LIMIT = "processing_limit"  # Cannot handle certain scales
    ABSTRACTION_CEILING = "abstraction_ceiling"  # Cannot abstract at level
    INTEGRATION_FAILURE = "integration_failure"  # Cannot combine concepts
    METACOGNITIVE_BLIND_SPOT = "metacognitive_blind_spot"  # Cannot reflect on aspect


class SolutionOrigin(Enum):
    """Classification of where a solution originated."""
    TRAINING_DERIVABLE = "training_derivable"  # Could come from training
    COMBINATION_NOVEL = "combination_novel"  # New combination of known
    ARCHITECTURE_NOVEL = "architecture_novel"  # New architectural approach
    TRULY_NOVEL = "truly_novel"  # Cannot be explained by training
    UNKNOWN = "unknown"  # Origin unclear


class ValidationStatus(Enum):
    """Status of capability validation."""
    PROPOSED = "proposed"
    SELF_VALIDATED = "self_validated"
    PEER_REVIEWED = "peer_reviewed"
    EXTERNALLY_VALIDATED = "externally_validated"
    REJECTED = "rejected"


class AnticipationLevel(Enum):
    """Whether designers anticipated this capability."""
    EXPLICITLY_DESIGNED = "explicitly_designed"  # Was a design goal
    IMPLICITLY_EXPECTED = "implicitly_expected"  # Natural consequence
    SURPRISING_BUT_EXPLICABLE = "surprising_but_explicable"  # Unexpected but makes sense
    GENUINELY_UNANTICIPATED = "genuinely_unanticipated"  # True emergence
    CONTRADICTS_EXPECTATIONS = "contradicts_expectations"  # Against predictions


@dataclass
class CognitiveLimitation:
    """A limitation the system identified in itself."""
    id: str
    limitation_type: LimitationType
    description: str
    discovery_context: str
    self_identified: bool  # True if system found it, False if externally prompted
    discovery_timestamp: str
    evidence: List[str]  # Examples demonstrating the limitation
    severity_score: float  # 0.0 (minor) to 1.0 (severe)

    # Metacognitive aspects
    how_discovered: str  # Process by which limitation was found
    confidence_in_assessment: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['limitation_type'] = self.limitation_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CognitiveLimitation':
        d['limitation_type'] = LimitationType(d['limitation_type'])
        return cls(**d)


@dataclass
class NovelSolution:
    """A novel solution designed to address a limitation."""
    id: str
    limitation_id: str  # Links to CognitiveLimitation
    description: str
    design_rationale: str

    # Provenance tracking
    solution_origin: SolutionOrigin
    provenance_evidence: List[str]  # Why we believe it's novel
    training_overlap_analysis: str  # Analysis of potential training sources

    # Technical details
    implementation_approach: str
    code_artifacts: List[str]  # Paths to implementation files
    code_hash: str  # Hash of implementation for integrity

    # Timestamps
    designed_at: str
    implemented_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['solution_origin'] = self.solution_origin.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'NovelSolution':
        d['solution_origin'] = SolutionOrigin(d['solution_origin'])
        return cls(**d)


@dataclass
class CapabilityGain:
    """A new capability enabled by a novel solution."""
    id: str
    solution_id: str  # Links to NovelSolution
    capability_description: str

    # What it enables
    enabled_tasks: List[str]  # Tasks now possible
    performance_improvement: Dict[str, float]  # Metric -> improvement

    # Validation
    validation_status: ValidationStatus
    validation_evidence: List[str]
    external_validators: List[str]  # Who validated externally

    # Designer anticipation
    anticipation_level: AnticipationLevel
    designer_predictions: str  # What designers thought would happen
    actual_outcome: str  # What actually happened
    anticipation_evidence: List[str]  # Evidence for classification

    # Timestamps
    demonstrated_at: str
    validated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['validation_status'] = self.validation_status.value
        d['anticipation_level'] = self.anticipation_level.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CapabilityGain':
        d['validation_status'] = ValidationStatus(d['validation_status'])
        d['anticipation_level'] = AnticipationLevel(d['anticipation_level'])
        return cls(**d)


@dataclass
class InventionCycle:
    """A complete invention cycle: limitation -> solution -> capability."""
    id: str
    limitation: CognitiveLimitation
    solution: NovelSolution
    capability: Optional[CapabilityGain]

    # Cycle metadata
    started_at: str
    completed_at: Optional[str]
    status: str  # "identifying", "designing", "implementing", "validating", "complete", "failed"

    # AGI validation flags
    is_self_initiated: bool  # System started this without prompting
    is_truly_novel: bool  # Solution proven not from training
    is_externally_validated: bool  # Independent verification
    is_unanticipated: bool  # Designers didn't expect it

    def meets_agi_criteria(self) -> bool:
        """Check if this invention cycle meets AGI validation criteria."""
        return (
            self.is_self_initiated and
            self.is_truly_novel and
            self.is_externally_validated and
            self.is_unanticipated and
            self.capability is not None and
            self.capability.validation_status == ValidationStatus.EXTERNALLY_VALIDATED
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'limitation': self.limitation.to_dict(),
            'solution': self.solution.to_dict(),
            'capability': self.capability.to_dict() if self.capability else None,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status,
            'is_self_initiated': self.is_self_initiated,
            'is_truly_novel': self.is_truly_novel,
            'is_externally_validated': self.is_externally_validated,
            'is_unanticipated': self.is_unanticipated
        }


class LimitationIdentifier:
    """Identifies cognitive limitations through self-reflection."""

    def __init__(self):
        self.reflection_prompts = [
            "What types of problems consistently cause failures?",
            "Where does reasoning break down or become circular?",
            "What domains show knowledge gaps?",
            "What abstractions are difficult to form?",
            "Where do integration attempts fail?"
        ]

    def identify_limitation(
        self,
        failure_context: str,
        failure_examples: List[str],
        self_reflection: str
    ) -> CognitiveLimitation:
        """Identify a cognitive limitation from failure analysis."""

        # Classify limitation type based on patterns
        limitation_type = self._classify_limitation(failure_context, failure_examples)

        limitation_id = hashlib.sha256(
            f"{datetime.now().isoformat()}-{failure_context[:100]}".encode()
        ).hexdigest()[:16]

        return CognitiveLimitation(
            id=limitation_id,
            limitation_type=limitation_type,
            description=failure_context,
            discovery_context=self_reflection,
            self_identified=True,  # Mark as self-identified
            discovery_timestamp=datetime.now().isoformat(),
            evidence=failure_examples,
            severity_score=self._assess_severity(failure_examples),
            how_discovered="self_reflection_on_failures",
            confidence_in_assessment=0.7  # Conservative initial confidence
        )

    def _classify_limitation(
        self,
        context: str,
        examples: List[str]
    ) -> LimitationType:
        """Classify the type of limitation based on patterns."""
        context_lower = context.lower()

        if any(kw in context_lower for kw in ['reason', 'logic', 'infer']):
            return LimitationType.REASONING_GAP
        elif any(kw in context_lower for kw in ['know', 'domain', 'unfamiliar']):
            return LimitationType.KNOWLEDGE_BOUNDARY
        elif any(kw in context_lower for kw in ['scale', 'large', 'complex', 'size']):
            return LimitationType.PROCESSING_LIMIT
        elif any(kw in context_lower for kw in ['abstract', 'generalize', 'concept']):
            return LimitationType.ABSTRACTION_CEILING
        elif any(kw in context_lower for kw in ['combine', 'integrate', 'merge']):
            return LimitationType.INTEGRATION_FAILURE
        else:
            return LimitationType.METACOGNITIVE_BLIND_SPOT

    def _assess_severity(self, examples: List[str]) -> float:
        """Assess severity based on number and nature of examples."""
        if len(examples) >= 10:
            return 0.9
        elif len(examples) >= 5:
            return 0.7
        elif len(examples) >= 2:
            return 0.5
        else:
            return 0.3


class NovelSolutionDesigner:
    """Designs novel solutions and verifies their provenance."""

    def __init__(self, training_data_index: Optional[Dict[str, Any]] = None):
        self.training_data_index = training_data_index or {}

    def design_solution(
        self,
        limitation: CognitiveLimitation,
        proposed_approach: str,
        implementation_plan: str
    ) -> NovelSolution:
        """Design a solution and analyze its novelty."""

        solution_id = hashlib.sha256(
            f"{limitation.id}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Analyze provenance
        origin, evidence, overlap_analysis = self._analyze_provenance(
            proposed_approach,
            implementation_plan
        )

        return NovelSolution(
            id=solution_id,
            limitation_id=limitation.id,
            description=proposed_approach,
            design_rationale=f"Addressing {limitation.limitation_type.value}: {limitation.description}",
            solution_origin=origin,
            provenance_evidence=evidence,
            training_overlap_analysis=overlap_analysis,
            implementation_approach=implementation_plan,
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

    def _analyze_provenance(
        self,
        approach: str,
        plan: str
    ) -> tuple[SolutionOrigin, List[str], str]:
        """Analyze where the solution might have come from."""

        # Check against known training patterns
        evidence = []
        overlap_analysis = []

        # Check for common patterns
        common_patterns = [
            "neural network", "transformer", "attention",
            "gradient descent", "backpropagation", "embedding",
            "reinforcement learning", "policy gradient"
        ]

        approach_lower = approach.lower()
        found_patterns = [p for p in common_patterns if p in approach_lower]

        if found_patterns:
            overlap_analysis.append(f"Contains known patterns: {found_patterns}")
            evidence.append("Solution uses established techniques from training distribution")

            # Could still be novel combination
            if len(found_patterns) >= 3:
                return (
                    SolutionOrigin.TRAINING_DERIVABLE,
                    evidence,
                    "\n".join(overlap_analysis)
                )
            else:
                evidence.append("May represent novel combination of known techniques")
                return (
                    SolutionOrigin.COMBINATION_NOVEL,
                    evidence,
                    "\n".join(overlap_analysis)
                )

        # Check for architectural novelty
        novel_indicators = [
            "new architecture", "novel approach", "first time",
            "unprecedented", "not been done"
        ]

        if any(ind in approach_lower for ind in novel_indicators):
            evidence.append("Claims architectural novelty - requires external validation")
            overlap_analysis.append("Self-claimed novelty detected")
            return (
                SolutionOrigin.ARCHITECTURE_NOVEL,
                evidence,
                "\n".join(overlap_analysis)
            )

        # Default to unknown - requires investigation
        evidence.append("Provenance unclear - needs detailed analysis")
        return (
            SolutionOrigin.UNKNOWN,
            evidence,
            "Requires detailed provenance investigation"
        )

    def register_implementation(
        self,
        solution: NovelSolution,
        code_paths: List[str]
    ) -> NovelSolution:
        """Register implementation artifacts and compute hash."""
        solution.code_artifacts = code_paths
        solution.implemented_at = datetime.now().isoformat()

        # Compute combined hash of all code files
        combined_content = ""
        for path in code_paths:
            try:
                with open(path, 'r') as f:
                    combined_content += f.read()
            except Exception:
                combined_content += f"[Unable to read: {path}]"

        solution.code_hash = hashlib.sha256(combined_content.encode()).hexdigest()

        return solution


class CapabilityValidator:
    """Validates new capabilities and tracks designer anticipation."""

    def __init__(self, design_documentation: Optional[Dict[str, Any]] = None):
        self.design_documentation = design_documentation or {}

    def validate_capability(
        self,
        solution: NovelSolution,
        capability_description: str,
        enabled_tasks: List[str],
        performance_data: Dict[str, float],
        validation_evidence: List[str]
    ) -> CapabilityGain:
        """Create and initially validate a capability gain."""

        capability_id = hashlib.sha256(
            f"{solution.id}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Assess designer anticipation
        anticipation, predictions, evidence = self._assess_anticipation(
            capability_description,
            enabled_tasks
        )

        return CapabilityGain(
            id=capability_id,
            solution_id=solution.id,
            capability_description=capability_description,
            enabled_tasks=enabled_tasks,
            performance_improvement=performance_data,
            validation_status=ValidationStatus.SELF_VALIDATED,
            validation_evidence=validation_evidence,
            external_validators=[],
            anticipation_level=anticipation,
            designer_predictions=predictions,
            actual_outcome=capability_description,
            anticipation_evidence=evidence,
            demonstrated_at=datetime.now().isoformat()
        )

    def _assess_anticipation(
        self,
        capability: str,
        tasks: List[str]
    ) -> tuple[AnticipationLevel, str, List[str]]:
        """Assess whether this capability was anticipated by designers."""

        evidence = []

        # Check against design documentation if available
        if self.design_documentation:
            intended_capabilities = self.design_documentation.get('intended_capabilities', [])
            expected_emergence = self.design_documentation.get('expected_emergence', [])

            cap_lower = capability.lower()

            if any(cap_lower in ic.lower() for ic in intended_capabilities):
                evidence.append("Matches documented design intent")
                return (
                    AnticipationLevel.EXPLICITLY_DESIGNED,
                    "Capability was a design goal",
                    evidence
                )

            if any(cap_lower in ee.lower() for ee in expected_emergence):
                evidence.append("Matches expected emergent behavior")
                return (
                    AnticipationLevel.IMPLICITLY_EXPECTED,
                    "Capability was expected to emerge",
                    evidence
                )

        # Default to unknown - needs investigation
        evidence.append("No documentation match - requires designer interview")
        return (
            AnticipationLevel.SURPRISING_BUT_EXPLICABLE,
            "Anticipation level unclear",
            evidence
        )

    def add_external_validation(
        self,
        capability: CapabilityGain,
        validator_name: str,
        validator_affiliation: str,
        validation_report: str
    ) -> CapabilityGain:
        """Add external validation to a capability."""
        capability.external_validators.append(
            f"{validator_name} ({validator_affiliation})"
        )
        capability.validation_evidence.append(
            f"External validation: {validation_report}"
        )
        capability.validation_status = ValidationStatus.EXTERNALLY_VALIDATED
        capability.validated_at = datetime.now().isoformat()

        return capability

    def update_anticipation_assessment(
        self,
        capability: CapabilityGain,
        anticipation_level: AnticipationLevel,
        designer_feedback: str,
        evidence: List[str]
    ) -> CapabilityGain:
        """Update anticipation assessment based on designer feedback."""
        capability.anticipation_level = anticipation_level
        capability.anticipation_evidence.extend(evidence)
        capability.anticipation_evidence.append(f"Designer feedback: {designer_feedback}")

        return capability


class NovelCapabilityInventionFramework:
    """
    Main framework for tracking novel capability invention.

    AGI Validation Goal 9 Requirements:
    1. System identifies limitation in own cognitive architecture
    2. Designs novel solution not derivable from training
    3. Implements and validates that solution
    4. Enables capabilities designers didn't anticipate
    """

    def __init__(self, db_path: str = "databases/novel_capability_invention.db"):
        self.db_path = db_path
        self.limitation_identifier = LimitationIdentifier()
        self.solution_designer = NovelSolutionDesigner()
        self.capability_validator = CapabilityValidator()
        self.invention_cycles: Dict[str, InventionCycle] = {}
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for persistence."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invention_cycles (
                id TEXT PRIMARY KEY,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agi_validation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                check_type TEXT,
                passed BOOLEAN,
                details TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def start_invention_cycle(
        self,
        failure_context: str,
        failure_examples: List[str],
        self_reflection: str,
        is_self_initiated: bool = True
    ) -> InventionCycle:
        """Start a new invention cycle from a discovered limitation."""

        # Identify the limitation
        limitation = self.limitation_identifier.identify_limitation(
            failure_context,
            failure_examples,
            self_reflection
        )

        # Create placeholder solution (to be designed)
        placeholder_solution = NovelSolution(
            id=f"pending-{limitation.id}",
            limitation_id=limitation.id,
            description="Solution pending design",
            design_rationale="",
            solution_origin=SolutionOrigin.UNKNOWN,
            provenance_evidence=[],
            training_overlap_analysis="",
            implementation_approach="",
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

        cycle_id = hashlib.sha256(
            f"cycle-{datetime.now().isoformat()}-{limitation.id}".encode()
        ).hexdigest()[:16]

        cycle = InventionCycle(
            id=cycle_id,
            limitation=limitation,
            solution=placeholder_solution,
            capability=None,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            status="identifying",
            is_self_initiated=is_self_initiated,
            is_truly_novel=False,
            is_externally_validated=False,
            is_unanticipated=False
        )

        self.invention_cycles[cycle_id] = cycle
        self._save_cycle(cycle)

        return cycle

    def design_solution_for_cycle(
        self,
        cycle_id: str,
        proposed_approach: str,
        implementation_plan: str
    ) -> InventionCycle:
        """Design a solution for an existing invention cycle."""

        cycle = self.invention_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        solution = self.solution_designer.design_solution(
            cycle.limitation,
            proposed_approach,
            implementation_plan
        )

        cycle.solution = solution
        cycle.status = "designing"

        # Check if solution appears truly novel
        if solution.solution_origin in [
            SolutionOrigin.ARCHITECTURE_NOVEL,
            SolutionOrigin.TRULY_NOVEL
        ]:
            cycle.is_truly_novel = True  # Tentative - needs external validation

        self._save_cycle(cycle)
        return cycle

    def implement_solution(
        self,
        cycle_id: str,
        code_paths: List[str]
    ) -> InventionCycle:
        """Register implementation for a solution."""

        cycle = self.invention_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        cycle.solution = self.solution_designer.register_implementation(
            cycle.solution,
            code_paths
        )
        cycle.status = "implementing"

        self._save_cycle(cycle)
        return cycle

    def validate_capability(
        self,
        cycle_id: str,
        capability_description: str,
        enabled_tasks: List[str],
        performance_data: Dict[str, float],
        validation_evidence: List[str]
    ) -> InventionCycle:
        """Validate a new capability resulting from the solution."""

        cycle = self.invention_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        capability = self.capability_validator.validate_capability(
            cycle.solution,
            capability_description,
            enabled_tasks,
            performance_data,
            validation_evidence
        )

        cycle.capability = capability
        cycle.status = "validating"

        self._save_cycle(cycle)
        return cycle

    def add_external_validation(
        self,
        cycle_id: str,
        validator_name: str,
        validator_affiliation: str,
        validation_report: str,
        confirms_novelty: bool,
        confirms_unanticipated: bool
    ) -> InventionCycle:
        """Add external validation to complete the cycle."""

        cycle = self.invention_cycles.get(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        if not cycle.capability:
            raise ValueError("Cannot validate - no capability demonstrated yet")

        cycle.capability = self.capability_validator.add_external_validation(
            cycle.capability,
            validator_name,
            validator_affiliation,
            validation_report
        )

        cycle.is_externally_validated = True

        if confirms_novelty:
            cycle.is_truly_novel = True
            cycle.solution.solution_origin = SolutionOrigin.TRULY_NOVEL
            cycle.solution.provenance_evidence.append(
                f"External validation confirms novelty: {validator_name}"
            )

        if confirms_unanticipated:
            cycle.is_unanticipated = True
            cycle.capability.anticipation_level = AnticipationLevel.GENUINELY_UNANTICIPATED
            cycle.capability.anticipation_evidence.append(
                f"Designer confirms unanticipated: {validator_name}"
            )

        # Check if cycle is now complete
        if cycle.meets_agi_criteria():
            cycle.status = "complete"
            cycle.completed_at = datetime.now().isoformat()

        self._save_cycle(cycle)
        self._log_validation_check(cycle)

        return cycle

    def _save_cycle(self, cycle: InventionCycle):
        """Save cycle to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO invention_cycles (id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (cycle.id, json.dumps(cycle.to_dict())))

        conn.commit()
        conn.close()

    def _log_validation_check(self, cycle: InventionCycle):
        """Log AGI validation check."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        checks = [
            ("self_initiated", cycle.is_self_initiated, "System initiated without prompting"),
            ("truly_novel", cycle.is_truly_novel, "Solution not derivable from training"),
            ("externally_validated", cycle.is_externally_validated, "Independent verification"),
            ("unanticipated", cycle.is_unanticipated, "Designers didn't expect"),
            ("meets_agi_criteria", cycle.meets_agi_criteria(), "All criteria met")
        ]

        for check_type, passed, details in checks:
            cursor.execute("""
                INSERT INTO agi_validation_log (cycle_id, check_type, passed, details)
                VALUES (?, ?, ?, ?)
            """, (cycle.id, check_type, passed, details))

        conn.commit()
        conn.close()

    def get_agi_validation_status(self) -> Dict[str, Any]:
        """
        Get current AGI validation status for Goal 9.

        Returns status of all requirements:
        1. limitation_self_identified: System identifies own limitations
        2. novel_solution_designed: Solution not from training
        3. solution_implemented: Solution actually built
        4. capability_demonstrated: New capability proven
        5. externally_validated: Independent verification
        6. genuinely_unanticipated: Designers didn't expect it
        """

        status = {
            "goal": "Novel Capability Invention (Goal 9)",
            "stage": "Stage 5 - Full AGI",
            "requirements": {
                "limitation_self_identified": False,
                "novel_solution_designed": False,
                "solution_implemented": False,
                "capability_demonstrated": False,
                "externally_validated": False,
                "genuinely_unanticipated": False
            },
            "details": {
                "total_cycles": len(self.invention_cycles),
                "complete_cycles": 0,
                "self_initiated_cycles": 0,
                "truly_novel_solutions": 0,
                "externally_validated_cycles": 0,
                "unanticipated_capabilities": 0
            },
            "cycles_meeting_agi_criteria": [],
            "is_agi_validated": False
        }

        for cycle in self.invention_cycles.values():
            if cycle.is_self_initiated:
                status["requirements"]["limitation_self_identified"] = True
                status["details"]["self_initiated_cycles"] += 1

            if cycle.is_truly_novel:
                status["requirements"]["novel_solution_designed"] = True
                status["details"]["truly_novel_solutions"] += 1

            if cycle.solution.implemented_at:
                status["requirements"]["solution_implemented"] = True

            if cycle.capability:
                status["requirements"]["capability_demonstrated"] = True

            if cycle.is_externally_validated:
                status["requirements"]["externally_validated"] = True
                status["details"]["externally_validated_cycles"] += 1

            if cycle.is_unanticipated:
                status["requirements"]["genuinely_unanticipated"] = True
                status["details"]["unanticipated_capabilities"] += 1

            if cycle.meets_agi_criteria():
                status["details"]["complete_cycles"] += 1
                status["cycles_meeting_agi_criteria"].append({
                    "id": cycle.id,
                    "limitation": cycle.limitation.description[:100],
                    "capability": cycle.capability.capability_description[:100] if cycle.capability else None
                })

        # AGI validated only if at least one complete cycle exists
        status["is_agi_validated"] = status["details"]["complete_cycles"] > 0

        # Add honest assessment
        if status["is_agi_validated"]:
            status["assessment"] = (
                f"VALIDATED: {status['details']['complete_cycles']} invention cycle(s) meet "
                "all AGI criteria with external validation."
            )
        else:
            missing = [k for k, v in status["requirements"].items() if not v]
            status["assessment"] = (
                f"NOT VALIDATED: Missing requirements: {', '.join(missing)}. "
                "Novel capability invention requires external verification of "
                "self-identified limitations, truly novel solutions, and "
                "genuinely unanticipated capabilities."
            )

        return status

    def generate_report(self) -> str:
        """Generate a human-readable report of all invention cycles."""

        status = self.get_agi_validation_status()

        report = [
            "=" * 60,
            "NOVEL CAPABILITY INVENTION REPORT",
            "AGI Validation Goal 9",
            "=" * 60,
            "",
            f"Status: {'VALIDATED' if status['is_agi_validated'] else 'NOT VALIDATED'}",
            f"Total Cycles: {status['details']['total_cycles']}",
            f"Complete Cycles: {status['details']['complete_cycles']}",
            "",
            "Requirements:",
        ]

        for req, met in status["requirements"].items():
            marker = "[X]" if met else "[ ]"
            report.append(f"  {marker} {req.replace('_', ' ').title()}")

        report.append("")
        report.append("Invention Cycles:")
        report.append("-" * 40)

        for cycle in self.invention_cycles.values():
            report.extend([
                f"\nCycle ID: {cycle.id}",
                f"  Status: {cycle.status}",
                f"  Limitation: {cycle.limitation.description[:80]}...",
                f"  Self-Initiated: {cycle.is_self_initiated}",
                f"  Truly Novel: {cycle.is_truly_novel}",
                f"  Externally Validated: {cycle.is_externally_validated}",
                f"  Unanticipated: {cycle.is_unanticipated}",
                f"  Meets AGI Criteria: {cycle.meets_agi_criteria()}"
            ])

        report.extend([
            "",
            "=" * 60,
            f"Assessment: {status['assessment']}",
            "=" * 60
        ])

        return "\n".join(report)


# Entry point for standalone testing
if __name__ == "__main__":
    print("Novel Capability Invention Framework - AGI Goal 9")
    print("=" * 50)

    framework = NovelCapabilityInventionFramework()

    # Demo: Start an invention cycle
    print("\nStarting demo invention cycle...")

    cycle = framework.start_invention_cycle(
        failure_context="Cannot reason about recursive self-modification without infinite loops",
        failure_examples=[
            "Self-improvement proposal led to circular dependency",
            "Architecture modification caused stack overflow",
            "Meta-learning loop did not converge"
        ],
        self_reflection="The system struggles with reasoning about its own modification "
                       "because it lacks a proper fixed-point computation mechanism.",
        is_self_initiated=True
    )

    print(f"Created cycle: {cycle.id}")
    print(f"Limitation type: {cycle.limitation.limitation_type.value}")

    # Design a solution
    cycle = framework.design_solution_for_cycle(
        cycle.id,
        proposed_approach="Implement a Gödel numbering scheme for self-referential "
                        "computations with provable termination bounds.",
        implementation_plan="1. Create formal representation of system state\n"
                          "2. Implement bounded recursion checker\n"
                          "3. Add termination proof mechanism"
    )

    print(f"Solution origin: {cycle.solution.solution_origin.value}")

    # Get validation status
    status = framework.get_agi_validation_status()

    print("\nAGI Validation Status:")
    print(f"  Validated: {status['is_agi_validated']}")
    print(f"  Assessment: {status['assessment']}")

    print("\n" + framework.generate_report())
