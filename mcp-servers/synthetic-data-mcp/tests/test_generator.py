"""
Tests for DSPy-powered synthetic data generation engine.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from synthetic_data_mcp.core.generator import (
    SyntheticDataGenerator,
    HealthcareDataSignature,
    FinanceDataSignature
)
from synthetic_data_mcp.schemas.healthcare import PatientRecord
from synthetic_data_mcp.schemas.finance import Transaction


class TestSyntheticDataGenerator:
    """Test suite for synthetic data generation."""

    @pytest.fixture
    def mock_dspy_healthcare_model(self):
        """Mock DSPy healthcare model."""
        mock_model = AsyncMock()
        mock_model.forward.return_value = MagicMock(
            synthetic_records="""[
                {
                    "patient_id": "PAT_001",
                    "demographics": {
                        "age_group": "35-44",
                        "gender": "F",
                        "ethnicity": "White",
                        "zip_code": "12345",
                        "state": "NY"
                    },
                    "conditions": [
                        {
                            "icd_10_code": "E11.9",
                            "description": "Type 2 diabetes mellitus",
                            "diagnosis_date": "2023-01-15",
                            "severity": "moderate",
                            "status": "active"
                        }
                    ],
                    "encounters": [
                        {
                            "encounter_id": "ENC_001",
                            "encounter_type": "office_visit",
                            "date": "2023-01-15",
                            "provider_id": "PROV_001",
                            "duration_minutes": 30
                        }
                    ]
                }
            ]"""
        )
        return mock_model

    @pytest.fixture
    def mock_dspy_finance_model(self):
        """Mock DSPy finance model."""
        mock_model = AsyncMock()
        mock_model.forward.return_value = MagicMock(
            synthetic_records="""[
                {
                    "transaction_id": "TXN_001",
                    "account_id": "ACC_001", 
                    "amount": 125.75,
                    "transaction_type": "purchase",
                    "category": "dining",
                    "timestamp": "2023-01-15T12:00:00Z",
                    "merchant": "Restaurant ABC",
                    "location": {
                        "city": "New York",
                        "state": "NY",
                        "zip_code": "10001"
                    }
                }
            ]"""
        )
        return mock_model

    @pytest.fixture
    async def generator(self, mock_dspy_healthcare_model, mock_dspy_finance_model):
        """Create generator with mocked models."""
        with patch('synthetic_data_mcp.core.generator.dspy') as mock_dspy:
            mock_dspy.ChainOfThought.side_effect = [
                mock_dspy_healthcare_model,
                mock_dspy_finance_model
            ]
            return SyntheticDataGenerator()

    @pytest.mark.asyncio
    async def test_generate_healthcare_dataset(self, generator, mock_dspy_healthcare_model):
        """Test healthcare dataset generation."""
        
        config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {
                "include_demographics": True,
                "include_conditions": True,
                "include_encounters": True
            }
        }
        
        result = await generator.generate_dataset(config)
        
        # Validate result structure
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Validate record content
        record = result[0]
        assert record["patient_id"] == "PAT_001"
        assert record["demographics"]["age_group"] == "35-44"
        assert len(record["conditions"]) == 1
        assert len(record["encounters"]) == 1
        
        # Verify DSPy model was called
        mock_dspy_healthcare_model.forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_finance_dataset(self, generator, mock_dspy_finance_model):
        """Test financial dataset generation."""
        
        config = {
            "record_count": 1,
            "domain": "finance",
            "schema_config": {
                "include_transactions": True,
                "transaction_types": ["purchase", "deposit"]
            }
        }
        
        result = await generator.generate_dataset(config)
        
        # Validate result structure
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Validate record content
        record = result[0]
        assert record["transaction_id"] == "TXN_001"
        assert record["amount"] == 125.75
        assert record["transaction_type"] == "purchase"
        assert record["location"]["city"] == "New York"
        
        # Verify DSPy model was called
        mock_dspy_finance_model.forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_multiple_records(self, generator, mock_dspy_healthcare_model):
        """Test generation of multiple records."""
        
        # Mock model to return multiple records
        mock_dspy_healthcare_model.forward.return_value = MagicMock(
            synthetic_records="""[
                {
                    "patient_id": "PAT_001",
                    "demographics": {"age_group": "25-34", "gender": "F"},
                    "conditions": [],
                    "encounters": []
                },
                {
                    "patient_id": "PAT_002", 
                    "demographics": {"age_group": "35-44", "gender": "M"},
                    "conditions": [],
                    "encounters": []
                }
            ]"""
        )
        
        config = {
            "record_count": 2,
            "domain": "healthcare",
            "schema_config": {"include_demographics": True}
        }
        
        result = await generator.generate_dataset(config)
        
        assert len(result) == 2
        assert result[0]["patient_id"] == "PAT_001"
        assert result[1]["patient_id"] == "PAT_002"

    @pytest.mark.asyncio
    async def test_domain_specific_knowledge_base(self, generator):
        """Test that domain-specific knowledge is used."""
        
        # Test healthcare knowledge base
        healthcare_kb = generator._get_domain_knowledge("healthcare", {})
        assert "medical_conditions" in healthcare_kb
        assert "demographics_patterns" in healthcare_kb
        assert "encounter_types" in healthcare_kb
        
        # Test finance knowledge base
        finance_kb = generator._get_domain_knowledge("finance", {})
        assert "transaction_patterns" in finance_kb
        assert "merchant_categories" in finance_kb
        assert "amount_distributions" in finance_kb

    @pytest.mark.asyncio
    async def test_schema_validation_integration(self, generator, mock_dspy_healthcare_model):
        """Test that generated data validates against schemas."""
        
        config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {
                "include_demographics": True,
                "include_conditions": True,
                "include_encounters": True
            }
        }
        
        result = await generator.generate_dataset(config)
        
        # Validate that result can be parsed into proper schema
        for record_data in result:
            record = PatientRecord(**record_data)
            assert record.patient_id is not None
            assert record.demographics is not None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_json(self, generator, mock_dspy_healthcare_model):
        """Test error handling for invalid JSON from DSPy."""
        
        # Mock model to return invalid JSON
        mock_dspy_healthcare_model.forward.return_value = MagicMock(
            synthetic_records="invalid json content"
        )
        
        config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {}
        }
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            await generator.generate_dataset(config)

    @pytest.mark.asyncio
    async def test_error_handling_model_failure(self, generator, mock_dspy_healthcare_model):
        """Test error handling for DSPy model failures."""
        
        # Mock model to raise exception
        mock_dspy_healthcare_model.forward.side_effect = Exception("Model error")
        
        config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {}
        }
        
        with pytest.raises(Exception, match="Failed to generate synthetic data"):
            await generator.generate_dataset(config)

    @pytest.mark.asyncio
    async def test_unsupported_domain(self, generator):
        """Test error handling for unsupported domains."""
        
        config = {
            "record_count": 1,
            "domain": "unsupported_domain",
            "schema_config": {}
        }
        
        with pytest.raises(ValueError, match="Unsupported domain"):
            await generator.generate_dataset(config)

    @pytest.mark.asyncio
    async def test_realistic_patterns_healthcare(self, generator):
        """Test that healthcare patterns are realistic."""
        
        knowledge_base = generator._get_domain_knowledge("healthcare", {
            "age_groups": ["25-34", "35-44"],
            "conditions": ["diabetes", "hypertension"]
        })
        
        # Verify realistic medical conditions are included
        conditions = knowledge_base["medical_conditions"]
        assert any("diabetes" in condition.lower() for condition in conditions)
        assert any("hypertension" in condition.lower() for condition in conditions)
        
        # Verify age group constraints are applied
        demographics = knowledge_base["demographics_patterns"]
        age_groups = [demo["age_group"] for demo in demographics]
        assert "25-34" in age_groups
        assert "35-44" in age_groups

    @pytest.mark.asyncio
    async def test_realistic_patterns_finance(self, generator):
        """Test that finance patterns are realistic."""
        
        knowledge_base = generator._get_domain_knowledge("finance", {
            "transaction_types": ["purchase", "deposit"],
            "amount_ranges": {"min": 10.0, "max": 1000.0}
        })
        
        # Verify transaction patterns are realistic
        patterns = knowledge_base["transaction_patterns"]
        assert len(patterns) > 0
        
        # Verify merchant categories are comprehensive
        categories = knowledge_base["merchant_categories"]
        expected_categories = ["groceries", "dining", "gas", "retail"]
        for category in expected_categories:
            assert category in categories

    @pytest.mark.asyncio
    async def test_statistical_diversity(self, generator, mock_dspy_healthcare_model):
        """Test that generated data has statistical diversity."""
        
        # Mock model to return diverse records
        mock_dspy_healthcare_model.forward.return_value = MagicMock(
            synthetic_records="""[
                {
                    "patient_id": "PAT_001",
                    "demographics": {"age_group": "25-34", "gender": "F", "ethnicity": "White"},
                    "conditions": [],
                    "encounters": []
                },
                {
                    "patient_id": "PAT_002",
                    "demographics": {"age_group": "35-44", "gender": "M", "ethnicity": "Hispanic or Latino"},
                    "conditions": [],
                    "encounters": []
                },
                {
                    "patient_id": "PAT_003",
                    "demographics": {"age_group": "45-54", "gender": "F", "ethnicity": "Black or African American"},
                    "conditions": [],
                    "encounters": []
                }
            ]"""
        )
        
        config = {
            "record_count": 3,
            "domain": "healthcare",
            "schema_config": {"include_demographics": True}
        }
        
        result = await generator.generate_dataset(config)
        
        # Check diversity in age groups
        age_groups = [record["demographics"]["age_group"] for record in result]
        assert len(set(age_groups)) > 1  # Multiple unique age groups
        
        # Check diversity in gender
        genders = [record["demographics"]["gender"] for record in result]
        assert len(set(genders)) > 1  # Multiple genders represented
        
        # Check diversity in ethnicity
        ethnicities = [record["demographics"]["ethnicity"] for record in result]
        assert len(set(ethnicities)) > 1  # Multiple ethnicities represented

    @pytest.mark.asyncio
    async def test_batch_generation_performance(self, generator, mock_dspy_healthcare_model):
        """Test performance with batch generation."""
        
        config = {
            "record_count": 100,
            "domain": "healthcare", 
            "schema_config": {"include_demographics": True}
        }
        
        # Mock model to return batch of records
        mock_records = []
        for i in range(100):
            mock_records.append({
                "patient_id": f"PAT_{i:03d}",
                "demographics": {"age_group": "25-34", "gender": "F"},
                "conditions": [],
                "encounters": []
            })
        
        mock_dspy_healthcare_model.forward.return_value = MagicMock(
            synthetic_records=str(mock_records).replace("'", '"')
        )
        
        import time
        start_time = time.time()
        result = await generator.generate_dataset(config)
        end_time = time.time()
        
        # Validate results
        assert len(result) == 100
        
        # Check that generation was reasonably fast (should be < 1 second for mocked data)
        generation_time = end_time - start_time
        assert generation_time < 1.0

    def test_dspy_signatures(self):
        """Test DSPy signature definitions."""
        
        # Test healthcare signature
        healthcare_sig = HealthcareDataSignature()
        assert hasattr(healthcare_sig, 'record_count')
        assert hasattr(healthcare_sig, 'domain_knowledge')
        assert hasattr(healthcare_sig, 'schema_requirements')
        assert hasattr(healthcare_sig, 'synthetic_records')
        
        # Test finance signature  
        finance_sig = FinanceDataSignature()
        assert hasattr(finance_sig, 'record_count')
        assert hasattr(finance_sig, 'domain_knowledge')
        assert hasattr(finance_sig, 'schema_requirements')
        assert hasattr(finance_sig, 'synthetic_records')

    @pytest.mark.asyncio
    async def test_configuration_flexibility(self, generator, mock_dspy_healthcare_model):
        """Test flexible configuration options."""
        
        # Test minimal configuration
        minimal_config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {}
        }
        
        result = await generator.generate_dataset(minimal_config)
        assert len(result) == 1
        
        # Test comprehensive configuration
        comprehensive_config = {
            "record_count": 1,
            "domain": "healthcare",
            "schema_config": {
                "include_demographics": True,
                "include_conditions": True,
                "include_encounters": True,
                "include_claims": True,
                "age_groups": ["25-34", "35-44"],
                "conditions": ["diabetes", "hypertension"],
                "encounter_types": ["office_visit", "emergency"]
            }
        }
        
        result = await generator.generate_dataset(comprehensive_config)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, generator):
        """Test memory efficiency for large datasets."""
        
        # Test that generator doesn't load unnecessary data structures
        initial_knowledge = generator._get_domain_knowledge("healthcare", {})
        
        # Knowledge base should be reasonably sized
        import sys
        knowledge_size = sys.getsizeof(str(initial_knowledge))
        assert knowledge_size < 10000  # Less than 10KB for knowledge base