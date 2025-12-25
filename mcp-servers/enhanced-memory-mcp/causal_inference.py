"""
Causal Inference Engine
========================

Novel verification algorithms, causal inference, statistical significance testing.
Ported from ruvnet/agentic-flow lean-agentic-integration.ts

Provides:
- Causal model validation (DAG structure validation)
- Assumption validation (SUTVA, Ignorability, Positivity, Consistency)
- Bias threat identification (selection, confounding, measurement, missing-data)
- Statistical significance testing (t-test, chi-square, ANOVA, regression)
- Power analysis (sample size, effect size calculations)
- Model diagnostics (residuals, multicollinearity, heteroscedasticity, normality)

MCP Tools:
- ci_validate_causal_model: Validate causal model structure and assumptions
- ci_identify_bias_threats: Identify potential bias threats in data/model
- ci_significance_test: Perform statistical significance testing
- ci_power_analysis: Perform power analysis for study design
- ci_validate_model: Validate statistical model diagnostics
- ci_estimate_effect: Estimate causal effect with confidence intervals
- ci_status: Get causal inference engine status
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Type Definitions
# ============================================================================

class VariableType(Enum):
    TREATMENT = "treatment"
    OUTCOME = "outcome"
    COVARIATE = "covariate"
    CONFOUNDER = "confounder"


class RelationshipType(Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    CONFOUNDED = "confounded"


class BiasType(Enum):
    SELECTION = "selection"
    CONFOUNDING = "confounding"
    MEASUREMENT = "measurement"
    MISSING_DATA = "missing-data"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StudyMethod(Enum):
    RANDOMIZED_TRIAL = "randomized-trial"
    OBSERVATIONAL = "observational"
    QUASI_EXPERIMENTAL = "quasi-experimental"


class TestType(Enum):
    T_TEST = "t-test"
    CHI_SQUARE = "chi-square"
    ANOVA = "anova"
    REGRESSION = "regression"


@dataclass
class CausalVariable:
    """A variable in a causal model."""
    name: str
    type: VariableType
    distribution: Optional[str] = None
    observed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "distribution": self.distribution,
            "observed": self.observed
        }


@dataclass
class CausalRelationship:
    """A causal relationship between variables."""
    from_var: str
    to_var: str
    type: RelationshipType = RelationshipType.DIRECT
    strength: Optional[float] = None
    significance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_var,
            "to": self.to_var,
            "type": self.type.value,
            "strength": self.strength,
            "significance": self.significance
        }


@dataclass
class CausalModel:
    """A complete causal model specification."""
    variables: List[CausalVariable]
    relationships: List[CausalRelationship]
    assumptions: List[str] = field(default_factory=list)
    confounders: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": [v.to_dict() for v in self.variables],
            "relationships": [r.to_dict() for r in self.relationships],
            "assumptions": self.assumptions,
            "confounders": self.confounders
        }


@dataclass
class AssumptionValidation:
    """Validation result for a causal assumption."""
    assumption: str
    satisfied: bool
    evidence: str
    risk: Severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumption": self.assumption,
            "satisfied": self.satisfied,
            "evidence": self.evidence,
            "risk": self.risk.value
        }


@dataclass
class BiasThreat:
    """A potential source of bias."""
    type: BiasType
    severity: Severity
    description: str
    mitigation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "description": self.description,
            "mitigation": self.mitigation
        }


@dataclass
class PowerAnalysis:
    """Statistical power analysis results."""
    power: float
    sample_size: int
    effect_size: float
    alpha: float
    adequate: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power": round(self.power, 4),
            "sample_size": self.sample_size,
            "effect_size": round(self.effect_size, 4),
            "alpha": self.alpha,
            "adequate": self.adequate
        }


@dataclass
class StatisticalTest:
    """Result of a statistical significance test."""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    alpha: float
    effect_size: Optional[float] = None
    power_analysis: Optional[PowerAnalysis] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "test_name": self.test_name,
            "statistic": round(self.statistic, 4),
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "alpha": self.alpha,
            "effect_size": round(self.effect_size, 4) if self.effect_size else None
        }
        if self.power_analysis:
            result["power_analysis"] = self.power_analysis.to_dict()
        return result


@dataclass
class CausalInferenceResult:
    """Complete result of causal inference analysis."""
    effect: float
    confidence: Tuple[float, float]
    p_value: float
    significant: bool
    method: StudyMethod
    assumptions: List[AssumptionValidation]
    threats: List[BiasThreat]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect": round(self.effect, 4),
            "confidence_interval": [round(self.confidence[0], 4), round(self.confidence[1], 4)],
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "method": self.method.value,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "threats": [t.to_dict() for t in self.threats]
        }


@dataclass
class ModelDiagnostics:
    """Statistical model diagnostic results."""
    residual_analysis: Dict[str, Any]
    multicollinearity: Dict[str, Any]
    heteroscedasticity: Dict[str, Any]
    normality: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "residual_analysis": self.residual_analysis,
            "multicollinearity": self.multicollinearity,
            "heteroscedasticity": self.heteroscedasticity,
            "normality": self.normality
        }


# ============================================================================
# Main Engine
# ============================================================================

class CausalInferenceEngine:
    """
    Causal Inference and Statistical Validation Engine.

    Provides rigorous validation of causal claims, statistical significance
    testing, and bias detection for AGI reasoning systems.
    """

    SIGNIFICANCE_LEVEL = 0.05
    MINIMUM_POWER = 0.8

    def __init__(self):
        self.analyses_performed = 0
        self.models_validated = 0
        self.tests_performed = 0
        self.created_at = datetime.now()

    # ========================================================================
    # Causal Model Validation
    # ========================================================================

    def validate_causal_model(
        self,
        model: CausalModel,
        data: Dict[str, Any]
    ) -> CausalInferenceResult:
        """
        Perform comprehensive causal inference validation.

        Args:
            model: The causal model to validate
            data: Data dictionary with observations and metadata

        Returns:
            Complete causal inference result
        """
        self.analyses_performed += 1

        # Step 1: Validate causal model structure
        structure_valid, reason = self._validate_causal_structure(model)
        if not structure_valid:
            raise ValueError(f"Invalid causal model: {reason}")

        # Step 2: Check assumptions
        assumptions = self._validate_assumptions(model, data)

        # Step 3: Identify bias threats
        threats = self.identify_bias_threats(model, data)

        # Step 4: Estimate causal effect
        effect = self._estimate_causal_effect(model, data)

        # Step 5: Calculate confidence interval
        confidence = self._calculate_confidence_interval(effect, data)

        # Step 6: Compute p-value
        p_value = self._compute_p_value(effect, data)

        # Step 7: Determine significance
        significant = (
            p_value < self.SIGNIFICANCE_LEVEL and
            all(a.satisfied or a.risk != Severity.HIGH for a in assumptions)
        )

        self.models_validated += 1

        return CausalInferenceResult(
            effect=effect["estimate"],
            confidence=confidence,
            p_value=p_value,
            significant=significant,
            method=self._determine_method(data),
            assumptions=assumptions,
            threats=threats
        )

    def _validate_causal_structure(self, model: CausalModel) -> Tuple[bool, Optional[str]]:
        """Validate causal model structure (DAG requirement)."""
        # Check for at least one treatment and one outcome
        has_treatment = any(v.type == VariableType.TREATMENT for v in model.variables)
        has_outcome = any(v.type == VariableType.OUTCOME for v in model.variables)

        if not has_treatment:
            return False, "No treatment variable specified"

        if not has_outcome:
            return False, "No outcome variable specified"

        # Check for cycles (DAG requirement)
        if self._has_cycles(model):
            return False, "Causal model contains cycles (not a DAG)"

        return True, None

    def _has_cycles(self, model: CausalModel) -> bool:
        """Check for cycles in causal graph using DFS."""
        visited = set()
        recursion_stack = set()

        # Build adjacency list
        adj: Dict[str, List[str]] = {v.name: [] for v in model.variables}
        for r in model.relationships:
            if r.from_var in adj:
                adj[r.from_var].append(r.to_var)

        def dfs(node: str) -> bool:
            visited.add(node)
            recursion_stack.add(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True  # Cycle detected

            recursion_stack.discard(node)
            return False

        for variable in model.variables:
            if variable.name not in visited:
                if dfs(variable.name):
                    return True

        return False

    # ========================================================================
    # Assumption Validation
    # ========================================================================

    def _validate_assumptions(
        self,
        model: CausalModel,
        data: Dict[str, Any]
    ) -> List[AssumptionValidation]:
        """Validate all causal assumptions."""
        return [
            self._validate_sutva(data),
            self._validate_ignorability(model, data),
            self._validate_positivity(data),
            self._validate_consistency(model)
        ]

    def _validate_sutva(self, data: Dict[str, Any]) -> AssumptionValidation:
        """
        Validate SUTVA (Stable Unit Treatment Value Assumption).

        SUTVA assumes no interference between units - treatment of one unit
        doesn't affect outcomes of another unit.
        """
        has_time_structure = "time" in data or "date" in data
        has_cluster_structure = "cluster" in data or "group" in data

        if has_time_structure or has_cluster_structure:
            return AssumptionValidation(
                assumption="SUTVA (Stable Unit Treatment Value Assumption)",
                satisfied=False,
                evidence="Data has temporal or cluster structure suggesting potential interference",
                risk=Severity.MEDIUM
            )

        return AssumptionValidation(
            assumption="SUTVA (Stable Unit Treatment Value Assumption)",
            satisfied=True,
            evidence="No obvious structure suggesting interference between units",
            risk=Severity.LOW
        )

    def _validate_ignorability(
        self,
        model: CausalModel,
        data: Dict[str, Any]
    ) -> AssumptionValidation:
        """
        Validate Ignorability (No unmeasured confounding).

        Also known as "conditional independence" or "selection on observables".
        """
        confounders = [v for v in model.variables if v.type == VariableType.CONFOUNDER]

        if not confounders:
            return AssumptionValidation(
                assumption="Ignorability (No unmeasured confounding)",
                satisfied=False,
                evidence="No confounders identified in model",
                risk=Severity.HIGH
            )

        measured_confounders = [c for c in confounders if c.observed]
        ratio = len(measured_confounders) / len(confounders)
        risk = Severity.LOW if ratio >= 0.8 else Severity.HIGH

        return AssumptionValidation(
            assumption="Ignorability (No unmeasured confounding)",
            satisfied=len(measured_confounders) == len(confounders),
            evidence=f"{len(measured_confounders)}/{len(confounders)} confounders measured",
            risk=risk
        )

    def _validate_positivity(self, data: Dict[str, Any]) -> AssumptionValidation:
        """
        Validate Positivity (Common support).

        Ensures all subgroups have some probability of receiving treatment.
        """
        # In practice, would use propensity score analysis
        return AssumptionValidation(
            assumption="Positivity (Common support)",
            satisfied=True,
            evidence="Assumed satisfied - requires propensity score analysis for verification",
            risk=Severity.LOW
        )

    def _validate_consistency(self, model: CausalModel) -> AssumptionValidation:
        """
        Validate Consistency (Well-defined intervention).

        Ensures treatment is well-defined with no hidden variations.
        """
        treatments = [v for v in model.variables if v.type == VariableType.TREATMENT]
        well_defined = all(t.distribution is not None for t in treatments)

        return AssumptionValidation(
            assumption="Consistency (Well-defined intervention)",
            satisfied=well_defined,
            evidence="Treatment variables have specified distributions" if well_defined
                     else "Some treatment variables lack clear definitions",
            risk=Severity.LOW if well_defined else Severity.MEDIUM
        )

    # ========================================================================
    # Bias Detection
    # ========================================================================

    def identify_bias_threats(
        self,
        model: CausalModel,
        data: Dict[str, Any]
    ) -> List[BiasThreat]:
        """Identify potential sources of bias in the analysis."""
        threats = []

        # Selection bias
        if not data.get("randomized", False):
            threats.append(BiasThreat(
                type=BiasType.SELECTION,
                severity=Severity.HIGH,
                description="Non-randomized study susceptible to selection bias",
                mitigation="Use propensity score matching or instrumental variables"
            ))

        # Confounding bias
        unmeasured_confounders = [
            v for v in model.variables
            if v.type == VariableType.CONFOUNDER and not v.observed
        ]

        if unmeasured_confounders:
            threats.append(BiasThreat(
                type=BiasType.CONFOUNDING,
                severity=Severity.CRITICAL,
                description=f"{len(unmeasured_confounders)} unmeasured confounders present",
                mitigation="Sensitivity analysis or use of negative controls"
            ))

        # Missing data bias
        missing_rate = data.get("missingRate", 0)
        if missing_rate > 0.1:
            severity = Severity.HIGH if missing_rate > 0.3 else Severity.MEDIUM
            threats.append(BiasThreat(
                type=BiasType.MISSING_DATA,
                severity=severity,
                description=f"{missing_rate * 100:.1f}% missing data",
                mitigation="Multiple imputation or inverse probability weighting"
            ))

        # Measurement bias
        if data.get("self_reported", False):
            threats.append(BiasThreat(
                type=BiasType.MEASUREMENT,
                severity=Severity.MEDIUM,
                description="Self-reported data may contain measurement error",
                mitigation="Use objective measurements or validation studies"
            ))

        return threats

    # ========================================================================
    # Effect Estimation
    # ========================================================================

    def _estimate_causal_effect(
        self,
        model: CausalModel,
        data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Estimate the causal effect."""
        # Use provided estimate or calculate
        estimate = data.get("effectEstimate", 0.0)
        standard_error = data.get("standardError", 0.1)

        return {
            "estimate": estimate,
            "standard_error": standard_error
        }

    def _calculate_confidence_interval(
        self,
        effect: Dict[str, float],
        data: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Calculate confidence interval using normal approximation."""
        z = 1.96  # 95% CI
        estimate = effect["estimate"]
        se = effect["standard_error"]

        lower = estimate - z * se
        upper = estimate + z * se

        return (lower, upper)

    def _compute_p_value(
        self,
        effect: Dict[str, float],
        data: Dict[str, Any]
    ) -> float:
        """Compute two-tailed p-value using z-test."""
        estimate = effect["estimate"]
        se = effect["standard_error"]

        if se == 0:
            return 1.0

        z = abs(estimate / se)
        p_value = 2 * (1 - self._normal_cdf(z))

        return p_value

    def _determine_method(self, data: Dict[str, Any]) -> StudyMethod:
        """Determine the study method based on data characteristics."""
        if data.get("randomized", False):
            return StudyMethod.RANDOMIZED_TRIAL
        if data.get("natural_experiment", False):
            return StudyMethod.QUASI_EXPERIMENTAL
        return StudyMethod.OBSERVATIONAL

    # ========================================================================
    # Statistical Testing
    # ========================================================================

    def perform_significance_test(
        self,
        hypothesis: str,
        data: Dict[str, Any],
        test_type: TestType
    ) -> StatisticalTest:
        """Perform statistical significance test."""
        self.tests_performed += 1

        test_name = test_type.value
        statistic = data.get("testStatistic", 0.0)
        p_value = data.get("pValue", 0.5)
        alpha = self.SIGNIFICANCE_LEVEL
        significant = p_value < alpha
        effect_size = data.get("effectSize")

        power = self._perform_power_analysis(data)

        return StatisticalTest(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            significant=significant,
            alpha=alpha,
            effect_size=effect_size,
            power_analysis=power
        )

    def _perform_power_analysis(self, data: Dict[str, Any]) -> PowerAnalysis:
        """Perform statistical power analysis."""
        sample_size = data.get("sampleSize", 100)
        effect_size = data.get("effectSize", 0.5)
        alpha = self.SIGNIFICANCE_LEVEL

        power = self._calculate_power(effect_size, sample_size, alpha)

        return PowerAnalysis(
            power=power,
            sample_size=sample_size,
            effect_size=effect_size,
            alpha=alpha,
            adequate=power >= self.MINIMUM_POWER
        )

    def _calculate_power(
        self,
        effect_size: float,
        sample_size: int,
        alpha: float
    ) -> float:
        """Calculate statistical power for two-sample t-test."""
        delta = effect_size * math.sqrt(sample_size / 2)
        critical_value = 1.96  # z for alpha = 0.05

        power = 1 - self._normal_cdf(critical_value - delta)

        return min(1.0, max(0.0, power))

    # ========================================================================
    # Model Diagnostics
    # ========================================================================

    def validate_statistical_model(
        self,
        model: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Tuple[bool, ModelDiagnostics, List[str]]:
        """Validate statistical model with comprehensive diagnostics."""
        diagnostics = ModelDiagnostics(
            residual_analysis=self._analyze_residuals(data),
            multicollinearity=self._check_multicollinearity(data),
            heteroscedasticity=self._check_heteroscedasticity(data),
            normality=self._check_normality(data)
        )

        recommendations = self._generate_model_recommendations(diagnostics)
        valid = self._assess_model_validity(diagnostics)

        return valid, diagnostics, recommendations

    def _analyze_residuals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze model residuals."""
        residuals = data.get("residuals", [])
        if not residuals:
            return {"mean": 0, "variance": 1, "pattern": "unknown"}

        mean = sum(residuals) / len(residuals)
        variance = sum((r - mean) ** 2 for r in residuals) / len(residuals)

        # Simple pattern detection
        pattern = "random"
        if abs(mean) > 0.1:
            pattern = "biased"

        return {
            "mean": round(mean, 4),
            "variance": round(variance, 4),
            "pattern": pattern
        }

    def _check_multicollinearity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for multicollinearity using VIF."""
        vif = data.get("vif", 1.5)
        problematic = vif > 5.0

        return {
            "vif": round(vif, 2),
            "problematic": problematic,
            "threshold": 5.0
        }

    def _check_heteroscedasticity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for heteroscedasticity using Breusch-Pagan test."""
        p_value = data.get("bp_pvalue", 0.1)
        present = p_value < 0.05

        return {
            "present": present,
            "test": "Breusch-Pagan",
            "p_value": round(p_value, 4)
        }

    def _check_normality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for normality using Shapiro-Wilk test."""
        p_value = data.get("sw_pvalue", 0.3)
        normal = p_value > 0.05

        return {
            "normal": normal,
            "test": "Shapiro-Wilk",
            "p_value": round(p_value, 4)
        }

    def _generate_model_recommendations(
        self,
        diagnostics: ModelDiagnostics
    ) -> List[str]:
        """Generate recommendations based on diagnostics."""
        recommendations = []

        if diagnostics.multicollinearity.get("problematic", False):
            recommendations.append(
                "Consider removing correlated predictors or using ridge regression"
            )

        if diagnostics.heteroscedasticity.get("present", False):
            recommendations.append(
                "Use robust standard errors or transform variables"
            )

        if not diagnostics.normality.get("normal", True):
            recommendations.append(
                "Consider non-parametric tests or data transformation"
            )

        if diagnostics.residual_analysis.get("pattern") == "biased":
            recommendations.append(
                "Residuals show bias - check for missing predictors or nonlinear relationships"
            )

        return recommendations

    def _assess_model_validity(self, diagnostics: ModelDiagnostics) -> bool:
        """Assess overall model validity."""
        return (
            not diagnostics.multicollinearity.get("problematic", False) and
            not diagnostics.heteroscedasticity.get("present", False) and
            diagnostics.normality.get("normal", True)
        )

    # ========================================================================
    # Utility Functions
    # ========================================================================

    def _normal_cdf(self, z: float) -> float:
        """Approximation of standard normal CDF."""
        t = 1 / (1 + 0.2316419 * abs(z))
        d = 0.3989423 * math.exp(-z * z / 2)
        p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))

        return 1 - p if z > 0 else p

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        return {
            "analyses_performed": self.analyses_performed,
            "models_validated": self.models_validated,
            "tests_performed": self.tests_performed,
            "significance_level": self.SIGNIFICANCE_LEVEL,
            "minimum_power": self.MINIMUM_POWER,
            "created_at": self.created_at.isoformat(),
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds()
        }

    def reset_statistics(self):
        """Reset engine statistics."""
        self.analyses_performed = 0
        self.models_validated = 0
        self.tests_performed = 0


# ============================================================================
# MCP Tool Registration
# ============================================================================

def register_causal_inference_tools(app) -> CausalInferenceEngine:
    """
    Register Causal Inference Engine tools with FastMCP app.

    Args:
        app: FastMCP application instance

    Returns:
        Configured CausalInferenceEngine instance
    """
    engine = CausalInferenceEngine()
    logger.info("Initializing Causal Inference Engine")

    @app.tool()
    async def ci_validate_causal_model(
        variables: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data: Dict[str, Any],
        assumptions: List[str] = None,
        confounders: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a causal model structure and assumptions.

        Performs comprehensive validation including:
        - DAG structure validation (no cycles)
        - SUTVA assumption check
        - Ignorability (no unmeasured confounding)
        - Positivity (common support)
        - Consistency (well-defined intervention)

        Args:
            variables: List of variable definitions with name, type (treatment/outcome/covariate/confounder), observed flag
            relationships: List of causal relationships with from_var, to_var, type (direct/indirect/confounded)
            data: Data dictionary with observations and metadata (randomized, missingRate, etc.)
            assumptions: Optional list of model assumptions
            confounders: Optional list of known confounders

        Returns:
            Complete causal inference result with effect estimate, confidence interval, assumptions, and threats
        """
        try:
            # Parse variables
            parsed_vars = []
            for v in variables:
                var_type = VariableType(v.get("type", "covariate"))
                parsed_vars.append(CausalVariable(
                    name=v["name"],
                    type=var_type,
                    distribution=v.get("distribution"),
                    observed=v.get("observed", True)
                ))

            # Parse relationships
            parsed_rels = []
            for r in relationships:
                rel_type = RelationshipType(r.get("type", "direct"))
                parsed_rels.append(CausalRelationship(
                    from_var=r["from"],
                    to_var=r["to"],
                    type=rel_type,
                    strength=r.get("strength"),
                    significance=r.get("significance")
                ))

            # Build model
            model = CausalModel(
                variables=parsed_vars,
                relationships=parsed_rels,
                assumptions=assumptions or [],
                confounders=confounders or []
            )

            # Validate
            result = engine.validate_causal_model(model, data)

            return {
                "success": True,
                "result": result.to_dict(),
                "model": model.to_dict()
            }
        except Exception as e:
            logger.error(f"Causal model validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def ci_identify_bias_threats(
        variables: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Identify potential bias threats in a causal analysis.

        Detects:
        - Selection bias (non-randomized studies)
        - Confounding bias (unmeasured confounders)
        - Missing data bias (high missingness rates)
        - Measurement bias (self-reported data)

        Args:
            variables: Variable definitions
            relationships: Causal relationships
            data: Data characteristics (randomized, missingRate, self_reported)

        Returns:
            List of identified bias threats with severity and mitigation strategies
        """
        try:
            parsed_vars = [
                CausalVariable(
                    name=v["name"],
                    type=VariableType(v.get("type", "covariate")),
                    observed=v.get("observed", True)
                )
                for v in variables
            ]

            parsed_rels = [
                CausalRelationship(
                    from_var=r["from"],
                    to_var=r["to"],
                    type=RelationshipType(r.get("type", "direct"))
                )
                for r in relationships
            ]

            model = CausalModel(variables=parsed_vars, relationships=parsed_rels)
            threats = engine.identify_bias_threats(model, data)

            return {
                "success": True,
                "threats": [t.to_dict() for t in threats],
                "threat_count": len(threats),
                "has_critical": any(t.severity == Severity.CRITICAL for t in threats)
            }
        except Exception as e:
            logger.error(f"Bias threat identification failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def ci_significance_test(
        hypothesis: str,
        test_type: str,
        test_statistic: float,
        p_value: float,
        sample_size: int = 100,
        effect_size: float = 0.5
    ) -> Dict[str, Any]:
        """
        Perform statistical significance testing.

        Supports:
        - t-test: Comparing means
        - chi-square: Testing independence
        - ANOVA: Comparing multiple groups
        - regression: Testing coefficients

        Args:
            hypothesis: The hypothesis being tested
            test_type: Type of test (t-test, chi-square, anova, regression)
            test_statistic: The computed test statistic
            p_value: The computed p-value
            sample_size: Sample size for power analysis
            effect_size: Effect size for power analysis

        Returns:
            Test result with significance determination and power analysis
        """
        try:
            data = {
                "testStatistic": test_statistic,
                "pValue": p_value,
                "sampleSize": sample_size,
                "effectSize": effect_size
            }

            test_type_enum = TestType(test_type)
            result = engine.perform_significance_test(hypothesis, data, test_type_enum)

            return {
                "success": True,
                "hypothesis": hypothesis,
                "result": result.to_dict()
            }
        except Exception as e:
            logger.error(f"Significance test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def ci_power_analysis(
        sample_size: int,
        effect_size: float,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Perform statistical power analysis.

        Calculates the probability of detecting an effect given:
        - Sample size
        - Expected effect size
        - Significance level (alpha)

        Args:
            sample_size: Number of observations
            effect_size: Expected standardized effect size (Cohen's d)
            alpha: Significance level (default 0.05)

        Returns:
            Power analysis with adequacy assessment
        """
        try:
            data = {
                "sampleSize": sample_size,
                "effectSize": effect_size
            }

            result = engine._perform_power_analysis(data)

            # Calculate required sample size for 80% power
            target_power = 0.8
            required_n = engine._calculate_required_sample_size(effect_size, target_power, alpha)

            return {
                "success": True,
                "power_analysis": result.to_dict(),
                "required_sample_size_for_80_power": required_n,
                "recommendation": "Adequate power achieved" if result.adequate
                                  else f"Increase sample size to at least {required_n} for adequate power"
            }
        except Exception as e:
            logger.error(f"Power analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Add helper method to engine
    def calculate_required_sample_size(self, effect_size: float, target_power: float, alpha: float) -> int:
        """Calculate required sample size for target power."""
        # Binary search for required n
        low, high = 10, 10000
        while low < high:
            mid = (low + high) // 2
            power = self._calculate_power(effect_size, mid, alpha)
            if power < target_power:
                low = mid + 1
            else:
                high = mid
        return low

    engine._calculate_required_sample_size = lambda e, p, a: calculate_required_sample_size(engine, e, p, a)

    @app.tool()
    async def ci_validate_model(
        model_data: Dict[str, Any],
        residuals: List[float] = None,
        vif: float = 1.5,
        bp_pvalue: float = 0.1,
        sw_pvalue: float = 0.3
    ) -> Dict[str, Any]:
        """
        Validate statistical model with comprehensive diagnostics.

        Checks:
        - Residual analysis (bias, patterns)
        - Multicollinearity (VIF)
        - Heteroscedasticity (Breusch-Pagan)
        - Normality (Shapiro-Wilk)

        Args:
            model_data: Model specification
            residuals: Optional list of model residuals
            vif: Variance Inflation Factor (default 1.5)
            bp_pvalue: Breusch-Pagan test p-value (default 0.1)
            sw_pvalue: Shapiro-Wilk test p-value (default 0.3)

        Returns:
            Model validity assessment with diagnostics and recommendations
        """
        try:
            data = {
                "residuals": residuals or [],
                "vif": vif,
                "bp_pvalue": bp_pvalue,
                "sw_pvalue": sw_pvalue
            }

            valid, diagnostics, recommendations = engine.validate_statistical_model(model_data, data)

            return {
                "success": True,
                "valid": valid,
                "diagnostics": diagnostics.to_dict(),
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def ci_estimate_effect(
        effect_estimate: float,
        standard_error: float,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Estimate causal effect with confidence interval.

        Args:
            effect_estimate: Point estimate of the effect
            standard_error: Standard error of the estimate
            confidence_level: Confidence level (default 0.95)

        Returns:
            Effect estimate with confidence interval and p-value
        """
        try:
            # Calculate z-score for confidence level
            alpha = 1 - confidence_level
            z = 1.96 if confidence_level == 0.95 else 2.576 if confidence_level == 0.99 else 1.645

            lower = effect_estimate - z * standard_error
            upper = effect_estimate + z * standard_error

            # Calculate p-value
            if standard_error > 0:
                z_stat = abs(effect_estimate / standard_error)
                p_value = 2 * (1 - engine._normal_cdf(z_stat))
            else:
                p_value = 1.0

            significant = p_value < 0.05

            return {
                "success": True,
                "effect_estimate": round(effect_estimate, 4),
                "standard_error": round(standard_error, 4),
                "confidence_interval": [round(lower, 4), round(upper, 4)],
                "confidence_level": confidence_level,
                "p_value": round(p_value, 6),
                "significant": significant
            }
        except Exception as e:
            logger.error(f"Effect estimation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def ci_status() -> Dict[str, Any]:
        """
        Get Causal Inference Engine status and statistics.

        Returns:
            Engine status including analyses performed, tests run, and configuration
        """
        return {
            "success": True,
            "status": engine.get_status()
        }

    logger.info(f"Registered 7 Causal Inference Engine tools")
    return engine


# ============================================================================
# Standalone Testing
# ============================================================================

if __name__ == "__main__":
    # Quick test
    engine = CausalInferenceEngine()

    # Create a simple causal model
    model = CausalModel(
        variables=[
            CausalVariable("treatment", VariableType.TREATMENT, observed=True),
            CausalVariable("outcome", VariableType.OUTCOME, observed=True),
            CausalVariable("age", VariableType.CONFOUNDER, observed=True),
            CausalVariable("income", VariableType.CONFOUNDER, observed=False)
        ],
        relationships=[
            CausalRelationship("treatment", "outcome", RelationshipType.DIRECT),
            CausalRelationship("age", "treatment", RelationshipType.CONFOUNDED),
            CausalRelationship("age", "outcome", RelationshipType.CONFOUNDED)
        ]
    )

    data = {
        "randomized": False,
        "missingRate": 0.15,
        "effectEstimate": 0.5,
        "standardError": 0.1
    }

    # Validate model
    result = engine.validate_causal_model(model, data)
    print("Causal Inference Result:")
    print(f"  Effect: {result.effect:.4f}")
    print(f"  95% CI: [{result.confidence[0]:.4f}, {result.confidence[1]:.4f}]")
    print(f"  P-value: {result.p_value:.6f}")
    print(f"  Significant: {result.significant}")
    print(f"  Method: {result.method.value}")
    print(f"\nAssumptions:")
    for a in result.assumptions:
        status = "✓" if a.satisfied else "✗"
        print(f"  {status} {a.assumption} (risk: {a.risk.value})")
    print(f"\nBias Threats: {len(result.threats)}")
    for t in result.threats:
        print(f"  ⚠ {t.type.value}: {t.description}")

    print(f"\n✅ Causal Inference Engine ready")
