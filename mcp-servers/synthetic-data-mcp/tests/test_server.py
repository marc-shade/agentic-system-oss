"""
Tests for the main MCP server functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from synthetic_data_mcp.server import (
    app,
    GenerateSyntheticDatasetRequest, 
    ValidateDatasetComplianceRequest
)


class TestMCPServer:
    """Test suite for MCP server functionality."""

    @pytest.mark.asyncio
    async def test_generate_synthetic_dataset_healthcare(
        self, 
        sample_healthcare_data,
        sample_privacy_metrics,
        sample_statistical_results
    ):
        """Test synthetic healthcare data generation."""
        
        # Mock all dependencies
        with patch('synthetic_data_mcp.server.SyntheticDataGenerator') as mock_generator_class, \
             patch('synthetic_data_mcp.server.PrivacyEngine') as mock_privacy_class, \
             patch('synthetic_data_mcp.server.ComplianceValidator') as mock_compliance_class, \
             patch('synthetic_data_mcp.server.StatisticalValidator') as mock_statistical_class, \
             patch('synthetic_data_mcp.server.AuditTrail') as mock_audit_class:

            # Setup mocks
            mock_generator = AsyncMock()
            mock_generator.generate_dataset.return_value = sample_healthcare_data
            mock_generator_class.return_value = mock_generator

            mock_privacy = AsyncMock()
            mock_privacy.protect_dataset.return_value = (sample_healthcare_data, sample_privacy_metrics)
            mock_privacy_class.return_value = mock_privacy

            mock_compliance = AsyncMock()
            mock_compliance.validate_dataset.return_value = {
                "compliant": True,
                "framework": "HIPAA",
                "violations": [],
                "risk_score": 0.1
            }
            mock_compliance_class.return_value = mock_compliance

            mock_statistical = AsyncMock()
            mock_statistical.validate_fidelity.return_value = sample_statistical_results
            mock_statistical_class.return_value = mock_statistical

            mock_audit = AsyncMock()
            mock_audit.start_operation.return_value = "audit_123"
            mock_audit.complete_operation = AsyncMock()
            mock_audit_class.return_value = mock_audit

            # Create test request
            request = GenerateSyntheticDatasetRequest(
                domain="healthcare",
                record_count=100,
                schema_config={
                    "include_demographics": True,
                    "include_conditions": True,
                    "include_encounters": True
                },
                privacy_config={
                    "epsilon": 1.0,
                    "delta": 1e-5,
                    "anonymization_level": "k_anonymity",
                    "k_value": 5
                },
                compliance_frameworks=["HIPAA"],
                format="json"
            )

            # Execute the tool
            result = await app._tools['generate_synthetic_dataset'](request)

            # Validate results
            assert isinstance(result, dict)
            assert "synthetic_data" in result
            assert "privacy_metrics" in result
            assert "compliance_results" in result
            assert "validation_results" in result
            assert "audit_trail" in result

            # Verify synthetic data structure
            synthetic_data = result["synthetic_data"]
            assert len(synthetic_data) == len(sample_healthcare_data)
            
            # Verify privacy metrics
            privacy_metrics = result["privacy_metrics"]
            assert "epsilon_used" in privacy_metrics
            assert "k_anonymity" in privacy_metrics
            assert "re_identification_risk" in privacy_metrics

            # Verify compliance results
            compliance_results = result["compliance_results"]
            assert compliance_results["compliant"] is True
            assert compliance_results["framework"] == "HIPAA"
            assert len(compliance_results["violations"]) == 0

            # Verify audit trail
            audit_info = result["audit_trail"]
            assert "audit_id" in audit_info
            assert "operation_type" in audit_info

            # Verify mocks were called correctly
            mock_generator.generate_dataset.assert_called_once()
            mock_privacy.protect_dataset.assert_called_once()
            mock_compliance.validate_dataset.assert_called_once()
            mock_audit.start_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_synthetic_dataset_finance(self, sample_finance_data):
        """Test synthetic financial data generation."""
        
        with patch('synthetic_data_mcp.server.SyntheticDataGenerator') as mock_generator_class, \
             patch('synthetic_data_mcp.server.PrivacyEngine') as mock_privacy_class, \
             patch('synthetic_data_mcp.server.ComplianceValidator') as mock_compliance_class, \
             patch('synthetic_data_mcp.server.StatisticalValidator') as mock_statistical_class, \
             patch('synthetic_data_mcp.server.AuditTrail') as mock_audit_class:

            # Setup mocks
            mock_generator = AsyncMock()
            mock_generator.generate_dataset.return_value = sample_finance_data
            mock_generator_class.return_value = mock_generator

            mock_privacy = AsyncMock()
            mock_privacy.protect_dataset.return_value = (sample_finance_data, {"epsilon_used": 0.5})
            mock_privacy_class.return_value = mock_privacy

            mock_compliance = AsyncMock()
            mock_compliance.validate_dataset.return_value = {
                "compliant": True,
                "framework": "PCI DSS",
                "violations": [],
                "risk_score": 0.05
            }
            mock_compliance_class.return_value = mock_compliance

            mock_statistical = AsyncMock()
            mock_statistical.validate_fidelity.return_value = {"overall_fidelity_score": 0.89}
            mock_statistical_class.return_value = mock_statistical

            mock_audit = AsyncMock()
            mock_audit.start_operation.return_value = "audit_456"
            mock_audit_class.return_value = mock_audit

            # Create finance request
            request = GenerateSyntheticDatasetRequest(
                domain="finance",
                record_count=50,
                schema_config={
                    "transaction_types": ["purchase", "deposit", "withdrawal"],
                    "amount_ranges": {"min": 10.0, "max": 10000.0}
                },
                privacy_config={
                    "epsilon": 2.0,
                    "delta": 1e-6
                },
                compliance_frameworks=["PCI DSS", "SOX"],
                format="json"
            )

            # Execute
            result = await app._tools['generate_synthetic_dataset'](request)

            # Validate
            assert "synthetic_data" in result
            assert len(result["synthetic_data"]) == len(sample_finance_data)
            assert result["compliance_results"]["framework"] == "PCI DSS"

    @pytest.mark.asyncio
    async def test_validate_compliance(self, sample_healthcare_data, sample_compliance_violations):
        """Test compliance validation functionality."""
        
        with patch('synthetic_data_mcp.server.ComplianceValidator') as mock_compliance_class:
            
            mock_compliance = AsyncMock()
            mock_compliance.validate_dataset.return_value = {
                "compliant": False,
                "framework": "HIPAA",
                "violations": sample_compliance_violations,
                "risk_score": 0.75,
                "recommendations": [
                    "Remove patient names from dataset",
                    "Anonymize geographic data below state level"
                ]
            }
            mock_compliance_class.return_value = mock_compliance

            # Create validation request
            request = ValidateComplianceRequest(
                data=sample_healthcare_data,
                frameworks=["HIPAA"],
                domain="healthcare"
            )

            # Execute
            result = await app._tools['validate_compliance'](request)

            # Validate
            assert isinstance(result, dict)
            assert "validation_results" in result
            assert result["validation_results"]["compliant"] is False
            assert len(result["validation_results"]["violations"]) > 0
            assert result["validation_results"]["risk_score"] == 0.75

    @pytest.mark.asyncio
    async def test_assess_privacy_risk(self, sample_healthcare_data):
        """Test privacy risk assessment."""
        
        with patch('synthetic_data_mcp.server.PrivacyEngine') as mock_privacy_class:
            
            mock_privacy = AsyncMock()
            mock_privacy.assess_privacy_risk.return_value = {
                "re_identification_risk": 0.05,
                "k_anonymity": 8,
                "l_diversity": 4,
                "privacy_score": 0.92,
                "recommendations": [
                    "Consider increasing k-anonymity threshold",
                    "Add more noise to sensitive numerical fields"
                ]
            }
            mock_privacy_class.return_value = mock_privacy

            # Execute
            result = await app._tools['assess_privacy_risk']({
                "data": sample_healthcare_data,
                "quasi_identifiers": ["age_group", "gender", "zip_code"]
            })

            # Validate
            assert "privacy_assessment" in result
            assert result["privacy_assessment"]["re_identification_risk"] == 0.05
            assert result["privacy_assessment"]["k_anonymity"] == 8

    @pytest.mark.asyncio
    async def test_validate_statistical_fidelity(self, sample_healthcare_data, sample_statistical_results):
        """Test statistical fidelity validation."""
        
        with patch('synthetic_data_mcp.server.StatisticalValidator') as mock_statistical_class:
            
            mock_statistical = AsyncMock()
            mock_statistical.validate_fidelity.return_value = sample_statistical_results
            mock_statistical_class.return_value = mock_statistical

            # Execute
            result = await app._tools['validate_statistical_fidelity']({
                "original_data": sample_healthcare_data,
                "synthetic_data": sample_healthcare_data,  # Using same for test
                "validation_config": {
                    "distribution_tests": True,
                    "correlation_tests": True,
                    "ml_utility_tests": True
                }
            })

            # Validate
            assert "validation_results" in result
            assert result["validation_results"]["overall_fidelity_score"] == 0.92
            assert "distribution_similarity" in result["validation_results"]
            assert "correlation_preservation" in result["validation_results"]

    @pytest.mark.asyncio
    async def test_get_generation_status(self):
        """Test generation status retrieval."""
        
        # Execute
        result = await app._tools['get_generation_status']({
            "operation_id": "test_operation_123"
        })

        # Validate
        assert "status" in result
        assert "operation_id" in result

    @pytest.mark.asyncio
    async def test_get_audit_report(self, temp_dir):
        """Test audit report generation."""
        
        with patch('synthetic_data_mcp.server.AuditTrail') as mock_audit_class:
            
            mock_audit = AsyncMock()
            mock_audit.generate_compliance_report.return_value = {
                "report_generated": "2023-01-01T00:00:00",
                "summary": {
                    "total_validations": 100,
                    "total_passed": 95,
                    "overall_pass_rate": 0.95
                },
                "compliance_status": "COMPLIANT"
            }
            mock_audit_class.return_value = mock_audit

            # Execute
            result = await app._tools['get_audit_report']({
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "frameworks": ["HIPAA", "PCI DSS"]
            })

            # Validate
            assert "audit_report" in result
            assert result["audit_report"]["compliance_status"] == "COMPLIANT"
            assert result["audit_report"]["summary"]["overall_pass_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in MCP server."""
        
        with patch('synthetic_data_mcp.server.SyntheticDataGenerator') as mock_generator_class:
            
            # Setup mock to raise exception
            mock_generator = AsyncMock()
            mock_generator.generate_dataset.side_effect = Exception("Test error")
            mock_generator_class.return_value = mock_generator

            request = GenerateSyntheticDatasetRequest(
                domain="healthcare",
                record_count=10,
                schema_config={},
                privacy_config={},
                compliance_frameworks=[],
                format="json"
            )

            # Execute and expect error handling
            with pytest.raises(Exception):
                await app._tools['generate_synthetic_dataset'](request)

    def test_server_initialization(self):
        """Test MCP server initialization."""
        
        # Verify app is properly initialized
        assert app is not None
        assert hasattr(app, '_tools')
        
        # Verify all expected tools are registered
        expected_tools = [
            'generate_synthetic_dataset',
            'validate_compliance', 
            'assess_privacy_risk',
            'validate_statistical_fidelity',
            'get_generation_status',
            'get_audit_report'
        ]
        
        for tool_name in expected_tools:
            assert tool_name in app._tools, f"Tool {tool_name} not found in app"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, sample_healthcare_data):
        """Test handling of concurrent requests."""
        
        import asyncio
        
        with patch('synthetic_data_mcp.server.SyntheticDataGenerator') as mock_generator_class, \
             patch('synthetic_data_mcp.server.PrivacyEngine') as mock_privacy_class, \
             patch('synthetic_data_mcp.server.ComplianceValidator') as mock_compliance_class, \
             patch('synthetic_data_mcp.server.StatisticalValidator') as mock_statistical_class, \
             patch('synthetic_data_mcp.server.AuditTrail') as mock_audit_class:

            # Setup mocks
            mock_generator = AsyncMock()
            mock_generator.generate_dataset.return_value = sample_healthcare_data
            mock_generator_class.return_value = mock_generator

            mock_privacy = AsyncMock()
            mock_privacy.protect_dataset.return_value = (sample_healthcare_data, {"epsilon_used": 0.5})
            mock_privacy_class.return_value = mock_privacy

            mock_compliance = AsyncMock()
            mock_compliance.validate_dataset.return_value = {"compliant": True}
            mock_compliance_class.return_value = mock_compliance

            mock_statistical = AsyncMock()
            mock_statistical.validate_fidelity.return_value = {"overall_fidelity_score": 0.9}
            mock_statistical_class.return_value = mock_statistical

            mock_audit = AsyncMock()
            mock_audit.start_operation.return_value = "audit_concurrent"
            mock_audit_class.return_value = mock_audit

            # Create multiple concurrent requests
            requests = [
                GenerateSyntheticDatasetRequest(
                    domain="healthcare",
                    record_count=10,
                    schema_config={},
                    privacy_config={},
                    compliance_frameworks=[],
                    format="json"
                )
                for _ in range(5)
            ]

            # Execute concurrently
            tasks = [
                app._tools['generate_synthetic_dataset'](request) 
                for request in requests
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate all succeeded
            assert len(results) == 5
            for result in results:
                assert isinstance(result, dict)
                assert "synthetic_data" in result