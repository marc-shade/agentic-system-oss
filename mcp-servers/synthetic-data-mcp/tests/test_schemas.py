"""
Tests for Pydantic schemas and data models.
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from synthetic_data_mcp.schemas.base import (
    BaseRecord
)
from synthetic_data_mcp.server import (
    GenerateSyntheticDatasetRequest,
    ValidateDatasetComplianceRequest,
    AnalyzePrivacyRiskRequest,
    GenerateDomainSchemaRequest
)
from synthetic_data_mcp.schemas.healthcare import (
    PatientRecord,
    PatientDemographics,
    MedicalCondition,
    Encounter,
    HealthcareClaim,
    ClinicalTrial,
)
from synthetic_data_mcp.schemas.finance import (
    Transaction,
    CreditRecord,
    TradingData
)


class TestBaseSchemas:
    """Test base schema classes."""

    def test_base_record_creation(self):
        """Test BaseRecord creation and validation."""
        
        record_data = {
            "record_id": "TEST_001",
            "timestamp": "2023-01-01T12:00:00Z",
            "metadata": {
                "source": "test",
                "version": "1.0"
            }
        }
        
        record = BaseRecord(**record_data)
        assert record.record_id == "TEST_001"
        assert record.metadata["source"] == "test"

    def test_privacy_config_validation(self):
        """Test PrivacyConfig validation."""
        
        # Valid configuration
        config = PrivacyConfig(
            epsilon=1.0,
            delta=1e-5,
            anonymization_level="k_anonymity",
            k_value=5,
            l_value=3,
            t_value=0.1
        )
        
        assert config.epsilon == 1.0
        assert config.k_value == 5
        
        # Invalid epsilon (too small)
        with pytest.raises(ValidationError):
            PrivacyConfig(epsilon=0.0)
        
        # Invalid k_value
        with pytest.raises(ValidationError):
            PrivacyConfig(k_value=1)  # Must be >= 2

    def test_compliance_config_validation(self):
        """Test ComplianceConfig validation."""
        
        config = ComplianceConfig(
            frameworks=["HIPAA", "PCI DSS"],
            risk_tolerance="medium",
            auto_remediation=True
        )
        
        assert len(config.frameworks) == 2
        assert "HIPAA" in config.frameworks
        assert config.risk_tolerance == "medium"
        
        # Invalid framework
        with pytest.raises(ValidationError):
            ComplianceConfig(frameworks=["INVALID_FRAMEWORK"])

    def test_generate_synthetic_dataset_request(self):
        """Test GenerateSyntheticDatasetRequest validation."""
        
        request_data = {
            "domain": "healthcare",
            "record_count": 1000,
            "schema_config": {
                "include_demographics": True,
                "include_conditions": True
            },
            "privacy_config": {
                "epsilon": 1.0,
                "delta": 1e-5
            },
            "compliance_frameworks": ["HIPAA"],
            "format": "json"
        }
        
        request = GenerateSyntheticDatasetRequest(**request_data)
        assert request.domain == "healthcare"
        assert request.record_count == 1000
        assert request.format == "json"
        
        # Invalid domain
        with pytest.raises(ValidationError):
            invalid_request = request_data.copy()
            invalid_request["domain"] = "invalid"
            GenerateSyntheticDatasetRequest(**invalid_request)
        
        # Invalid record count
        with pytest.raises(ValidationError):
            invalid_request = request_data.copy()
            invalid_request["record_count"] = 0
            GenerateSyntheticDatasetRequest(**invalid_request)

    def test_validate_compliance_request(self):
        """Test ValidateComplianceRequest validation."""
        
        request_data = {
            "data": [{"patient_id": "PAT_001", "age": 35}],
            "frameworks": ["HIPAA"],
            "domain": "healthcare"
        }
        
        request = ValidateComplianceRequest(**request_data)
        assert len(request.data) == 1
        assert "HIPAA" in request.frameworks
        assert request.domain == "healthcare"


class TestHealthcareSchemas:
    """Test healthcare-specific schemas."""

    def test_patient_demographics_creation(self):
        """Test PatientDemographics schema."""
        
        demographics_data = {
            "age_group": "25-34",
            "gender": "F",
            "ethnicity": "Hispanic or Latino",
            "race": "White",
            "zip_code": "12345",
            "state": "NY"
        }
        
        demographics = PatientDemographics(**demographics_data)
        assert demographics.age_group == "25-34"
        assert demographics.gender == "F"
        assert demographics.zip_code == "12345"
        
        # Test age group validation
        with pytest.raises(ValidationError):
            invalid_demographics = demographics_data.copy()
            invalid_demographics["age_group"] = "invalid_age_group"
            PatientDemographics(**invalid_demographics)
        
        # Test gender validation
        with pytest.raises(ValidationError):
            invalid_demographics = demographics_data.copy()
            invalid_demographics["gender"] = "X"  # Not in allowed values
            PatientDemographics(**invalid_demographics)

    def test_medical_condition_creation(self):
        """Test MedicalCondition schema."""
        
        condition_data = {
            "icd_10_code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "diagnosis_date": "2023-01-15",
            "severity": "moderate",
            "status": "active"
        }
        
        condition = MedicalCondition(**condition_data)
        assert condition.icd_10_code == "E11.9"
        assert condition.severity == "moderate"
        assert condition.status == "active"
        
        # Test ICD-10 code validation
        with pytest.raises(ValidationError):
            invalid_condition = condition_data.copy()
            invalid_condition["icd_10_code"] = "INVALID"
            MedicalCondition(**invalid_condition)

    def test_encounter_creation(self):
        """Test Encounter schema."""
        
        encounter_data = {
            "encounter_id": "ENC_001",
            "encounter_type": "office_visit",
            "date": "2023-01-15",
            "provider_id": "PROV_001",
            "duration_minutes": 30,
            "location": "clinic"
        }
        
        encounter = Encounter(**encounter_data)
        assert encounter.encounter_id == "ENC_001"
        assert encounter.encounter_type == "office_visit"
        assert encounter.duration_minutes == 30
        
        # Test encounter type validation
        with pytest.raises(ValidationError):
            invalid_encounter = encounter_data.copy()
            invalid_encounter["encounter_type"] = "invalid_type"
            Encounter(**invalid_encounter)

    def test_patient_record_creation(self, generate_test_patient_record):
        """Test complete PatientRecord creation."""
        
        patient_data = generate_test_patient_record()
        patient = PatientRecord(**patient_data)
        
        assert patient.patient_id == "TEST_PAT_001"
        assert patient.demographics.age_group == "25-34"
        assert len(patient.conditions) == 1
        assert len(patient.encounters) == 1
        assert patient.conditions[0].icd_10_code == "E11.9"

    def test_healthcare_claim_creation(self):
        """Test HealthcareClaim schema."""
        
        claim_data = {
            "claim_id": "CLM_001",
            "patient_id": "PAT_001",
            "provider_id": "PROV_001",
            "claim_amount": 1500.00,
            "service_date": "2023-01-15",
            "diagnosis_codes": ["E11.9", "I10"],
            "procedure_codes": ["99213"],
            "claim_status": "approved"
        }
        
        claim = HealthcareClaim(**claim_data)
        assert claim.claim_id == "CLM_001"
        assert claim.claim_amount == 1500.00
        assert len(claim.diagnosis_codes) == 2
        assert claim.claim_status == "approved"

    def test_clinical_trial_creation(self):
        """Test ClinicalTrial schema."""
        
        trial_data = {
            "trial_id": "TRIAL_001",
            "participant_id": "PART_001",
            "study_phase": "phase_3",
            "enrollment_date": "2023-01-01",
            "intervention": "Drug A vs Placebo",
            "primary_outcome": "Blood pressure reduction",
            "status": "active"
        }
        
        trial = ClinicalTrial(**trial_data)
        assert trial.trial_id == "TRIAL_001"
        assert trial.study_phase == "phase_3"
        assert trial.status == "active"

    def test_healthcare_dataset_request(self):
        """Test HealthcareDatasetRequest schema."""
        
        request_data = {
            "include_demographics": True,
            "include_conditions": True,
            "include_encounters": True,
            "include_claims": False,
            "include_clinical_trials": False,
            "age_groups": ["25-34", "35-44"],
            "conditions": ["diabetes", "hypertension"],
            "encounter_types": ["office_visit", "emergency"]
        }
        
        request = HealthcareDatasetRequest(**request_data)
        assert request.include_demographics is True
        assert len(request.age_groups) == 2
        assert "diabetes" in request.conditions


class TestFinanceSchemas:
    """Test finance-specific schemas."""

    def test_transaction_location_creation(self):
        """Test TransactionLocation schema."""
        
        location_data = {
            "city": "New York",
            "state": "NY", 
            "zip_code": "10001",
            "country": "USA"
        }
        
        location = TransactionLocation(**location_data)
        assert location.city == "New York"
        assert location.state == "NY"
        assert location.zip_code == "10001"

    def test_transaction_creation(self, generate_test_transaction):
        """Test Transaction schema."""
        
        transaction_data = generate_test_transaction()
        transaction = Transaction(**transaction_data)
        
        assert transaction.transaction_id == "TEST_TXN_001"
        assert transaction.amount == 125.75
        assert transaction.transaction_type == "purchase"
        assert transaction.category == "dining"
        assert transaction.location.city == "Test City"
        
        # Test amount validation (should be positive)
        with pytest.raises(ValidationError):
            invalid_transaction = transaction_data.copy()
            invalid_transaction["amount"] = -100.0
            Transaction(**invalid_transaction)
        
        # Test transaction type validation
        with pytest.raises(ValidationError):
            invalid_transaction = transaction_data.copy()
            invalid_transaction["transaction_type"] = "invalid_type"
            Transaction(**invalid_transaction)

    def test_credit_record_creation(self):
        """Test CreditRecord schema."""
        
        credit_data = {
            "record_id": "CR_001",
            "account_id": "ACC_001",
            "credit_score": 750,
            "credit_limit": 25000.00,
            "current_balance": 2500.00,
            "payment_history_months": 24,
            "delinquent_accounts": 0,
            "credit_utilization": 0.10,
            "account_age_years": 5.0
        }
        
        credit = CreditRecord(**credit_data)
        assert credit.credit_score == 750
        assert credit.credit_utilization == 0.10
        assert credit.delinquent_accounts == 0
        
        # Test credit score validation
        with pytest.raises(ValidationError):
            invalid_credit = credit_data.copy()
            invalid_credit["credit_score"] = 900  # Too high
            CreditRecord(**invalid_credit)

    def test_trading_data_creation(self):
        """Test TradingData schema."""
        
        trading_data = {
            "trade_id": "TRD_001",
            "account_id": "ACC_001",
            "symbol": "AAPL",
            "trade_type": "buy",
            "quantity": 100,
            "price": 150.00,
            "timestamp": "2023-01-15T09:30:00Z",
            "portfolio_value": 50000.00,
            "risk_score": 0.25
        }
        
        trade = TradingData(**trading_data)
        assert trade.symbol == "AAPL"
        assert trade.trade_type == "buy"
        assert trade.quantity == 100
        assert trade.price == 150.00
        
        # Test quantity validation (positive)
        with pytest.raises(ValidationError):
            invalid_trade = trading_data.copy()
            invalid_trade["quantity"] = -50
            TradingData(**invalid_trade)

    def test_finance_dataset_request(self):
        """Test FinanceDatasetRequest schema."""
        
        request_data = {
            "include_transactions": True,
            "include_credit_records": True,
            "include_trading_data": False,
            "transaction_types": ["purchase", "deposit"],
            "amount_ranges": {
                "min": 10.0,
                "max": 10000.0
            },
            "date_range": {
                "start": "2023-01-01",
                "end": "2023-12-31"
            }
        }
        
        request = FinanceDatasetRequest(**request_data)
        assert request.include_transactions is True
        assert len(request.transaction_types) == 2
        assert request.amount_ranges["min"] == 10.0


class TestSchemaIntegration:
    """Test schema integration and edge cases."""

    def test_nested_schema_validation(self):
        """Test validation of nested schemas."""
        
        # Create a complex patient record with nested objects
        patient_data = {
            "patient_id": "PAT_NESTED_001",
            "demographics": {
                "age_group": "45-54",
                "gender": "M",
                "zip_code": "90210"
            },
            "conditions": [
                {
                    "icd_10_code": "E11.9",
                    "description": "Type 2 diabetes",
                    "diagnosis_date": "2023-01-01",
                    "severity": "moderate"
                },
                {
                    "icd_10_code": "I10",
                    "description": "Essential hypertension", 
                    "diagnosis_date": "2023-02-15",
                    "severity": "mild"
                }
            ],
            "encounters": [
                {
                    "encounter_id": "ENC_NESTED_001",
                    "encounter_type": "office_visit",
                    "date": "2023-01-01",
                    "provider_id": "PROV_001"
                }
            ]
        }
        
        # Should validate successfully
        patient = PatientRecord(**patient_data)
        assert len(patient.conditions) == 2
        assert patient.conditions[0].severity == "moderate"
        assert patient.conditions[1].severity == "mild"

    def test_optional_fields_handling(self):
        """Test handling of optional fields."""
        
        # Minimal patient record with only required fields
        minimal_patient = {
            "patient_id": "PAT_MINIMAL",
            "demographics": {
                "age_group": "35-44",
                "gender": "F"
            }
        }
        
        patient = PatientRecord(**minimal_patient)
        assert patient.patient_id == "PAT_MINIMAL"
        assert patient.conditions == []  # Default empty list
        assert patient.encounters == []  # Default empty list

    def test_data_type_coercion(self):
        """Test automatic data type coercion."""
        
        # String numbers should be coerced to float
        transaction_data = {
            "transaction_id": "TXN_COERCE",
            "account_id": "ACC_001",
            "amount": "123.45",  # String that should become float
            "transaction_type": "purchase",
            "category": "groceries",
            "timestamp": "2023-01-15T12:00:00Z",
            "merchant": "Store",
            "location": {
                "city": "City",
                "state": "ST",
                "zip_code": "12345"
            }
        }
        
        transaction = Transaction(**transaction_data)
        assert isinstance(transaction.amount, float)
        assert transaction.amount == 123.45

    def test_schema_serialization(self, generate_test_patient_record):
        """Test schema serialization to dict/JSON."""
        
        patient_data = generate_test_patient_record()
        patient = PatientRecord(**patient_data)
        
        # Test dict serialization
        patient_dict = patient.model_dump()
        assert isinstance(patient_dict, dict)
        assert patient_dict["patient_id"] == "TEST_PAT_001"
        
        # Test JSON serialization
        patient_json = patient.model_dump_json()
        assert isinstance(patient_json, str)
        assert "TEST_PAT_001" in patient_json

    def test_schema_validation_error_messages(self):
        """Test that validation errors provide helpful messages."""
        
        # Invalid patient record missing required field
        invalid_data = {
            "demographics": {
                "age_group": "25-34"
                # Missing required 'gender' field
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PatientRecord(**invalid_data)
        
        error = exc_info.value
        assert "patient_id" in str(error)  # Should mention missing field
        assert "field required" in str(error)

    def test_custom_validators(self):
        """Test custom field validators."""
        
        # Test ICD-10 code pattern validation
        with pytest.raises(ValidationError) as exc_info:
            MedicalCondition(
                icd_10_code="INVALID_CODE",
                description="Test condition",
                diagnosis_date="2023-01-01"
            )
        
        assert "ICD-10" in str(exc_info.value) or "pattern" in str(exc_info.value)