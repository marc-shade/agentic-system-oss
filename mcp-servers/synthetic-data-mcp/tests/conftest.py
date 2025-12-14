"""
Pytest configuration and shared fixtures for synthetic data MCP tests.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import pandas as pd
from pydantic import BaseModel

from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.privacy.engine import PrivacyEngine
from synthetic_data_mcp.compliance.validator import ComplianceValidator
from synthetic_data_mcp.validation.statistical import StatisticalValidator
from synthetic_data_mcp.utils.audit import AuditTrail
from synthetic_data_mcp.schemas.healthcare import PatientRecord
from synthetic_data_mcp.schemas.finance import Transaction


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_dspy_model():
    """Mock DSPy model for testing."""
    mock_model = MagicMock()
    mock_model.generate = AsyncMock(return_value={
        "records": [
            {
                "patient_id": "PAT_001",
                "demographics": {
                    "age_group": "30-39",
                    "gender": "F",
                    "zip_code": "12345"
                },
                "conditions": [
                    {
                        "icd_10_code": "E11.9",
                        "description": "Type 2 diabetes mellitus without complications"
                    }
                ]
            }
        ]
    })
    return mock_model


@pytest.fixture
async def synthetic_generator(mock_dspy_model) -> SyntheticDataGenerator:
    """Create a synthetic data generator with mocked DSPy."""
    generator = SyntheticDataGenerator(
        healthcare_model=mock_dspy_model,
        finance_model=mock_dspy_model
    )
    return generator


@pytest.fixture
async def privacy_engine() -> PrivacyEngine:
    """Create a privacy engine instance."""
    return PrivacyEngine(epsilon=1.0, delta=1e-5)


@pytest.fixture
async def compliance_validator() -> ComplianceValidator:
    """Create a compliance validator instance."""
    return ComplianceValidator()


@pytest.fixture
async def statistical_validator() -> StatisticalValidator:
    """Create a statistical validator instance."""
    return StatisticalValidator()


@pytest.fixture
async def audit_trail(temp_dir) -> AuditTrail:
    """Create an audit trail instance with temporary database."""
    db_path = temp_dir / "test_audit.db"
    return AuditTrail(str(db_path))


@pytest.fixture
def sample_healthcare_data() -> List[Dict[str, Any]]:
    """Sample healthcare data for testing."""
    return [
        {
            "patient_id": "PAT_001",
            "demographics": {
                "age": 35,
                "gender": "F",
                "zip_code": "12345",
                "state": "NY"
            },
            "conditions": [
                {
                    "icd_10_code": "E11.9",
                    "description": "Type 2 diabetes mellitus",
                    "diagnosis_date": "2023-01-15"
                }
            ],
            "encounters": [
                {
                    "encounter_id": "ENC_001",
                    "encounter_type": "office_visit",
                    "date": "2023-01-15",
                    "provider_id": "PROV_001"
                }
            ]
        },
        {
            "patient_id": "PAT_002", 
            "demographics": {
                "age": 42,
                "gender": "M",
                "zip_code": "54321",
                "state": "CA"
            },
            "conditions": [
                {
                    "icd_10_code": "I10",
                    "description": "Essential hypertension",
                    "diagnosis_date": "2023-02-20"
                }
            ],
            "encounters": [
                {
                    "encounter_id": "ENC_002",
                    "encounter_type": "office_visit",
                    "date": "2023-02-20",
                    "provider_id": "PROV_002"
                }
            ]
        }
    ]


@pytest.fixture
def sample_finance_data() -> List[Dict[str, Any]]:
    """Sample financial data for testing."""
    return [
        {
            "transaction_id": "TXN_001",
            "account_id": "ACC_001",
            "amount": 1500.50,
            "transaction_type": "purchase",
            "category": "groceries",
            "timestamp": "2023-01-15T14:30:00Z",
            "merchant": "SuperMart",
            "location": {
                "city": "New York",
                "state": "NY",
                "zip_code": "10001"
            }
        },
        {
            "transaction_id": "TXN_002",
            "account_id": "ACC_002", 
            "amount": 2500.00,
            "transaction_type": "deposit",
            "category": "salary",
            "timestamp": "2023-01-01T09:00:00Z",
            "merchant": "Company Payroll",
            "location": {
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94102"
            }
        }
    ]


@pytest.fixture
def sample_compliance_violations() -> List[Dict[str, Any]]:
    """Sample compliance violations for testing."""
    return [
        {
            "violation_type": "hipaa_identifier",
            "field": "patient_name",
            "value": "John Smith",
            "identifier_type": "name",
            "confidence": 0.95,
            "recommendation": "Remove or tokenize patient name"
        },
        {
            "violation_type": "pci_card_number",
            "field": "payment_info.card_number", 
            "value": "4111-1111-1111-1111",
            "identifier_type": "credit_card",
            "confidence": 1.0,
            "recommendation": "Mask or tokenize card number"
        }
    ]


@pytest.fixture
def sample_privacy_metrics() -> Dict[str, Any]:
    """Sample privacy metrics for testing."""
    return {
        "epsilon_used": 0.5,
        "delta_used": 1e-6,
        "k_anonymity": 5,
        "l_diversity": 3,
        "t_closeness": 0.1,
        "privacy_budget_remaining": 0.5,
        "re_identification_risk": 0.02,
        "utility_score": 0.87
    }


@pytest.fixture 
def sample_statistical_results() -> Dict[str, Any]:
    """Sample statistical validation results."""
    return {
        "distribution_similarity": {
            "ks_test_pvalue": 0.15,
            "anderson_darling_statistic": 0.5,
            "chi_square_pvalue": 0.25
        },
        "correlation_preservation": {
            "pearson_correlation_diff": 0.05,
            "spearman_correlation_diff": 0.03,
            "kendall_tau_diff": 0.02
        },
        "ml_utility": {
            "classification_accuracy_diff": 0.02,
            "regression_r2_diff": 0.01,
            "clustering_silhouette_diff": 0.03
        },
        "overall_fidelity_score": 0.92
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for DSPy integration."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(
            message=MagicMock(
                content='{"records": [{"patient_id": "PAT_001", "age": 35}]}'
            )
        )]
    ))
    return mock_client


class MockDataFrame:
    """Mock pandas DataFrame for testing."""
    
    def __init__(self, data):
        self.data = data
        self.columns = list(data[0].keys()) if data else []
        
    def to_dict(self, orient='records'):
        return self.data
        
    def describe(self):
        return pd.DataFrame({
            'count': [len(self.data)],
            'mean': [100.0],
            'std': [10.0]
        })
        
    def corr(self):
        return pd.DataFrame([[1.0, 0.5], [0.5, 1.0]])


@pytest.fixture
def mock_pandas_dataframe(sample_healthcare_data):
    """Mock pandas DataFrame."""
    return MockDataFrame(sample_healthcare_data)


# Test data generators
def generate_test_patient_record() -> Dict[str, Any]:
    """Generate a test patient record."""
    return {
        "patient_id": "TEST_PAT_001",
        "demographics": {
            "age_group": "25-34",
            "gender": "F", 
            "zip_code": "12345",
            "state": "NY",
            "ethnicity": "Hispanic"
        },
        "conditions": [
            {
                "icd_10_code": "E11.9",
                "description": "Type 2 diabetes mellitus",
                "diagnosis_date": "2023-01-15",
                "severity": "moderate"
            }
        ],
        "encounters": [
            {
                "encounter_id": "TEST_ENC_001",
                "encounter_type": "office_visit",
                "date": "2023-01-15",
                "provider_id": "TEST_PROV_001",
                "duration_minutes": 30
            }
        ]
    }


def generate_test_transaction() -> Dict[str, Any]:
    """Generate a test financial transaction."""
    return {
        "transaction_id": "TEST_TXN_001",
        "account_id": "TEST_ACC_001",
        "amount": 125.75,
        "transaction_type": "purchase",
        "category": "dining",
        "timestamp": "2023-01-15T12:00:00Z",
        "merchant": "Test Restaurant",
        "location": {
            "city": "Test City",
            "state": "NY",
            "zip_code": "12345"
        }
    }


# Test utilities
def assert_hipaa_compliant(data: Dict[str, Any]) -> bool:
    """Assert that data is HIPAA compliant."""
    hipaa_identifiers = [
        "patient_name", "ssn", "medical_record_number", 
        "health_plan_number", "account_numbers", "certificate_numbers",
        "license_numbers", "vehicle_identifiers", "device_identifiers",
        "urls", "ip_addresses", "biometric_identifiers", "facial_photos",
        "fingerprints", "voiceprints"
    ]
    
    for identifier in hipaa_identifiers:
        assert identifier not in str(data), f"HIPAA identifier found: {identifier}"
    
    return True


def assert_pci_compliant(data: Dict[str, Any]) -> bool:
    """Assert that data is PCI DSS compliant."""
    # Check for credit card numbers (simplified)
    data_str = str(data)
    
    # Basic credit card pattern (simplified for testing)
    import re
    cc_pattern = r'\b4[0-9]{12}(?:[0-9]{3})?\b|5[1-5][0-9]{14}\b'
    
    assert not re.search(cc_pattern, data_str), "Credit card number found in data"
    
    return True


def calculate_k_anonymity(data: List[Dict[str, Any]], quasi_identifiers: List[str]) -> int:
    """Calculate k-anonymity for test data."""
    if not data:
        return 0
        
    # Group records by quasi-identifier combinations
    groups = {}
    for record in data:
        key = tuple(str(record.get(qi, '')) for qi in quasi_identifiers)
        groups[key] = groups.get(key, 0) + 1
    
    return min(groups.values()) if groups else 0