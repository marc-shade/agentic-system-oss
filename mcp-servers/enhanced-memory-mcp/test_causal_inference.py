#!/usr/bin/env python3
"""
Comprehensive tests for Causal Inference Engine.

Tests cover:
- Causal model structure validation
- DAG cycle detection
- Assumption validation (SUTVA, Ignorability, Positivity, Consistency)
- Bias threat identification
- Statistical significance testing
- Power analysis
- Model diagnostics
- Effect estimation
- MCP tool registration
"""

import sys
import math
from datetime import datetime

# Test framework
class TestResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message

def run_tests():
    results = []

    # Import the module
    try:
        from causal_inference import (
            CausalInferenceEngine,
            CausalModel,
            CausalVariable,
            CausalRelationship,
            VariableType,
            RelationshipType,
            BiasType,
            Severity,
            TestType,
            StudyMethod,
            register_causal_inference_tools
        )
        results.append(TestResult("Import Module", True))
    except Exception as e:
        results.append(TestResult("Import Module", False, str(e)))
        return results

    # Test 1: Basic Initialization
    try:
        engine = CausalInferenceEngine()
        assert engine.analyses_performed == 0
        assert engine.models_validated == 0
        assert engine.SIGNIFICANCE_LEVEL == 0.05
        assert engine.MINIMUM_POWER == 0.8
        results.append(TestResult("Basic Initialization", True))
    except Exception as e:
        results.append(TestResult("Basic Initialization", False, str(e)))

    # Test 2: Valid Causal Model
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME),
                CausalVariable("age", VariableType.CONFOUNDER, observed=True)
            ],
            relationships=[
                CausalRelationship("treatment", "outcome", RelationshipType.DIRECT),
                CausalRelationship("age", "treatment"),
                CausalRelationship("age", "outcome")
            ]
        )
        data = {"randomized": True, "effectEstimate": 0.5, "standardError": 0.1}
        result = engine.validate_causal_model(model, data)
        assert result is not None
        assert result.effect == 0.5
        assert result.significant  # p < 0.05 for effect/SE = 5
        assert result.method == StudyMethod.RANDOMIZED_TRIAL
        results.append(TestResult("Valid Causal Model", True))
    except Exception as e:
        results.append(TestResult("Valid Causal Model", False, str(e)))

    # Test 3: Model Missing Treatment
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("outcome", VariableType.OUTCOME)
            ],
            relationships=[]
        )
        error_caught = False
        try:
            engine.validate_causal_model(model, {})
        except ValueError as ve:
            error_caught = "No treatment variable" in str(ve)
        assert error_caught
        results.append(TestResult("Model Missing Treatment", True))
    except Exception as e:
        results.append(TestResult("Model Missing Treatment", False, str(e)))

    # Test 4: Model Missing Outcome
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT)
            ],
            relationships=[]
        )
        error_caught = False
        try:
            engine.validate_causal_model(model, {})
        except ValueError as ve:
            error_caught = "No outcome variable" in str(ve)
        assert error_caught
        results.append(TestResult("Model Missing Outcome", True))
    except Exception as e:
        results.append(TestResult("Model Missing Outcome", False, str(e)))

    # Test 5: DAG Cycle Detection
    try:
        engine = CausalInferenceEngine()
        # Model with cycle: A -> B -> C -> A
        model = CausalModel(
            variables=[
                CausalVariable("A", VariableType.TREATMENT),
                CausalVariable("B", VariableType.COVARIATE),
                CausalVariable("C", VariableType.OUTCOME)
            ],
            relationships=[
                CausalRelationship("A", "B"),
                CausalRelationship("B", "C"),
                CausalRelationship("C", "A")  # Creates cycle
            ]
        )
        error_caught = False
        try:
            engine.validate_causal_model(model, {})
        except ValueError as ve:
            error_caught = "cycles" in str(ve).lower()
        assert error_caught
        results.append(TestResult("DAG Cycle Detection", True))
    except Exception as e:
        results.append(TestResult("DAG Cycle Detection", False, str(e)))

    # Test 6: No False Cycle Detection
    try:
        engine = CausalInferenceEngine()
        # Valid DAG (no cycles)
        model = CausalModel(
            variables=[
                CausalVariable("A", VariableType.TREATMENT),
                CausalVariable("B", VariableType.COVARIATE),
                CausalVariable("C", VariableType.OUTCOME)
            ],
            relationships=[
                CausalRelationship("A", "B"),
                CausalRelationship("B", "C"),
                CausalRelationship("A", "C")  # Direct effect too
            ]
        )
        data = {"effectEstimate": 0.3, "standardError": 0.1}
        result = engine.validate_causal_model(model, data)
        assert result is not None
        results.append(TestResult("No False Cycle Detection", True))
    except Exception as e:
        results.append(TestResult("No False Cycle Detection", False, str(e)))

    # Test 7: SUTVA Validation
    try:
        engine = CausalInferenceEngine()
        # Data with time structure suggests SUTVA violation
        data_with_time = {"time": [1, 2, 3]}
        sutva = engine._validate_sutva(data_with_time)
        assert not sutva.satisfied
        assert sutva.risk == Severity.MEDIUM

        # Data without time structure
        data_no_time = {"value": [1, 2, 3]}
        sutva2 = engine._validate_sutva(data_no_time)
        assert sutva2.satisfied
        results.append(TestResult("SUTVA Validation", True))
    except Exception as e:
        results.append(TestResult("SUTVA Validation", False, str(e)))

    # Test 8: Ignorability Validation
    try:
        engine = CausalInferenceEngine()

        # Model with unmeasured confounders
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME),
                CausalVariable("age", VariableType.CONFOUNDER, observed=True),
                CausalVariable("income", VariableType.CONFOUNDER, observed=False)  # Unmeasured
            ],
            relationships=[]
        )
        ignorability = engine._validate_ignorability(model, {})
        assert not ignorability.satisfied
        assert "1/2" in ignorability.evidence

        # Model with all measured confounders
        model2 = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME),
                CausalVariable("age", VariableType.CONFOUNDER, observed=True)
            ],
            relationships=[]
        )
        ignorability2 = engine._validate_ignorability(model2, {})
        assert ignorability2.satisfied
        results.append(TestResult("Ignorability Validation", True))
    except Exception as e:
        results.append(TestResult("Ignorability Validation", False, str(e)))

    # Test 9: Consistency Validation
    try:
        engine = CausalInferenceEngine()

        # Treatment without distribution
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT, distribution=None)
            ],
            relationships=[]
        )
        consistency = engine._validate_consistency(model)
        assert not consistency.satisfied

        # Treatment with distribution
        model2 = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT, distribution="binary")
            ],
            relationships=[]
        )
        consistency2 = engine._validate_consistency(model2)
        assert consistency2.satisfied
        results.append(TestResult("Consistency Validation", True))
    except Exception as e:
        results.append(TestResult("Consistency Validation", False, str(e)))

    # Test 10: Bias Threat Detection - Selection Bias
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME)
            ],
            relationships=[]
        )

        # Non-randomized study
        data = {"randomized": False}
        threats = engine.identify_bias_threats(model, data)
        selection_threats = [t for t in threats if t.type == BiasType.SELECTION]
        assert len(selection_threats) == 1
        assert selection_threats[0].severity == Severity.HIGH

        # Randomized study
        data2 = {"randomized": True}
        threats2 = engine.identify_bias_threats(model, data2)
        selection_threats2 = [t for t in threats2 if t.type == BiasType.SELECTION]
        assert len(selection_threats2) == 0
        results.append(TestResult("Bias Threat Detection - Selection", True))
    except Exception as e:
        results.append(TestResult("Bias Threat Detection - Selection", False, str(e)))

    # Test 11: Bias Threat Detection - Confounding
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME),
                CausalVariable("hidden", VariableType.CONFOUNDER, observed=False)
            ],
            relationships=[]
        )
        threats = engine.identify_bias_threats(model, {"randomized": True})
        confounding_threats = [t for t in threats if t.type == BiasType.CONFOUNDING]
        assert len(confounding_threats) == 1
        assert confounding_threats[0].severity == Severity.CRITICAL
        results.append(TestResult("Bias Threat Detection - Confounding", True))
    except Exception as e:
        results.append(TestResult("Bias Threat Detection - Confounding", False, str(e)))

    # Test 12: Bias Threat Detection - Missing Data
    try:
        engine = CausalInferenceEngine()
        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME)
            ],
            relationships=[]
        )

        # High missing rate
        data = {"randomized": True, "missingRate": 0.35}
        threats = engine.identify_bias_threats(model, data)
        missing_threats = [t for t in threats if t.type == BiasType.MISSING_DATA]
        assert len(missing_threats) == 1
        assert missing_threats[0].severity == Severity.HIGH

        # Low missing rate
        data2 = {"randomized": True, "missingRate": 0.05}
        threats2 = engine.identify_bias_threats(model, data2)
        missing_threats2 = [t for t in threats2 if t.type == BiasType.MISSING_DATA]
        assert len(missing_threats2) == 0
        results.append(TestResult("Bias Threat Detection - Missing Data", True))
    except Exception as e:
        results.append(TestResult("Bias Threat Detection - Missing Data", False, str(e)))

    # Test 13: Statistical Significance Test
    try:
        engine = CausalInferenceEngine()
        data = {
            "testStatistic": 2.5,
            "pValue": 0.01,
            "sampleSize": 200,
            "effectSize": 0.5
        }
        result = engine.perform_significance_test("Effect is positive", data, TestType.T_TEST)
        assert result.test_name == "t-test"
        assert result.significant == True
        assert result.p_value == 0.01
        assert result.power_analysis is not None
        results.append(TestResult("Statistical Significance Test", True))
    except Exception as e:
        results.append(TestResult("Statistical Significance Test", False, str(e)))

    # Test 14: Power Analysis
    try:
        engine = CausalInferenceEngine()
        data = {
            "sampleSize": 100,
            "effectSize": 0.5
        }
        power = engine._perform_power_analysis(data)
        assert power.sample_size == 100
        assert power.effect_size == 0.5
        assert 0 <= power.power <= 1
        assert isinstance(power.adequate, bool)
        results.append(TestResult("Power Analysis", True))
    except Exception as e:
        results.append(TestResult("Power Analysis", False, str(e)))

    # Test 15: Model Diagnostics
    try:
        engine = CausalInferenceEngine()
        data = {
            "residuals": [0.1, -0.1, 0.05, -0.05, 0.02],
            "vif": 1.5,
            "bp_pvalue": 0.2,
            "sw_pvalue": 0.4
        }
        valid, diagnostics, recommendations = engine.validate_statistical_model({}, data)
        assert valid == True  # All checks pass
        assert diagnostics.multicollinearity["problematic"] == False
        assert diagnostics.heteroscedasticity["present"] == False
        assert diagnostics.normality["normal"] == True
        assert len(recommendations) == 0
        results.append(TestResult("Model Diagnostics - Valid", True))
    except Exception as e:
        results.append(TestResult("Model Diagnostics - Valid", False, str(e)))

    # Test 16: Model Diagnostics - Issues
    try:
        engine = CausalInferenceEngine()
        data = {
            "residuals": [1.0, -1.0, 0.5, -0.5, 0.2],  # Biased
            "vif": 6.0,  # Multicollinearity
            "bp_pvalue": 0.01,  # Heteroscedasticity
            "sw_pvalue": 0.01  # Non-normal
        }
        valid, diagnostics, recommendations = engine.validate_statistical_model({}, data)
        assert valid == False  # Issues present
        assert diagnostics.multicollinearity["problematic"] == True
        assert diagnostics.heteroscedasticity["present"] == True
        assert diagnostics.normality["normal"] == False
        assert len(recommendations) >= 3
        results.append(TestResult("Model Diagnostics - Issues", True))
    except Exception as e:
        results.append(TestResult("Model Diagnostics - Issues", False, str(e)))

    # Test 17: Effect Estimation
    try:
        engine = CausalInferenceEngine()
        effect = engine._estimate_causal_effect(None, {
            "effectEstimate": 0.5,
            "standardError": 0.1
        })
        assert effect["estimate"] == 0.5
        assert effect["standard_error"] == 0.1

        ci = engine._calculate_confidence_interval(effect, {})
        assert ci[0] < effect["estimate"] < ci[1]
        assert abs(ci[1] - ci[0] - 2 * 1.96 * 0.1) < 0.01  # Width check

        p_value = engine._compute_p_value(effect, {})
        assert p_value < 0.05  # Significant effect
        results.append(TestResult("Effect Estimation", True))
    except Exception as e:
        results.append(TestResult("Effect Estimation", False, str(e)))

    # Test 18: Normal CDF
    try:
        engine = CausalInferenceEngine()
        # z=0 should give 0.5
        assert abs(engine._normal_cdf(0) - 0.5) < 0.001
        # z=1.96 should give ~0.975
        assert abs(engine._normal_cdf(1.96) - 0.975) < 0.01
        # z=-1.96 should give ~0.025
        assert abs(engine._normal_cdf(-1.96) - 0.025) < 0.01
        results.append(TestResult("Normal CDF", True))
    except Exception as e:
        results.append(TestResult("Normal CDF", False, str(e)))

    # Test 19: Study Method Detection
    try:
        engine = CausalInferenceEngine()
        assert engine._determine_method({"randomized": True}) == StudyMethod.RANDOMIZED_TRIAL
        assert engine._determine_method({"natural_experiment": True}) == StudyMethod.QUASI_EXPERIMENTAL
        assert engine._determine_method({}) == StudyMethod.OBSERVATIONAL
        results.append(TestResult("Study Method Detection", True))
    except Exception as e:
        results.append(TestResult("Study Method Detection", False, str(e)))

    # Test 20: Statistics Tracking
    try:
        engine = CausalInferenceEngine()
        assert engine.analyses_performed == 0

        model = CausalModel(
            variables=[
                CausalVariable("treatment", VariableType.TREATMENT),
                CausalVariable("outcome", VariableType.OUTCOME)
            ],
            relationships=[]
        )
        data = {"effectEstimate": 0.5, "standardError": 0.1}

        engine.validate_causal_model(model, data)
        assert engine.analyses_performed == 1
        assert engine.models_validated == 1

        engine.perform_significance_test("test", {"testStatistic": 2, "pValue": 0.01}, TestType.T_TEST)
        assert engine.tests_performed == 1

        status = engine.get_status()
        assert status["analyses_performed"] == 1
        assert status["models_validated"] == 1
        assert status["tests_performed"] == 1
        results.append(TestResult("Statistics Tracking", True))
    except Exception as e:
        results.append(TestResult("Statistics Tracking", False, str(e)))

    # Test 21: Serialization
    try:
        from causal_inference import (
            AssumptionValidation, BiasThreat, PowerAnalysis,
            StatisticalTest, CausalInferenceResult
        )

        # Test various to_dict methods
        assumption = AssumptionValidation(
            "SUTVA", True, "No interference", Severity.LOW
        )
        d = assumption.to_dict()
        assert d["assumption"] == "SUTVA"
        assert d["satisfied"] == True
        assert d["risk"] == "low"

        threat = BiasThreat(
            BiasType.SELECTION, Severity.HIGH,
            "Selection bias", "Use matching"
        )
        d = threat.to_dict()
        assert d["type"] == "selection"
        assert d["severity"] == "high"

        power = PowerAnalysis(0.85, 100, 0.5, 0.05, True)
        d = power.to_dict()
        assert d["power"] == 0.85
        assert d["adequate"] == True
        results.append(TestResult("Serialization", True))
    except Exception as e:
        results.append(TestResult("Serialization", False, str(e)))

    # Test 22: MCP Tool Registration
    try:
        class MockApp:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()
        engine = register_causal_inference_tools(mock_app)

        expected_tools = [
            "ci_validate_causal_model",
            "ci_identify_bias_threats",
            "ci_significance_test",
            "ci_power_analysis",
            "ci_validate_model",
            "ci_estimate_effect",
            "ci_status"
        ]

        for tool_name in expected_tools:
            assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"

        assert len(mock_app.tools) == 7
        results.append(TestResult("MCP Tool Registration", True))
    except Exception as e:
        results.append(TestResult("MCP Tool Registration", False, str(e)))

    # Test 23: MCP Tool Execution
    try:
        import asyncio

        class MockApp:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()
        register_causal_inference_tools(mock_app)

        async def test_tools():
            # Test ci_status
            status_result = await mock_app.tools["ci_status"]()
            assert status_result["success"] == True
            assert "status" in status_result

            # Test ci_estimate_effect
            effect_result = await mock_app.tools["ci_estimate_effect"](
                effect_estimate=0.5,
                standard_error=0.1,
                confidence_level=0.95
            )
            assert effect_result["success"] == True
            assert "confidence_interval" in effect_result
            assert effect_result["significant"] == True

            # Test ci_significance_test
            sig_result = await mock_app.tools["ci_significance_test"](
                hypothesis="Effect is positive",
                test_type="t-test",
                test_statistic=2.5,
                p_value=0.01,
                sample_size=100,
                effect_size=0.5
            )
            assert sig_result["success"] == True
            assert sig_result["result"]["significant"] == True

            return True

        asyncio.run(test_tools())
        results.append(TestResult("MCP Tool Execution", True))
    except Exception as e:
        results.append(TestResult("MCP Tool Execution", False, str(e)))

    # Test 24: Complete Workflow
    try:
        import asyncio

        class MockApp:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()
        register_causal_inference_tools(mock_app)

        async def test_workflow():
            # Full causal model validation
            result = await mock_app.tools["ci_validate_causal_model"](
                variables=[
                    {"name": "drug", "type": "treatment", "observed": True},
                    {"name": "recovery", "type": "outcome", "observed": True},
                    {"name": "age", "type": "confounder", "observed": True},
                    {"name": "genetics", "type": "confounder", "observed": False}
                ],
                relationships=[
                    {"from": "drug", "to": "recovery", "type": "direct"},
                    {"from": "age", "to": "drug"},
                    {"from": "age", "to": "recovery"},
                    {"from": "genetics", "to": "recovery"}
                ],
                data={
                    "randomized": False,
                    "missingRate": 0.15,
                    "effectEstimate": 0.4,
                    "standardError": 0.1
                }
            )

            assert result["success"] == True
            assert "result" in result
            assert "threats" in result["result"]
            assert len(result["result"]["threats"]) > 0  # Should have bias threats

            # Check assumptions
            assumptions = result["result"]["assumptions"]
            assert len(assumptions) == 4  # SUTVA, Ignorability, Positivity, Consistency

            return True

        asyncio.run(test_workflow())
        results.append(TestResult("Complete Workflow", True))
    except Exception as e:
        results.append(TestResult("Complete Workflow", False, str(e)))

    return results


def main():
    print("=" * 60)
    print("Causal Inference Engine - Comprehensive Test Suite")
    print("=" * 60)
    print()

    results = run_tests()

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{status}: {r.name}")
        if not r.passed and r.message:
            print(f"       Error: {r.message}")

    print()
    print("=" * 60)
    print(f"Results: {passed}/{len(results)} tests passed")
    print("=" * 60)

    if failed > 0:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
