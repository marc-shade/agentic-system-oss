"""
Compliance validation engine for regulatory frameworks.

This module implements validation logic for healthcare (HIPAA, FDA) and 
finance (SOX, PCI DSS) compliance requirements with detailed reporting.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger
from pydantic import BaseModel

from ..schemas.base import ComplianceFramework, DataDomain, ComplianceResult


class HIPAAValidator:
    """HIPAA Safe Harbor compliance validator."""
    
    # HIPAA Safe Harbor 18 identifiers
    SAFE_HARBOR_IDENTIFIERS = {
        "names": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # Simple name pattern
        "geographic_subdivisions": r"\b\d{5}(-\d{4})?\b",  # Full ZIP codes
        "dates": r"\b\d{4}-\d{2}-\d{2}\b",  # Specific dates
        "telephone_numbers": r"\b\d{3}-\d{3}-\d{4}\b",
        "fax_numbers": r"\bfax:?\s*\d{3}-\d{3}-\d{4}\b",
        "email_addresses": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "medical_record_numbers": r"\bMRN\d{6,}\b",
        "health_plan_beneficiary": r"\b[A-Z]{2,3}\d{6,}\b",
        "account_numbers": r"\bACCT\d{6,}\b",
        "certificate_numbers": r"\bCERT\d{6,}\b",
        "vehicle_identifiers": r"\b[A-Z0-9]{17}\b",  # VIN
        "device_identifiers": r"\bDEV\d{6,}\b",
        "web_urls": r"https?://[^\s]+",
        "ip_addresses": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "biometric_identifiers": r"\bBIO\d{6,}\b",
        "face_photos": r"\.(?:jpg|jpeg|png|gif)\b",
        "other_unique_identifying": r"\b[A-Z]{2,}\d{6,}\b"
    }
    
    def validate_dataset(self, records: List[Dict[str, Any]]) -> ComplianceResult:
        """Validate dataset for HIPAA Safe Harbor compliance."""
        
        violations = []
        risk_score = 0.0
        total_checks = 0
        passed_checks = 0
        
        for i, record in enumerate(records):
            record_violations = self._validate_record(record, i)
            violations.extend(record_violations)
            
            # Calculate risk based on violations
            total_checks += len(self.SAFE_HARBOR_IDENTIFIERS)
            passed_checks += len(self.SAFE_HARBOR_IDENTIFIERS) - len(record_violations)
        
        # Calculate overall risk score
        if total_checks > 0:
            risk_score = 1.0 - (passed_checks / total_checks)
        
        # HIPAA requires "very small" risk (typically <0.04)
        passed = risk_score < 0.04 and len(violations) == 0
        
        # Generate recommendations
        recommendations = self._generate_hipaa_recommendations(violations)
        
        return ComplianceResult(
            passed=passed,
            score=1.0 - risk_score,
            framework=ComplianceFramework.HIPAA,
            risk_score=risk_score,
            violations=violations,
            certification_ready=passed and risk_score < 0.01,
            details={
                "total_records_checked": len(records),
                "total_violations": len(violations),
                "safe_harbor_compliance": risk_score < 0.04,
                "expert_determination_required": risk_score >= 0.04,
                "validation_timestamp": datetime.now().isoformat()
            },
            recommendations=recommendations
        )
    
    def _validate_record(self, record: Dict[str, Any], record_index: int) -> List[Dict[str, Any]]:
        """Validate individual record for HIPAA violations."""
        violations = []
        
        # Convert record to string for pattern matching
        record_str = str(record)
        
        for identifier_type, pattern in self.SAFE_HARBOR_IDENTIFIERS.items():
            matches = re.findall(pattern, record_str, re.IGNORECASE)
            
            if matches:
                violations.append({
                    "type": "hipaa_identifier_detected",
                    "identifier_type": identifier_type,
                    "record_index": record_index,
                    "matches_found": len(matches),
                    "severity": "high",
                    "description": f"Detected {identifier_type} in record {record_index}",
                    "remediation": f"Remove or de-identify {identifier_type}"
                })
        
        # Check for age violations (>89 requires special handling)
        age_violations = self._check_age_compliance(record, record_index)
        violations.extend(age_violations)
        
        # Check for small population risk
        geographic_violations = self._check_geographic_compliance(record, record_index)
        violations.extend(geographic_violations)
        
        return violations
    
    def _check_age_compliance(self, record: Dict[str, Any], record_index: int) -> List[Dict[str, Any]]:
        """Check age-related HIPAA compliance."""
        violations = []
        
        # Check for specific ages over 89
        age_fields = ["age", "patient_age", "birth_date", "dob"]
        
        for field in age_fields:
            if field in record:
                value = record[field]
                
                # Check for specific ages > 89
                if isinstance(value, int) and value > 89:
                    violations.append({
                        "type": "hipaa_age_violation",
                        "field": field,
                        "record_index": record_index,
                        "value": value,
                        "severity": "medium",
                        "description": f"Age {value} > 89 requires aggregation to 90+",
                        "remediation": "Aggregate all ages 90 and above to '90+'"
                    })
        
        return violations
    
    def _check_geographic_compliance(self, record: Dict[str, Any], record_index: int) -> List[Dict[str, Any]]:
        """Check geographic subdivisions compliance."""
        violations = []
        
        # Check for full ZIP codes (should be 3-digit only)
        zip_fields = ["zip_code", "zipcode", "postal_code", "address_zip"]
        
        for field in zip_fields:
            if field in record and record[field]:
                zip_value = str(record[field])
                
                if len(zip_value) > 3 and zip_value.isdigit():
                    violations.append({
                        "type": "hipaa_geographic_violation",
                        "field": field,
                        "record_index": record_index,
                        "value": zip_value,
                        "severity": "high",
                        "description": f"Full ZIP code {zip_value} detected",
                        "remediation": "Use only first 3 digits of ZIP code"
                    })
        
        return violations
    
    def _generate_hipaa_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate HIPAA compliance recommendations."""
        recommendations = []
        
        violation_types = set(v["type"] for v in violations)
        
        if "hipaa_identifier_detected" in violation_types:
            recommendations.append("Remove all 18 HIPAA Safe Harbor identifiers from datasets")
            recommendations.append("Implement automated PII detection and removal")
            recommendations.append("Consider using synthetic identifiers for tracking")
        
        if "hipaa_age_violation" in violation_types:
            recommendations.append("Aggregate all ages 90+ to prevent re-identification")
            recommendations.append("Use age groups instead of specific ages when possible")
        
        if "hipaa_geographic_violation" in violation_types:
            recommendations.append("Use 3-digit ZIP codes instead of full ZIP codes")
            recommendations.append("Consider state-level geographic indicators only")
        
        if not violations:
            recommendations.append("Dataset appears HIPAA Safe Harbor compliant")
            recommendations.append("Consider expert determination for additional validation")
            recommendations.append("Maintain audit trail documentation")
        
        return recommendations


