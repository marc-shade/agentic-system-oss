"""
Tests for compliance validation system.
"""

import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List

from synthetic_data_mcp.compliance.validator import (
    ComplianceValidator,
    HIPAAValidator,
    PCIDSSValidator,
    SOXValidator
)


class TestComplianceValidator:
    """Test suite for compliance validation."""

    @pytest.fixture
    async def compliance_validator(self):
        """Create compliance validator instance."""
        return ComplianceValidator()

    @pytest.mark.asyncio
    async def test_validate_dataset_hipaa_compliant(self, compliance_validator, sample_healthcare_data):
        """Test HIPAA compliant dataset validation."""
        
        # Ensure sample data is HIPAA compliant (no direct identifiers)
        compliant_data = []
        for record in sample_healthcare_data:
            clean_record = record.copy()
            # Remove any potential identifiers
            if "demographics" in clean_record:
                demographics = clean_record["demographics"].copy()
                demographics.pop("full_name", None)
                demographics.pop("ssn", None) 
                demographics.pop("phone", None)
                demographics.pop("email", None)
                clean_record["demographics"] = demographics
            compliant_data.append(clean_record)
        
        result = await compliance_validator.validate_dataset(
            data=compliant_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        assert result["compliant"] is True
        assert result["framework"] == "HIPAA"
        assert len(result["violations"]) == 0
        assert result["risk_score"] < 0.3  # Low risk

    @pytest.mark.asyncio
    async def test_validate_dataset_hipaa_violations(self, compliance_validator):
        """Test HIPAA violation detection."""
        
        # Create data with HIPAA violations
        violating_data = [
            {
                "patient_id": "PAT_001",
                "full_name": "John Smith",  # HIPAA violation - name
                "ssn": "123-45-6789",      # HIPAA violation - SSN
                "demographics": {
                    "age": 35,  # HIPAA violation - exact age
                    "zip_code": "12345-6789",  # HIPAA violation - full ZIP
                    "phone": "555-123-4567"    # HIPAA violation - phone
                },
                "conditions": [
                    {
                        "icd_10_code": "E11.9",
                        "description": "Type 2 diabetes"
                    }
                ]
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=violating_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        assert result["compliant"] is False
        assert result["framework"] == "HIPAA"
        assert len(result["violations"]) > 0
        assert result["risk_score"] > 0.5  # High risk
        
        # Check specific violations
        violation_types = [v["violation_type"] for v in result["violations"]]
        assert "hipaa_identifier" in violation_types
        
        # Check recommendations exist
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_validate_dataset_pci_dss_compliant(self, compliance_validator, sample_finance_data):
        """Test PCI DSS compliant dataset validation."""
        
        # Ensure sample data is PCI DSS compliant
        compliant_data = []
        for record in sample_finance_data:
            clean_record = record.copy()
            # Remove any payment card data
            clean_record.pop("card_number", None)
            clean_record.pop("cvv", None)
            clean_record.pop("expiry_date", None)
            compliant_data.append(clean_record)
        
        result = await compliance_validator.validate_dataset(
            data=compliant_data,
            frameworks=["PCI DSS"],
            domain="finance"
        )
        
        assert result["compliant"] is True
        assert result["framework"] == "PCI DSS"
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_validate_dataset_pci_dss_violations(self, compliance_validator):
        """Test PCI DSS violation detection."""
        
        violating_data = [
            {
                "transaction_id": "TXN_001",
                "card_number": "4111-1111-1111-1111",  # PCI DSS violation
                "cvv": "123",                          # PCI DSS violation
                "expiry_date": "12/25",                # PCI DSS violation
                "amount": 100.00,
                "merchant": "Test Store"
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=violating_data,
            frameworks=["PCI DSS"],
            domain="finance"
        )
        
        assert result["compliant"] is False
        assert len(result["violations"]) > 0
        
        violation_types = [v["violation_type"] for v in result["violations"]]
        assert "pci_card_data" in violation_types

    @pytest.mark.asyncio
    async def test_validate_dataset_sox_compliance(self, compliance_validator):
        """Test SOX compliance validation."""
        
        compliant_data = [
            {
                "transaction_id": "TXN_001",
                "account_id": "ACC_001",
                "amount": 1500.00,
                "transaction_date": "2023-01-15",
                "transaction_type": "journal_entry",
                "approval_status": "approved",
                "audit_trail": "complete"
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=compliant_data,
            frameworks=["SOX"],
            domain="finance"
        )
        
        assert result["compliant"] is True
        assert result["framework"] == "SOX"

    @pytest.mark.asyncio
    async def test_validate_dataset_gdpr_compliance(self, compliance_validator):
        """Test GDPR compliance validation."""
        
        # GDPR compliant data (anonymized, no PII)
        compliant_data = [
            {
                "user_id": "USER_ANON_001",
                "age_group": "25-34",
                "country": "DE", 
                "preferences": {
                    "marketing_consent": False,
                    "data_processing_consent": True
                },
                "anonymized": True
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=compliant_data,
            frameworks=["GDPR"],
            domain="general"
        )
        
        assert result["compliant"] is True

    @pytest.mark.asyncio
    async def test_multiple_frameworks_validation(self, compliance_validator):
        """Test validation against multiple compliance frameworks."""
        
        healthcare_finance_data = [
            {
                "record_id": "REC_001",
                "patient_id": "PAT_ANON_001",
                "demographics": {
                    "age_group": "35-44",
                    "gender": "F",
                    "zip_code": "12345"
                },
                "financial_info": {
                    "insurance_id": "INS_001",
                    "payment_method": "insurance"
                    # No card numbers or sensitive payment data
                }
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=healthcare_finance_data,
            frameworks=["HIPAA", "PCI DSS"],
            domain="healthcare"
        )
        
        # Should validate against both frameworks
        assert isinstance(result, dict)
        assert "compliant" in result

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, compliance_validator):
        """Test risk score calculation accuracy."""
        
        # High risk data
        high_risk_data = [
            {
                "patient_name": "John Doe",
                "ssn": "123-45-6789", 
                "address": "123 Main St",
                "phone": "555-1234",
                "email": "john@example.com"
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=high_risk_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        assert result["risk_score"] > 0.8  # Very high risk
        
        # Low risk data
        low_risk_data = [
            {
                "patient_id": "PAT_ANON_001",
                "age_group": "25-34",
                "condition_category": "chronic"
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=low_risk_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        assert result["risk_score"] < 0.2  # Very low risk


class TestHIPAAValidator:
    """Test HIPAA-specific validation logic."""

    @pytest.fixture
    def hipaa_validator(self):
        """Create HIPAA validator instance."""
        return HIPAAValidator()

    def test_safe_harbor_identifiers_detection(self, hipaa_validator):
        """Test detection of all 18 HIPAA Safe Harbor identifiers."""
        
        # Test data with various identifiers
        test_data = {
            "patient_name": "John Smith",                    # 1. Names
            "address": "123 Main St, Anytown, NY 12345-6789", # 2. Geographic subdivisions < state
            "birth_date": "1988-03-15",                      # 3. Dates related to individual
            "phone": "555-123-4567",                         # 4. Telephone numbers
            "fax": "555-123-4568",                           # 5. Fax numbers
            "email": "john.smith@email.com",                 # 6. Email addresses
            "ssn": "123-45-6789",                           # 7. Social security numbers
            "mrn": "MRN123456",                             # 8. Medical record numbers
            "health_plan_id": "HP123456789",                # 9. Health plan beneficiary numbers
            "account_number": "ACC987654321",               # 10. Account numbers
            "license_plate": "ABC123",                      # 11. Certificate/license numbers
            "url": "http://johnswebsite.com",               # 12. Web URLs
            "ip_address": "192.168.1.1",                   # 13. Internet protocol addresses
            "device_serial": "DEV123456789",               # 14. Device identifiers
            "photo": "patient_photo.jpg"                   # 15. Photos and comparable images
        }
        
        violations = hipaa_validator.detect_violations(test_data)
        
        # Should detect multiple violation types
        assert len(violations) > 10
        
        violation_types = [v["identifier_type"] for v in violations]
        expected_types = ["name", "address", "date", "phone", "email", "ssn"]
        
        for expected_type in expected_types:
            assert any(expected_type in vtype for vtype in violation_types)

    def test_safe_zip_code_validation(self, hipaa_validator):
        """Test ZIP code validation per HIPAA Safe Harbor."""
        
        # Valid ZIP codes (first 3 digits only)
        valid_data = {"zip_code": "12345"}
        violations = hipaa_validator.detect_violations(valid_data)
        zip_violations = [v for v in violations if "zip" in v.get("field", "").lower()]
        assert len(zip_violations) == 0
        
        # Invalid ZIP codes (too specific)
        invalid_data = {"zip_code": "12345-6789"}
        violations = hipaa_validator.detect_violations(invalid_data)
        zip_violations = [v for v in violations if "zip" in v.get("field", "").lower()]
        assert len(zip_violations) > 0

    def test_age_group_validation(self, hipaa_validator):
        """Test age validation per HIPAA requirements."""
        
        # Valid age group
        valid_data = {"age_group": "25-34"}
        violations = hipaa_validator.detect_violations(valid_data)
        age_violations = [v for v in violations if "age" in v.get("field", "").lower()]
        assert len(age_violations) == 0
        
        # Invalid exact age
        invalid_data = {"age": 35}
        violations = hipaa_validator.detect_violations(invalid_data)
        age_violations = [v for v in violations if "age" in str(v).lower()]
        assert len(age_violations) > 0

    def test_date_validation(self, hipaa_validator):
        """Test date validation per HIPAA requirements."""
        
        # Dates should be year-only or removed for ages > 89
        test_cases = [
            {"birth_date": "1988-01-01", "should_violate": True},   # Full date
            {"birth_year": "1988", "should_violate": False},        # Year only
            {"service_date": "2023", "should_violate": False},      # Year only
        ]
        
        for test_case in test_cases:
            data = {k: v for k, v in test_case.items() if k != "should_violate"}
            violations = hipaa_validator.detect_violations(data)
            date_violations = [v for v in violations if "date" in v.get("field", "").lower()]
            
            if test_case["should_violate"]:
                assert len(date_violations) > 0
            else:
                assert len(date_violations) == 0


class TestPCIDSSValidator:
    """Test PCI DSS-specific validation logic."""

    @pytest.fixture
    def pci_validator(self):
        """Create PCI DSS validator instance."""
        return PCIDSSValidator()

    def test_credit_card_detection(self, pci_validator):
        """Test credit card number detection."""
        
        test_cases = [
            # Valid credit card patterns that should be detected
            {"card_number": "4111111111111111", "should_violate": True},     # Visa
            {"card_number": "4111-1111-1111-1111", "should_violate": True},  # Visa with dashes
            {"card_number": "4111 1111 1111 1111", "should_violate": True},  # Visa with spaces
            {"card_number": "5555555555554444", "should_violate": True},     # MasterCard
            {"card_number": "378282246310005", "should_violate": True},      # American Express
            
            # Non-card numbers that should not be detected
            {"account_number": "1234567890", "should_violate": False},       # Too short
            {"reference_id": "REF123456789", "should_violate": False},       # Non-numeric prefix
        ]
        
        for test_case in test_cases:
            data = {k: v for k, v in test_case.items() if k != "should_violate"}
            violations = pci_validator.detect_violations(data)
            card_violations = [v for v in violations if "card" in v.get("violation_type", "").lower()]
            
            if test_case["should_violate"]:
                assert len(card_violations) > 0, f"Should detect violation in: {data}"
            else:
                assert len(card_violations) == 0, f"Should not detect violation in: {data}"

    def test_cvv_detection(self, pci_validator):
        """Test CVV/CVC detection."""
        
        violating_data = {
            "cvv": "123",
            "cvc": "4567",
            "security_code": "123"
        }
        
        violations = pci_validator.detect_violations(violating_data)
        cvv_violations = [v for v in violations if "cvv" in v.get("violation_type", "").lower() or "cvc" in v.get("violation_type", "").lower()]
        
        assert len(cvv_violations) > 0

    def test_expiry_date_detection(self, pci_validator):
        """Test expiry date detection."""
        
        violating_data = {
            "expiry_date": "12/25",
            "exp_month": "12",
            "exp_year": "2025"
        }
        
        violations = pci_validator.detect_violations(violating_data)
        expiry_violations = [v for v in violations if "expiry" in v.get("violation_type", "").lower()]
        
        assert len(expiry_violations) > 0


class TestSOXValidator:
    """Test SOX-specific validation logic."""

    @pytest.fixture
    def sox_validator(self):
        """Create SOX validator instance."""
        return SOXValidator()

    def test_financial_control_validation(self, sox_validator):
        """Test SOX financial controls validation."""
        
        # Compliant financial record
        compliant_data = {
            "transaction_id": "TXN_001",
            "amount": 1500.00,
            "approval_required": True,
            "approver_id": "MGR_001",
            "approval_date": "2023-01-15",
            "audit_trail": "complete",
            "segregation_of_duties": True
        }
        
        violations = sox_validator.detect_violations(compliant_data)
        assert len(violations) == 0
        
        # Non-compliant record (missing controls)
        non_compliant_data = {
            "transaction_id": "TXN_002",
            "amount": 5000.00,
            # Missing approval information
            # Missing audit trail
        }
        
        violations = sox_validator.detect_violations(non_compliant_data)
        assert len(violations) > 0

    def test_audit_trail_requirements(self, sox_validator):
        """Test audit trail requirements."""
        
        # Missing audit trail
        data_no_trail = {
            "transaction_id": "TXN_001",
            "amount": 1000.00
        }
        
        violations = sox_validator.detect_violations(data_no_trail)
        trail_violations = [v for v in violations if "audit" in v.get("violation_type", "").lower()]
        
        assert len(trail_violations) > 0


class TestGDPRValidator:
    """Test GDPR-specific validation logic."""

    @pytest.fixture
    def gdpr_validator(self):
        """Create GDPR validator instance."""
        return GDPRValidator()

    def test_personal_data_detection(self, gdpr_validator):
        """Test personal data detection under GDPR."""
        
        violating_data = {
            "full_name": "John Smith",
            "email": "john@example.com",
            "ip_address": "192.168.1.1",
            "device_id": "DEV123456",
            "location_data": "52.5200° N, 13.4050° E"
        }
        
        violations = gdpr_validator.detect_violations(violating_data)
        assert len(violations) > 0
        
        # Check for personal data violations
        personal_data_violations = [v for v in violations if "personal_data" in v.get("violation_type", "")]
        assert len(personal_data_violations) > 0

    def test_consent_validation(self, gdpr_validator):
        """Test GDPR consent requirements."""
        
        # Missing consent data
        data_no_consent = {
            "user_id": "USER_001",
            "email": "user@example.com",
            "marketing_data": "some data"
        }
        
        violations = gdpr_validator.detect_violations(data_no_consent)
        consent_violations = [v for v in violations if "consent" in v.get("violation_type", "").lower()]
        
        assert len(consent_violations) > 0


class TestComplianceIntegration:
    """Test compliance system integration."""

    @pytest.mark.asyncio
    async def test_compliance_remediation_suggestions(self, compliance_validator):
        """Test that compliance violations include remediation suggestions."""
        
        violating_data = [
            {
                "patient_name": "John Smith",
                "ssn": "123-45-6789",
                "phone": "555-123-4567"
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=violating_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        
        # Check that recommendations are actionable
        recommendations = result["recommendations"]
        actionable_keywords = ["remove", "anonymize", "tokenize", "mask", "replace"]
        
        recommendation_text = " ".join(recommendations).lower()
        assert any(keyword in recommendation_text for keyword in actionable_keywords)

    @pytest.mark.asyncio
    async def test_compliance_severity_levels(self, compliance_validator):
        """Test compliance violation severity levels."""
        
        # Critical violation (SSN)
        critical_data = [{"ssn": "123-45-6789"}]
        
        result = await compliance_validator.validate_dataset(
            data=critical_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        # Should have high risk score for critical violations
        assert result["risk_score"] > 0.7
        
        # Minor violation (5-digit ZIP instead of 3)
        minor_data = [{"zip_code": "12345"}]
        
        result = await compliance_validator.validate_dataset(
            data=minor_data,
            frameworks=["HIPAA"],
            domain="healthcare"
        )
        
        # Should have lower risk score
        assert result["risk_score"] < 0.3

    @pytest.mark.asyncio
    async def test_cross_framework_conflicts(self, compliance_validator):
        """Test handling of cross-framework compliance conflicts."""
        
        # Data that might comply with one framework but not another
        mixed_compliance_data = [
            {
                "user_id": "USER_001",
                "age_group": "25-34",        # HIPAA compliant (age range)
                "zip_code": "12345",         # HIPAA compliant
                "email_hash": "abc123...",   # GDPR might require more
                "consent_date": "2023-01-01" # GDPR requirement
            }
        ]
        
        result = await compliance_validator.validate_dataset(
            data=mixed_compliance_data,
            frameworks=["HIPAA", "GDPR"],
            domain="healthcare"
        )
        
        # Should handle multiple frameworks gracefully
        assert "compliant" in result
        assert isinstance(result["risk_score"], (int, float))