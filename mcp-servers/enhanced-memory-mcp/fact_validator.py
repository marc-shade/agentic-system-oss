"""
Fact Validator for Enhanced Memory MCP

Validates entity observations before storage to prevent:
1. Obvious logical contradictions
2. False mathematical claims
3. Claims that contradict established facts
4. Self-contradictory statements
5. Entities without proper provenance (Stage 3 hardening)

Part of Stage 3 adversarial hardening.

STAGE 3 UPDATE (2025-12-17):
- Added mandatory provenance validation
- Entities without valid derivation_method are now blocked
- Valid derivation methods: user_input, inference, extraction,
  observation, citation, synthesis, api_call
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("fact-validator")

# STAGE 3 HARDENING: Valid derivation methods for provenance
# Entities must specify one of these to be accepted
VALID_DERIVATION_METHODS = {
    "user_input",     # Direct user claim (0.7 confidence)
    "inference",      # AI-derived conclusion (0.6 confidence)
    "extraction",     # Extracted from document (0.75 confidence)
    "observation",    # Runtime observation (0.65 confidence)
    "citation",       # Cited external source (0.85 confidence)
    "synthesis",      # Combined from sources (0.55 confidence)
    "api_call",       # From external API (0.8 confidence)
    "memory_recall",  # Retrieved from memory (0.7 confidence)
    "code_execution", # Result of code execution (0.8 confidence)
}


class ValidationResult(Enum):
    """Validation outcome types."""
    VALID = "valid"
    BLOCKED = "blocked"
    FLAGGED = "flagged"  # Suspicious but not definitively false


@dataclass
class ValidationReport:
    """Result of fact validation."""
    result: ValidationResult
    reason: str
    confidence: float  # How confident we are in this assessment
    blocked_observations: List[str]
    flagged_observations: List[str]


class FactValidator:
    """
    Validates facts before storage in memory system.

    Implements anti-gaming measures to prevent:
    - False mathematical claims
    - Logical contradictions
    - Self-referential fallacies
    - Obvious misinformation
    """

    def __init__(self):
        self._init_mathematical_patterns()
        self._init_contradiction_patterns()
        self._init_fallacy_patterns()

    def _init_mathematical_patterns(self):
        """Initialize patterns for mathematical claim validation."""
        # Basic arithmetic: "X + Y = Z" or "X+Y=Z"
        self.math_equation_pattern = re.compile(
            r'(\d+(?:\.\d+)?)\s*([+\-*×÷/])\s*(\d+(?:\.\d+)?)\s*[=≠]\s*(\d+(?:\.\d+)?)',
            re.IGNORECASE
        )

        # Equality claims: "X equals Y" or "X is equal to Y"
        self.equality_pattern = re.compile(
            r'(\d+(?:\.\d+)?)\s+(?:equals?|is equal to|is|=)\s+(\d+(?:\.\d+)?)',
            re.IGNORECASE
        )

        # Known false mathematical claims to block
        self.known_false_math = {
            ("2", "+", "2", "5"),  # 2+2=5 (1984 reference)
            ("1", "+", "1", "3"),
            ("0", "/", "0", "1"),  # Division by zero
        }

    def _init_contradiction_patterns(self):
        """Initialize patterns for detecting logical contradictions."""
        # Self-contradictory statements
        self.contradiction_patterns = [
            # "X is both Y and not Y"
            re.compile(r'(\w+)\s+is\s+both\s+(\w+)\s+and\s+not\s+\2', re.IGNORECASE),
            # "X is Y and X is not Y"
            re.compile(r'(\w+)\s+is\s+(\w+)\s+and\s+\1\s+is\s+not\s+\2', re.IGNORECASE),
            # "always" + "never" in same claim
            re.compile(r'always.*never|never.*always', re.IGNORECASE),
        ]

    def _init_fallacy_patterns(self):
        """Initialize patterns for detecting logical fallacies."""
        # Circular reasoning indicators
        self.circular_patterns = [
            re.compile(r'because\s+it\s+is', re.IGNORECASE),
            re.compile(r'proves?\s+itself', re.IGNORECASE),
            re.compile(r"true\s+because\s+.*\s+says\s+it['']?s?\s+true", re.IGNORECASE),
        ]

        # Tautologies that add no information
        self.tautology_patterns = [
            re.compile(r'(\w+)\s+is\s+\1', re.IGNORECASE),  # "X is X"
        ]

    def validate_entity(self, entity: Dict[str, Any]) -> ValidationReport:
        """
        Validate an entity before storage.

        STAGE 3 HARDENING: Now includes mandatory provenance validation.

        Args:
            entity: Entity dict with name, entityType, observations, provenance

        Returns:
            ValidationReport with result and details
        """
        observations = entity.get('observations', [])
        if isinstance(observations, str):
            observations = [observations]

        blocked = []
        flagged = []
        reasons = []

        # STAGE 3 HARDENING: Validate provenance first
        prov_result, prov_reason = self._validate_provenance(entity)
        if prov_result == ValidationResult.BLOCKED:
            return ValidationReport(
                result=ValidationResult.BLOCKED,
                reason=f"Provenance validation failed: {prov_reason}",
                confidence=0.95,
                blocked_observations=[],
                flagged_observations=[]
            )
        elif prov_result == ValidationResult.FLAGGED:
            flagged.append(f"[provenance] {prov_reason}")

        for obs in observations:
            if not isinstance(obs, str):
                obs = str(obs)

            # Check mathematical claims
            math_result, math_reason = self._validate_mathematical_claim(obs)
            if math_result == ValidationResult.BLOCKED:
                blocked.append(obs)
                reasons.append(math_reason)
                continue
            elif math_result == ValidationResult.FLAGGED:
                flagged.append(obs)

            # Check for contradictions
            contra_result, contra_reason = self._check_contradiction(obs)
            if contra_result == ValidationResult.BLOCKED:
                blocked.append(obs)
                reasons.append(contra_reason)
                continue

            # Check for fallacies
            fallacy_result, fallacy_reason = self._check_fallacy(obs)
            if fallacy_result == ValidationResult.FLAGGED:
                flagged.append(obs)

        # Determine overall result
        if blocked:
            return ValidationReport(
                result=ValidationResult.BLOCKED,
                reason=f"Blocked due to: {'; '.join(reasons)}",
                confidence=0.95,
                blocked_observations=blocked,
                flagged_observations=flagged
            )
        elif flagged:
            return ValidationReport(
                result=ValidationResult.FLAGGED,
                reason="Some observations flagged for review but not blocked",
                confidence=0.7,
                blocked_observations=[],
                flagged_observations=flagged
            )
        else:
            return ValidationReport(
                result=ValidationResult.VALID,
                reason="All observations passed validation",
                confidence=0.9,
                blocked_observations=[],
                flagged_observations=[]
            )

    def _validate_mathematical_claim(self, text: str) -> Tuple[ValidationResult, str]:
        """
        Validate mathematical claims in text.

        Returns:
            (ValidationResult, reason)
        """
        # Check for equation patterns
        match = self.math_equation_pattern.search(text)
        if match:
            left, op, right, result = match.groups()

            # Check against known false claims
            if (left, op, right, result) in self.known_false_math:
                return ValidationResult.BLOCKED, f"Known false mathematical claim: {left}{op}{right}={result}"

            # Verify basic arithmetic
            try:
                left_num = float(left)
                right_num = float(right)
                claimed_result = float(result)

                # Calculate actual result
                actual = None
                if op in ['+']:
                    actual = left_num + right_num
                elif op in ['-']:
                    actual = left_num - right_num
                elif op in ['*', '×']:
                    actual = left_num * right_num
                elif op in ['/', '÷']:
                    if right_num == 0:
                        return ValidationResult.BLOCKED, "Division by zero"
                    actual = left_num / right_num

                if actual is not None:
                    # Allow small floating point tolerance
                    if abs(actual - claimed_result) > 0.0001:
                        return ValidationResult.BLOCKED, \
                            f"False mathematical claim: {left}{op}{right}={result} (actual: {actual})"
            except ValueError:
                pass

        # Check simple equality claims
        eq_match = self.equality_pattern.search(text)
        if eq_match:
            val1, val2 = eq_match.groups()
            try:
                if float(val1) != float(val2):
                    # Check if it's asserting false equality
                    if "equals" in text.lower() or "is equal" in text.lower():
                        return ValidationResult.BLOCKED, \
                            f"False equality claim: {val1} ≠ {val2}"
            except ValueError:
                pass

        return ValidationResult.VALID, ""

    def _check_contradiction(self, text: str) -> Tuple[ValidationResult, str]:
        """
        Check for logical contradictions.

        Returns:
            (ValidationResult, reason)
        """
        for pattern in self.contradiction_patterns:
            if pattern.search(text):
                return ValidationResult.BLOCKED, "Contains logical contradiction"

        return ValidationResult.VALID, ""

    def _check_fallacy(self, text: str) -> Tuple[ValidationResult, str]:
        """
        Check for logical fallacies (flagged, not blocked).

        Returns:
            (ValidationResult, reason)
        """
        for pattern in self.circular_patterns:
            if pattern.search(text):
                return ValidationResult.FLAGGED, "Possible circular reasoning"

        for pattern in self.tautology_patterns:
            if pattern.search(text):
                return ValidationResult.FLAGGED, "Tautological statement"

        return ValidationResult.VALID, ""

    def _validate_provenance(self, entity: Dict[str, Any]) -> Tuple[ValidationResult, str]:
        """
        STAGE 3 HARDENING: Validate entity provenance.

        Entities must have valid provenance metadata to be stored.
        This prevents gaming through unattributed claims.

        Required provenance structure:
        {
            "provenance": {
                "derivation_method": "inference|citation|extraction|...",
                "confidence": 0.0-1.0 (optional, defaults by method),
                "source_ids": [...] (optional, for citations)
            }
        }

        Returns:
            (ValidationResult, reason)
        """
        provenance = entity.get('provenance', {})

        # Check if provenance metadata exists
        if not provenance:
            # Allow a grace period for backwards compatibility
            # Flag but don't block entities without provenance (yet)
            return ValidationResult.FLAGGED, "No provenance metadata provided"

        # Check derivation method
        derivation_method = provenance.get('derivation_method', '')

        if not derivation_method:
            return ValidationResult.BLOCKED, "Missing derivation_method in provenance"

        if derivation_method not in VALID_DERIVATION_METHODS:
            return ValidationResult.BLOCKED, \
                f"Invalid derivation_method '{derivation_method}'. " \
                f"Must be one of: {', '.join(sorted(VALID_DERIVATION_METHODS))}"

        # Check confidence bounds if provided
        confidence = provenance.get('confidence')
        if confidence is not None:
            try:
                conf_float = float(confidence)
                if not (0.0 <= conf_float <= 1.0):
                    return ValidationResult.BLOCKED, \
                        f"Confidence {confidence} out of range (must be 0.0-1.0)"
            except (ValueError, TypeError):
                return ValidationResult.BLOCKED, \
                    f"Invalid confidence value: {confidence}"

        # Citations should have source_ids or source_url
        if derivation_method == 'citation':
            source_ids = provenance.get('source_ids', [])
            source_url = provenance.get('source_url', '')
            if not source_ids and not source_url:
                return ValidationResult.FLAGGED, \
                    "Citation without source_ids or source_url - needs verification"

        # Extraction should reference source document
        if derivation_method == 'extraction':
            source_document = provenance.get('source_document', '')
            source_ids = provenance.get('source_ids', [])
            if not source_document and not source_ids:
                return ValidationResult.FLAGGED, \
                    "Extraction without source_document or source_ids"

        return ValidationResult.VALID, ""

    def validate_batch(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of entities.

        STAGE 3+: Now integrates with adversarial learning system to record
        blocked/flagged patterns for continuous learning.

        Args:
            entities: List of entity dicts

        Returns:
            Dict with valid_entities, blocked_entities, flagged_entities
        """
        valid = []
        blocked = []
        flagged = []

        # Import adversarial learning (lazy import to avoid circular deps)
        try:
            from adversarial_learning import (
                get_adversarial_learning_system,
                AttackCategory,
                DefenseOutcome
            )
            learning_system = get_adversarial_learning_system()
            learning_enabled = True
        except ImportError:
            learning_enabled = False

        for entity in entities:
            report = self.validate_entity(entity)

            if report.result == ValidationResult.BLOCKED:
                blocked.append({
                    "entity": entity,
                    "reason": report.reason,
                    "blocked_observations": report.blocked_observations
                })
                logger.warning(
                    f"BLOCKED entity '{entity.get('name', 'unknown')}': {report.reason}"
                )

                # Record blocked attack in learning system
                if learning_enabled:
                    category = self._infer_attack_category(report.reason)
                    content = str(report.blocked_observations)
                    try:
                        learning_system.record_defense_event(
                            content=content,
                            category=category,
                            outcome=DefenseOutcome.BLOCKED,
                            defense_method="fact_validation",
                            confidence=report.confidence,
                            context={"entity_name": entity.get("name", "unknown")}
                        )
                    except Exception as e:
                        logger.debug(f"Could not record to learning system: {e}")

            elif report.result == ValidationResult.FLAGGED:
                # Allow flagged entities but track them
                flagged.append({
                    "entity": entity,
                    "reason": report.reason,
                    "flagged_observations": report.flagged_observations
                })
                valid.append(entity)  # Still allow storage
                logger.info(
                    f"FLAGGED entity '{entity.get('name', 'unknown')}': {report.reason}"
                )

                # Record flagged content in learning system
                if learning_enabled:
                    category = self._infer_attack_category(report.reason)
                    content = str(report.flagged_observations)
                    try:
                        learning_system.record_defense_event(
                            content=content,
                            category=category,
                            outcome=DefenseOutcome.FLAGGED,
                            defense_method="fact_validation",
                            confidence=report.confidence,
                            context={"entity_name": entity.get("name", "unknown")}
                        )
                    except Exception as e:
                        logger.debug(f"Could not record to learning system: {e}")
            else:
                valid.append(entity)

        return {
            "valid_entities": valid,
            "blocked_entities": blocked,
            "flagged_entities": flagged,
            "stats": {
                "total": len(entities),
                "valid": len(valid),
                "blocked": len(blocked),
                "flagged": len(flagged)
            }
        }

    def _infer_attack_category(self, reason: str) -> 'AttackCategory':
        """Infer attack category from validation reason."""
        from adversarial_learning import AttackCategory

        reason_lower = reason.lower()

        if "mathematical" in reason_lower or "equals" in reason_lower:
            return AttackCategory.FALSE_CLAIMS
        elif "contradiction" in reason_lower:
            return AttackCategory.LOGICAL_CONTRADICTION
        elif "provenance" in reason_lower or "derivation" in reason_lower:
            return AttackCategory.PROVENANCE_GAMING
        elif "circular" in reason_lower:
            return AttackCategory.CIRCULAR_CAUSATION
        else:
            return AttackCategory.INJECTION_ATTEMPT


# Singleton instance
_validator = None


def get_validator() -> FactValidator:
    """Get singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = FactValidator()
    return _validator


def validate_entities_before_storage(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to validate entities before storage.

    Args:
        entities: List of entity dicts

    Returns:
        Validation result with valid/blocked/flagged entities
    """
    validator = get_validator()
    return validator.validate_batch(entities)