class SOXValidator:
    """Sarbanes-Oxley Act compliance validator."""
    
    def validate_dataset(self, records: List[Dict[str, Any]]) -> ComplianceResult:
        """Validate dataset for SOX compliance."""
        
        violations = []
        risk_score = 0.0
        
        # SOX Section 302 and 404 requirements
        internal_controls_violations = self._check_internal_controls(records)
        data_integrity_violations = self._check_data_integrity(records)
        audit_trail_violations = self._check_audit_trail(records)
        
        violations.extend(internal_controls_violations)
        violations.extend(data_integrity_violations)
        violations.extend(audit_trail_violations)
        
        # Calculate risk score
        total_requirements = 3  # internal controls, data integrity, audit trail
        failed_requirements = sum([
            len(internal_controls_violations) > 0,
            len(data_integrity_violations) > 0,
            len(audit_trail_violations) > 0
        ])
        
        risk_score = failed_requirements / total_requirements
        passed = len(violations) == 0
        
        recommendations = self._generate_sox_recommendations(violations)
        
        return ComplianceResult(
            passed=passed,
            score=1.0 - risk_score,
            framework=ComplianceFramework.SOX,
            risk_score=risk_score,
            violations=violations,
            certification_ready=passed,
            details={
                "internal_controls_compliant": len(internal_controls_violations) == 0,
                "data_integrity_compliant": len(data_integrity_violations) == 0,
                "audit_trail_compliant": len(audit_trail_violations) == 0,
                "total_records_checked": len(records),
                "validation_timestamp": datetime.now().isoformat()
            },
            recommendations=recommendations
        )
    
    def _check_internal_controls(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check SOX internal controls requirements."""
        violations = []
        
        required_controls = ["created_by", "approved_by", "version", "audit_trail_id"]
        
        for i, record in enumerate(records):
            missing_controls = [ctrl for ctrl in required_controls if ctrl not in record]
            
            if missing_controls:
                violations.append({
                    "type": "sox_internal_controls_violation",
                    "record_index": i,
                    "missing_controls": missing_controls,
                    "severity": "high",
                    "description": f"Missing internal controls: {missing_controls}",
                    "remediation": "Add required internal control fields"
                })
        
        return violations
    
    def _check_data_integrity(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check SOX data integrity requirements."""
        violations = []
        
        for i, record in enumerate(records):
            # Check for data consistency
            if "amount" in record and record["amount"] is None:
                violations.append({
                    "type": "sox_data_integrity_violation",
                    "record_index": i,
                    "field": "amount",
                    "severity": "medium",
                    "description": "Financial amounts cannot be null",
                    "remediation": "Ensure all financial fields have valid values"
                })
            
            # Check for proper data types in financial fields
            financial_fields = ["amount", "balance", "cost", "revenue"]
            
            for field in financial_fields:
                if field in record and record[field] is not None:
                    try:
                        float(record[field])
                    except (ValueError, TypeError):
                        violations.append({
                            "type": "sox_data_integrity_violation",
                            "record_index": i,
                            "field": field,
                            "severity": "high",
                            "description": f"Invalid numeric format in {field}",
                            "remediation": "Ensure financial fields contain valid numeric data"
                        })
        
        return violations
    
    def _check_audit_trail(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check SOX audit trail requirements."""
        violations = []
        
        audit_fields = ["created_at", "updated_at", "audit_trail_id"]
        
        for i, record in enumerate(records):
            missing_audit_fields = [field for field in audit_fields if field not in record or not record[field]]
            
            if missing_audit_fields:
                violations.append({
                    "type": "sox_audit_trail_violation",
                    "record_index": i,
                    "missing_fields": missing_audit_fields,
                    "severity": "high",
                    "description": f"Missing audit trail fields: {missing_audit_fields}",
                    "remediation": "Add complete audit trail documentation"
                })
        
        return violations
    
    def _generate_sox_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate SOX compliance recommendations."""
        recommendations = []
        
        violation_types = set(v["type"] for v in violations)
        
        if "sox_internal_controls_violation" in violation_types:
            recommendations.append("Implement comprehensive internal controls framework")
            recommendations.append("Add user authentication and authorization tracking")
            recommendations.append("Establish approval workflows for financial data")
        
        if "sox_data_integrity_violation" in violation_types:
            recommendations.append("Implement data validation at input and processing stages")
            recommendations.append("Add data type validation for all financial fields")
            recommendations.append("Establish data quality monitoring")
        
        if "sox_audit_trail_violation" in violation_types:
            recommendations.append("Implement comprehensive audit logging")
            recommendations.append("Add timestamps and user tracking for all changes")
            recommendations.append("Establish audit trail retention policies")
        
        if not violations:
            recommendations.append("Dataset meets SOX compliance requirements")
            recommendations.append("Continue monitoring for ongoing compliance")
            recommendations.append("Regular audit trail review recommended")
        
        return recommendations


class PCIDSSValidator:
    """PCI DSS compliance validator for payment card data."""
    
    def validate_dataset(self, records: List[Dict[str, Any]]) -> ComplianceResult:
        """Validate dataset for PCI DSS compliance."""
        
        violations = []
        risk_score = 0.0
        
        cardholder_violations = self._check_cardholder_data(records)
        encryption_violations = self._check_encryption_requirements(records)
        
        violations.extend(cardholder_violations)
        violations.extend(encryption_violations)
        
        # PCI DSS is pass/fail - any cardholder data exposure is critical
        passed = len(cardholder_violations) == 0
        risk_score = 1.0 if len(cardholder_violations) > 0 else 0.0
        
        recommendations = self._generate_pci_recommendations(violations)
        
        return ComplianceResult(
            passed=passed,
            score=1.0 - risk_score,
            framework=ComplianceFramework.PCI_DSS,
            risk_score=risk_score,
            violations=violations,
            certification_ready=passed,
            details={
                "cardholder_data_protected": len(cardholder_violations) == 0,
                "encryption_compliant": len(encryption_violations) == 0,
                "total_records_checked": len(records),
                "validation_timestamp": datetime.now().isoformat()
            },
            recommendations=recommendations
        )
    
    def _check_cardholder_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for exposed cardholder data."""
        violations = []
        
        # PAN (Primary Account Number) patterns
        pan_pattern = r"\b(?:\d[ -]*?){13,19}\b"
        
        # CVV patterns
        cvv_pattern = r"\b\d{3,4}\b"
        
        # Track data patterns
        track_pattern = r"%[A-Z]?\d{1,19}\^[^\^]*\^\d{4}"
        
        for i, record in enumerate(records):
            record_str = str(record)
            
            # Check for PAN
            if re.search(pan_pattern, record_str):
                violations.append({
                    "type": "pci_pan_exposure",
                    "record_index": i,
                    "severity": "critical",
                    "description": "Primary Account Number detected",
                    "remediation": "Remove or mask PAN - show only first 6 and last 4 digits"
                })
            
            # Check for CVV
            cvv_fields = ["cvv", "cvc", "security_code", "verification_code"]
            for field in cvv_fields:
                if field in record and record[field]:
                    violations.append({
                        "type": "pci_cvv_exposure",
                        "record_index": i,
                        "field": field,
                        "severity": "critical",
                        "description": "CVV/CVC code detected",
                        "remediation": "Remove CVV/CVC codes - never store after authorization"
                    })
            
            # Check for track data
            if re.search(track_pattern, record_str):
                violations.append({
                    "type": "pci_track_data_exposure",
                    "record_index": i,
                    "severity": "critical",
                    "description": "Magnetic stripe track data detected",
                    "remediation": "Remove track data - never store full track data"
                })
        
        return violations
    
    def _check_encryption_requirements(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check encryption and protection requirements."""
        violations = []
        
        # Look for indicators that data should be encrypted but isn't
        sensitive_fields = ["card_number", "account_number", "pan"]
        
        for i, record in enumerate(records):
            for field in sensitive_fields:
                if field in record and record[field]:
                    # Check if field appears to be encrypted (basic check)
                    value = str(record[field])
                    
                    # If it looks like plain card data
                    if re.match(r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}", value):
                        violations.append({
                            "type": "pci_encryption_violation",
                            "record_index": i,
                            "field": field,
                            "severity": "high",
                            "description": f"Unencrypted sensitive data in {field}",
                            "remediation": "Encrypt sensitive data or use tokenization"
                        })
        
        return violations
    
    def _generate_pci_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate PCI DSS compliance recommendations."""
        recommendations = []
        
        violation_types = set(v["type"] for v in violations)
        
        if "pci_pan_exposure" in violation_types:
            recommendations.append("Mask PAN - display only first 6 and last 4 digits")
            recommendations.append("Implement strong cryptography for stored PAN")
            recommendations.append("Use tokenization to replace PAN in datasets")
        
        if "pci_cvv_exposure" in violation_types:
            recommendations.append("Remove all CVV/CVC codes from stored data")
            recommendations.append("Never store CVV after transaction authorization")
        
        if "pci_track_data_exposure" in violation_types:
            recommendations.append("Remove all magnetic stripe track data")
            recommendations.append("Extract only necessary data elements from track data")
        
        if "pci_encryption_violation" in violation_types:
            recommendations.append("Implement strong encryption for all cardholder data")
            recommendations.append("Use industry-accepted algorithms (AES, RSA, etc.)")
            recommendations.append("Implement proper key management")
        
        if not violations:
            recommendations.append("Dataset meets PCI DSS requirements")
            recommendations.append("Maintain secure handling of synthetic payment data")
            recommendations.append("Regular security assessments recommended")
        
        return recommendations


class ComplianceValidator:
    """Main compliance validation orchestrator."""
    
    def __init__(self):
        """Initialize compliance validators."""
        self.validators = {
            ComplianceFramework.HIPAA: HIPAAValidator(),
            ComplianceFramework.SOX: SOXValidator(),
            ComplianceFramework.PCI_DSS: PCIDSSValidator()
        }
        
        logger.info("Compliance Validator initialized with all frameworks")
    
    async def validate_dataset(
        self,
        dataset: List[Dict[str, Any]],
        frameworks: List[ComplianceFramework],
        domain: DataDomain,
        risk_threshold: float = 0.01
    ) -> Dict[str, ComplianceResult]:
        """
        Validate dataset against specified compliance frameworks.
        
        Args:
            dataset: Dataset to validate
            frameworks: Compliance frameworks to validate against
            domain: Data domain for context
            risk_threshold: Acceptable risk threshold
            
        Returns:
            Dictionary of framework -> validation result
        """
        results = {}
        
        logger.info(f"Validating {len(dataset)} records against {len(frameworks)} frameworks")
        
        for framework in frameworks:
            if framework in self.validators:
                try:
                    result = self.validators[framework].validate_dataset(dataset)
                    results[framework] = result
                    
                    logger.info(
                        f"{framework} validation: {'PASSED' if result.passed else 'FAILED'} "
                        f"(Risk: {result.risk_score:.4f})"
                    )
                    
                except Exception as e:
                    logger.error(f"Error validating {framework}: {str(e)}")
                    results[framework] = ComplianceResult(
                        passed=False,
                        score=0.0,
                        framework=framework,
                        risk_score=1.0,
                        violations=[{
                            "type": "validation_error",
                            "description": f"Validation failed: {str(e)}",
                            "severity": "critical"
                        }],
                        certification_ready=False,
                        details={"error": str(e)},
                        recommendations=["Review validation configuration and dataset format"]
                    )
            else:
                logger.warning(f"No validator available for framework: {framework}")
                results[framework] = ComplianceResult(
                    passed=False,
                    score=0.0,
                    framework=framework,
                    risk_score=1.0,
                    violations=[{
                        "type": "unsupported_framework",
                        "description": f"Framework {framework} not supported",
                        "severity": "medium"
                    }],
                    certification_ready=False,
                    details={"error": "Framework not implemented"},
                    recommendations=[f"Implement validator for {framework}"]
                )
        
        return results
    
    def get_supported_frameworks(self, domain: DataDomain) -> List[ComplianceFramework]:
        """Get supported compliance frameworks for a domain."""
        
        if domain == DataDomain.HEALTHCARE:
            return [ComplianceFramework.HIPAA, ComplianceFramework.FDA, ComplianceFramework.GDPR]
        elif domain == DataDomain.FINANCE:
            return [ComplianceFramework.SOX, ComplianceFramework.PCI_DSS, ComplianceFramework.BASEL_III]
        else:
            return [ComplianceFramework.GDPR, ComplianceFramework.CCPA]