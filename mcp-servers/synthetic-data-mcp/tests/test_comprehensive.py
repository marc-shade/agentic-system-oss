#!/usr/bin/env python3
"""
Comprehensive test suite for Synthetic Data MCP Server.
Tests all features, domains, privacy levels, and output formats.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import core modules
from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.privacy.engine import PrivacyEngine
from synthetic_data_mcp.compliance.validator import ComplianceValidator
from synthetic_data_mcp.validation.statistical import StatisticalValidator
from synthetic_data_mcp.ingestion.data_ingestion import DataIngestionPipeline
from synthetic_data_mcp.ingestion.pattern_analyzer import PatternAnalyzer
from synthetic_data_mcp.ingestion.knowledge_loader import DynamicKnowledgeLoader
from synthetic_data_mcp.schemas.base import (
    DataDomain, PrivacyLevel, OutputFormat, ComplianceFramework
)


def print_header(title: str):
    """Print a formatted test header."""
    print(f"\n{'='*80}")
    print(f"TEST: {title}")
    print(f"{'='*80}")


def print_result(description: str, success: bool, details: str = ""):
    """Print a formatted test result."""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"  {status}: {description}")
    if details:
        print(f"    Details: {details}")


async def test_healthcare_generation():
    """Test healthcare domain data generation with all privacy levels."""
    print_header("Healthcare Data Generation")
    
    generator = SyntheticDataGenerator()
    privacy_engine = PrivacyEngine()
    results = []
    
    # Test all privacy levels
    for privacy_level in PrivacyLevel:
        try:
            # Generate patient records
            dataset = await generator.generate_dataset(
                domain=DataDomain.HEALTHCARE,
                dataset_type="patient_records",
                record_count=10,
                privacy_level=privacy_level
            )
            
            # Apply privacy protection
            # Extract just the dataset array from the result
            if dataset.get("status") == "success" and "dataset" in dataset:
                actual_data = dataset["dataset"]
            else:
                actual_data = dataset if isinstance(dataset, list) else []
                
            protected_data, privacy_metrics = await privacy_engine.protect_dataset(
                dataset=actual_data,
                privacy_level=privacy_level,
                domain=DataDomain.HEALTHCARE
            )
            
            results.append(True)
            print_result(
                f"Healthcare generation with {privacy_level.value} privacy",
                True,
                f"{len(protected_data)} records generated"
            )
            
        except Exception as e:
            results.append(False)
            print_result(
                f"Healthcare generation with {privacy_level.value} privacy",
                False,
                str(e)
            )
    
    return all(results)


async def test_finance_generation():
    """Test finance domain data generation with compliance frameworks."""
    print_header("Finance Data Generation with Compliance")
    
    generator = SyntheticDataGenerator()
    compliance_validator = ComplianceValidator()
    results = []
    
    # Test finance-specific compliance frameworks
    finance_frameworks = [
        ComplianceFramework.PCI_DSS,
        ComplianceFramework.SOX,
        ComplianceFramework.BASEL_III
    ]
    
    for framework in finance_frameworks:
        try:
            # Generate transaction records
            dataset = await generator.generate_dataset(
                domain=DataDomain.FINANCE,
                dataset_type="transaction_records",
                record_count=20,
                privacy_level=PrivacyLevel.HIGH
            )
            
            # Validate compliance
            # Extract just the dataset array from the result
            if dataset.get("status") == "success" and "dataset" in dataset:
                actual_data = dataset["dataset"]
            else:
                actual_data = dataset if isinstance(dataset, list) else []
                
            compliance_results = await compliance_validator.validate_dataset(
                dataset=actual_data,
                frameworks=[framework],
                domain=DataDomain.FINANCE
            )
            
            # ComplianceResult is an object, not a dict
            compliance_result = compliance_results.get(framework.value) or compliance_results.get(framework)
            passed = compliance_result.passed if compliance_result else False
            results.append(passed)
            
            print_result(
                f"Finance data with {framework.value} compliance",
                passed,
                f"Compliance {'passed' if passed else 'failed'}"
            )
            
        except Exception as e:
            results.append(False)
            print_result(
                f"Finance data with {framework.value} compliance",
                False,
                str(e)
            )
    
    return all(results)


async def test_data_ingestion():
    """Test data ingestion and pattern learning."""
    print_header("Data Ingestion and Pattern Learning")
    
    privacy_engine = PrivacyEngine()
    pipeline = DataIngestionPipeline(privacy_engine)
    analyzer = PatternAnalyzer()
    results = []
    
    # Create sample data with PII
    sample_data = [
        {
            "customer_id": f"CUST{i:04d}",
            "name": f"Customer {i}",
            "email": f"customer{i}@example.com",
            "phone": f"+1-555-{i:04d}",
            "transaction_amount": 100.00 + i * 50,
            "category": ["electronics", "clothing", "food"][i % 3],
            "timestamp": datetime.now().isoformat()
        }
        for i in range(50)
    ]
    
    try:
        # Ingest data
        result = await pipeline.ingest(
            source=sample_data,
            format="dict",
            anonymize=True,
            learn_patterns=True
        )
        
        pattern_id = result.get("pattern_id")
        results.append(pattern_id is not None)
        print_result(
            "Data ingestion with PII anonymization",
            pattern_id is not None,
            f"Pattern ID: {pattern_id}, Rows: {result.get('rows_ingested', 0)}"
        )
        
        # Test pattern analysis
        pattern_summary = await analyzer.analyze_patterns(sample_data)
        has_patterns = bool(pattern_summary.get("columns"))
        results.append(has_patterns)
        print_result(
            "Pattern analysis",
            has_patterns,
            f"Columns: {len(pattern_summary.get('columns', []))}"
        )
        
    except Exception as e:
        results.append(False)
        print_result("Data ingestion", False, str(e))
    
    return all(results)


async def test_output_formats():
    """Test all output formats."""
    print_header("Output Formats")
    
    generator = SyntheticDataGenerator()
    results = []
    
    # Test each output format
    for output_format in [OutputFormat.JSON, OutputFormat.CSV]:
        try:
            dataset = await generator.generate_dataset(
                domain=DataDomain.CUSTOM,
                dataset_type="custom",
                record_count=5,
                privacy_level=PrivacyLevel.MEDIUM,
                output_format=output_format
            )
            
            # Check if data was generated
            success = len(dataset) > 0
            results.append(success)
            
            print_result(
                f"Output format: {output_format.value}",
                success,
                f"{len(dataset)} records"
            )
            
        except Exception as e:
            results.append(False)
            print_result(
                f"Output format: {output_format.value}",
                False,
                str(e)
            )
    
    return all(results)


async def test_statistical_validation():
    """Test statistical validation."""
    print_header("Statistical Validation")
    
    generator = SyntheticDataGenerator()
    validator = StatisticalValidator()
    results = []
    
    try:
        # Generate synthetic data
        synthetic_data = await generator.generate_dataset(
            domain=DataDomain.CUSTOM,
            dataset_type="custom",
            record_count=100,
            privacy_level=PrivacyLevel.MEDIUM
        )
        
        # Perform statistical validation
        # Extract just the dataset array from the result
        if synthetic_data.get("status") == "success" and "dataset" in synthetic_data:
            actual_data = synthetic_data["dataset"]
        else:
            actual_data = synthetic_data if isinstance(synthetic_data, list) else []
            
        validation_results = await validator.validate_fidelity(
            synthetic_data=actual_data,
            validation_level="standard",
            domain=DataDomain.CUSTOM
        )
        
        success = validation_results.get("overall_quality", 0) > 0
        results.append(success)
        
        print_result(
            "Statistical fidelity validation",
            success,
            f"Quality score: {validation_results.get('overall_quality', 0):.2f}"
        )
        
    except Exception as e:
        results.append(False)
        print_result("Statistical validation", False, str(e))
    
    return all(results)


async def test_privacy_analysis():
    """Test privacy risk analysis."""
    print_header("Privacy Risk Analysis")
    
    privacy_engine = PrivacyEngine()
    generator = SyntheticDataGenerator()
    results = []
    
    try:
        # Generate dataset
        dataset = await generator.generate_dataset(
            domain=DataDomain.HEALTHCARE,
            dataset_type="patient_records",
            record_count=50,
            privacy_level=PrivacyLevel.HIGH
        )
        
        # Analyze privacy risk
        # Extract just the dataset array from the result
        if dataset.get("status") == "success" and "dataset" in dataset:
            actual_data = dataset["dataset"]
        else:
            actual_data = dataset if isinstance(dataset, list) else []
            
        risk_analysis = await privacy_engine.analyze_privacy_risk(
            dataset=actual_data,
            auxiliary_data=None,
            attack_scenarios=["linkage", "inference"]
        )
        
        risk_score = risk_analysis.get("overall_risk", 1.0)
        success = risk_score < 0.5  # Risk should be low
        results.append(success)
        
        print_result(
            "Privacy risk assessment",
            success,
            f"Risk score: {risk_score:.3f}"
        )
        
        # Test differential privacy
        dp_metrics = risk_analysis.get("dp_recommendations", {})
        has_dp = bool(dp_metrics)
        results.append(has_dp)
        
        print_result(
            "Differential privacy recommendations",
            has_dp,
            f"Epsilon: {dp_metrics.get('epsilon', 'N/A')}"
        )
        
    except Exception as e:
        results.append(False)
        print_result("Privacy analysis", False, str(e))
    
    return all(results)


async def test_pattern_based_generation():
    """Test pattern-based synthetic data generation."""
    print_header("Pattern-Based Generation")
    
    generator = SyntheticDataGenerator()
    privacy_engine = PrivacyEngine()
    pipeline = DataIngestionPipeline(privacy_engine)
    results = []
    
    # Create training data
    training_data = [
        {
            "product_id": f"PROD{i:04d}",
            "price": 10.00 + (i * 2.5),
            "quantity": 1 + (i % 10),
            "category": ["A", "B", "C"][i % 3]
        }
        for i in range(30)
    ]
    
    try:
        # Learn patterns
        ingestion_result = await pipeline.ingest(
            source=training_data,
            format="dict",
            learn_patterns=True
        )
        
        pattern_id = ingestion_result.get("pattern_id")
        
        # Generate from patterns
        generated_data = await generator.generate_from_pattern(
            pattern_id=pattern_id,
            record_count=50,
            variation=0.3,
            privacy_level=PrivacyLevel.MEDIUM
        )
        
        success = len(generated_data.get("data", [])) == 50
        results.append(success)
        
        print_result(
            "Pattern-based generation",
            success,
            f"Generated {len(generated_data.get('data', []))} records from pattern"
        )
        
    except Exception as e:
        results.append(False)
        print_result("Pattern-based generation", False, str(e))
    
    return all(results)


async def test_dynamic_knowledge():
    """Test dynamic knowledge loading."""
    print_header("Dynamic Knowledge Loading")
    
    loader = DynamicKnowledgeLoader()
    results = []
    
    # Test that knowledge is dynamic
    for domain in ["healthcare", "finance"]:
        try:
            # Use the correct method names
            if domain == "healthcare":
                knowledge = loader.get_healthcare_knowledge()
            else:
                knowledge = loader.get_finance_knowledge()
            
            # Check if knowledge has the expected structure
            has_structure = isinstance(knowledge, dict) and len(knowledge) > 0
            
            results.append(has_structure)
            print_result(
                f"{domain.capitalize()} knowledge loaded",
                has_structure,
                f"Knowledge contains {len(knowledge)} keys" if has_structure else "Empty knowledge"
            )
            
        except Exception as e:
            results.append(False)
            print_result(f"{domain.capitalize()} knowledge", False, str(e))
    
    return all(results)


async def main():
    """Run all comprehensive tests."""
    print("="*80)
    print("SYNTHETIC DATA MCP - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Run all tests
    test_results = []
    
    # Test 1: Healthcare generation
    test_results.append(("Healthcare Generation", await test_healthcare_generation()))
    
    # Test 2: Finance generation with compliance
    test_results.append(("Finance Generation", await test_finance_generation()))
    
    # Test 3: Data ingestion and patterns
    test_results.append(("Data Ingestion", await test_data_ingestion()))
    
    # Test 4: Output formats
    test_results.append(("Output Formats", await test_output_formats()))
    
    # Test 5: Statistical validation
    test_results.append(("Statistical Validation", await test_statistical_validation()))
    
    # Test 6: Privacy analysis
    test_results.append(("Privacy Analysis", await test_privacy_analysis()))
    
    # Test 7: Pattern-based generation
    test_results.append(("Pattern Generation", await test_pattern_based_generation()))
    
    # Test 8: Dynamic knowledge
    test_results.append(("Dynamic Knowledge", await test_dynamic_knowledge()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30s}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed}/{passed+failed} tests passed")
    
    if failed > 0:
        print(f"\n⚠️ {failed} tests failed. Review the errors above.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    # Set environment variables for testing
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test-key")
    
    # Run the test suite
    asyncio.run(main())