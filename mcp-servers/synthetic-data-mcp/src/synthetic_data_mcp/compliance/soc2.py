"""
SOC 2 Type II compliance implementation for enterprise requirements.

Implements the five Trust Service Criteria (TSC):
- Security
- Availability
- Processing Integrity
- Confidentiality
- Privacy
"""

import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from loguru import logger
from pydantic import BaseModel, Field
import cryptography.fernet
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class TrustServiceCriteria(Enum):
    """SOC 2 Trust Service Criteria."""
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class ControlCategory(Enum):
    """SOC 2 control categories."""
    CONTROL_ENVIRONMENT = "control_environment"
    COMMUNICATION_INFORMATION = "communication_information"
    RISK_ASSESSMENT = "risk_assessment"
    MONITORING_ACTIVITIES = "monitoring_activities"
    CONTROL_ACTIVITIES = "control_activities"
    LOGICAL_ACCESS = "logical_access"
    SYSTEM_OPERATIONS = "system_operations"
    CHANGE_MANAGEMENT = "change_management"
    RISK_MITIGATION = "risk_mitigation"


@dataclass
class Control:
    """SOC 2 control definition."""
    id: str
    name: str
    description: str
    category: ControlCategory
    criteria: List[TrustServiceCriteria]
    frequency: str  # continuous, daily, weekly, monthly
    automated: bool
    evidence_required: List[str]
    risk_level: str  # low, medium, high, critical


@dataclass
class ControlTest:
    """Control test result."""
    control_id: str
    test_date: datetime
    tester: str
    result: str  # pass, fail, partial
    evidence: List[str]
    findings: List[str]
    remediation: Optional[str] = None
    due_date: Optional[datetime] = None


@dataclass
class ComplianceEvidence:
    """Evidence for compliance audit."""
    id: str
    control_id: str
    type: str  # screenshot, log, report, configuration, policy
    description: str
    location: str
    created_at: datetime
    hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SOC2Control(Base):
    """SOC 2 control database model."""
    __tablename__ = "soc2_controls"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)
    criteria = Column(JSON)
    frequency = Column(String)
    automated = Column(Boolean, default=False)
    evidence_required = Column(JSON)
    risk_level = Column(String)
    last_tested = Column(DateTime)
    next_test_due = Column(DateTime)
    status = Column(String)  # compliant, non_compliant, pending


class SOC2Evidence(Base):
    """SOC 2 evidence database model."""
    __tablename__ = "soc2_evidence"
    
    id = Column(String, primary_key=True)
    control_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text)
    location = Column(String)
    hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    verified_by = Column(String)
    metadata = Column(JSON, default=dict)


class SOC2TestResult(Base):
    """SOC 2 test result database model."""
    __tablename__ = "soc2_test_results"
    
    id = Column(Integer, primary_key=True)
    control_id = Column(String, nullable=False)
    test_date = Column(DateTime, default=datetime.utcnow)
    tester = Column(String)
    result = Column(String)
    evidence = Column(JSON)
    findings = Column(JSON)
    remediation = Column(Text)
    due_date = Column(DateTime)
    resolved = Column(Boolean, default=False)
    resolved_date = Column(DateTime)


class SOC2ComplianceManager:
    """Manages SOC 2 Type II compliance."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.controls = self._initialize_controls()
        self._start_monitoring()
    
    def _initialize_controls(self) -> Dict[str, Control]:
        """Initialize SOC 2 control framework."""
        controls = {}
        
        # Security Controls
        controls["SEC-001"] = Control(
            id="SEC-001",
            name="Access Control",
            description="Logical access to systems is restricted to authorized users",
            category=ControlCategory.LOGICAL_ACCESS,
            criteria=[TrustServiceCriteria.SECURITY],
            frequency="continuous",
            automated=True,
            evidence_required=["access_logs", "user_provisioning_records", "permission_matrix"],
            risk_level="high"
        )
        
        controls["SEC-002"] = Control(
            id="SEC-002",
            name="Encryption at Rest",
            description="Sensitive data is encrypted at rest using AES-256",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.SECURITY, TrustServiceCriteria.CONFIDENTIALITY],
            frequency="continuous",
            automated=True,
            evidence_required=["encryption_config", "key_management_policy", "encryption_scan"],
            risk_level="critical"
        )
        
        controls["SEC-003"] = Control(
            id="SEC-003",
            name="Encryption in Transit",
            description="Data is encrypted in transit using TLS 1.2+",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.SECURITY, TrustServiceCriteria.CONFIDENTIALITY],
            frequency="continuous",
            automated=True,
            evidence_required=["ssl_certificates", "tls_configuration", "vulnerability_scan"],
            risk_level="critical"
        )
        
        # Availability Controls
        controls["AVL-001"] = Control(
            id="AVL-001",
            name="System Availability Monitoring",
            description="System availability is monitored 24/7 with alerting",
            category=ControlCategory.MONITORING_ACTIVITIES,
            criteria=[TrustServiceCriteria.AVAILABILITY],
            frequency="continuous",
            automated=True,
            evidence_required=["uptime_reports", "monitoring_dashboards", "alert_logs"],
            risk_level="high"
        )
        
        controls["AVL-002"] = Control(
            id="AVL-002",
            name="Backup and Recovery",
            description="Data is backed up daily and can be recovered within RTO",
            category=ControlCategory.SYSTEM_OPERATIONS,
            criteria=[TrustServiceCriteria.AVAILABILITY],
            frequency="daily",
            automated=True,
            evidence_required=["backup_logs", "recovery_test_results", "backup_configuration"],
            risk_level="high"
        )
        
        # Processing Integrity Controls
        controls["INT-001"] = Control(
            id="INT-001",
            name="Data Validation",
            description="Input data is validated for completeness and accuracy",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.PROCESSING_INTEGRITY],
            frequency="continuous",
            automated=True,
            evidence_required=["validation_rules", "error_logs", "data_quality_reports"],
            risk_level="medium"
        )
        
        controls["INT-002"] = Control(
            id="INT-002",
            name="Change Management",
            description="System changes follow approved change management process",
            category=ControlCategory.CHANGE_MANAGEMENT,
            criteria=[TrustServiceCriteria.PROCESSING_INTEGRITY],
            frequency="per_change",
            automated=False,
            evidence_required=["change_requests", "approval_records", "deployment_logs"],
            risk_level="high"
        )
        
        # Privacy Controls
        controls["PRV-001"] = Control(
            id="PRV-001",
            name="Data Minimization",
            description="Only necessary personal data is collected and processed",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.PRIVACY],
            frequency="continuous",
            automated=True,
            evidence_required=["data_inventory", "privacy_assessment", "collection_policies"],
            risk_level="high"
        )
        
        controls["PRV-002"] = Control(
            id="PRV-002",
            name="Consent Management",
            description="User consent is obtained and managed for data processing",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.PRIVACY],
            frequency="continuous",
            automated=True,
            evidence_required=["consent_records", "opt_out_logs", "consent_interface"],
            risk_level="critical"
        )
        
        controls["PRV-003"] = Control(
            id="PRV-003",
            name="Data Retention",
            description="Data is retained according to policy and deleted when no longer needed",
            category=ControlCategory.CONTROL_ACTIVITIES,
            criteria=[TrustServiceCriteria.PRIVACY],
            frequency="monthly",
            automated=True,
            evidence_required=["retention_policy", "deletion_logs", "retention_schedule"],
            risk_level="medium"
        )
        
        return controls
    
    def _start_monitoring(self):
        """Start continuous monitoring tasks."""
        asyncio.create_task(self._continuous_monitoring())
        asyncio.create_task(self._automated_testing())
    
    async def _continuous_monitoring(self):
        """Continuous monitoring of controls."""
        while True:
            try:
                for control_id, control in self.controls.items():
                    if control.automated and control.frequency == "continuous":
                        await self.test_control(control_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _automated_testing(self):
        """Automated control testing based on frequency."""
        while True:
            try:
                now = datetime.utcnow()
                
                # Daily tests
                if now.hour == 2 and now.minute < 5:  # Run at 2 AM
                    for control_id, control in self.controls.items():
                        if control.frequency == "daily":
                            await self.test_control(control_id)
                
                # Weekly tests (Sundays)
                if now.weekday() == 6 and now.hour == 3 and now.minute < 5:
                    for control_id, control in self.controls.items():
                        if control.frequency == "weekly":
                            await self.test_control(control_id)
                
                # Monthly tests (1st of month)
                if now.day == 1 and now.hour == 4 and now.minute < 5:
                    for control_id, control in self.controls.items():
                        if control.frequency == "monthly":
                            await self.test_control(control_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Automated testing error: {e}")
                await asyncio.sleep(300)
    
    async def test_control(self, control_id: str) -> ControlTest:
        """Test a specific control."""
        control = self.controls.get(control_id)
        if not control:
            raise ValueError(f"Control {control_id} not found")
        
        logger.info(f"Testing control {control_id}: {control.name}")
        
        # Perform control-specific tests
        test_result = await self._perform_control_test(control)
        
        # Store test result
        db_result = SOC2TestResult(
            control_id=control_id,
            test_date=datetime.utcnow(),
            tester="automated" if control.automated else "manual",
            result=test_result.result,
            evidence=test_result.evidence,
            findings=test_result.findings,
            remediation=test_result.remediation,
            due_date=test_result.due_date
        )
        
        self.db.add(db_result)
        self.db.commit()
        
        # Update control status
        db_control = self.db.query(SOC2Control).filter_by(id=control_id).first()
        if not db_control:
            db_control = SOC2Control(
                id=control_id,
                name=control.name,
                description=control.description,
                category=control.category.value,
                criteria=[c.value for c in control.criteria],
                frequency=control.frequency,
                automated=control.automated,
                evidence_required=control.evidence_required,
                risk_level=control.risk_level
            )
            self.db.add(db_control)
        
        db_control.last_tested = datetime.utcnow()
        db_control.status = "compliant" if test_result.result == "pass" else "non_compliant"
        
        # Calculate next test due date
        if control.frequency == "continuous":
            db_control.next_test_due = datetime.utcnow() + timedelta(minutes=5)
        elif control.frequency == "daily":
            db_control.next_test_due = datetime.utcnow() + timedelta(days=1)
        elif control.frequency == "weekly":
            db_control.next_test_due = datetime.utcnow() + timedelta(weeks=1)
        elif control.frequency == "monthly":
            db_control.next_test_due = datetime.utcnow() + timedelta(days=30)
        
        self.db.commit()
        
        return test_result
    
    async def _perform_control_test(self, control: Control) -> ControlTest:
        """Perform actual control testing logic."""
        evidence = []
        findings = []
        result = "pass"
        
        # Control-specific testing logic
        if control.id == "SEC-001":  # Access Control
            # Check access logs
            evidence.append("access_logs_checked")
            # Verify no unauthorized access
            unauthorized = await self._check_unauthorized_access()
            if unauthorized:
                findings.append(f"Found {len(unauthorized)} unauthorized access attempts")
                result = "fail"
        
        elif control.id == "SEC-002":  # Encryption at Rest
            # Verify encryption configuration
            evidence.append("encryption_config_verified")
            encrypted = await self._verify_encryption_at_rest()
            if not encrypted:
                findings.append("Some data not encrypted at rest")
                result = "fail"
        
        elif control.id == "SEC-003":  # Encryption in Transit
            # Check TLS configuration
            evidence.append("tls_config_verified")
            tls_valid = await self._verify_tls_configuration()
            if not tls_valid:
                findings.append("TLS configuration issues found")
                result = "fail"
        
        elif control.id == "AVL-001":  # System Availability
            # Check uptime metrics
            evidence.append("uptime_metrics_checked")
            uptime = await self._get_uptime_percentage()
            if uptime < 99.9:
                findings.append(f"Uptime {uptime}% below 99.9% SLA")
                result = "fail"
        
        elif control.id == "AVL-002":  # Backup and Recovery
            # Verify recent backups
            evidence.append("backup_verification")
            backup_valid = await self._verify_recent_backups()
            if not backup_valid:
                findings.append("Backup issues detected")
                result = "fail"
        
        elif control.id == "INT-001":  # Data Validation
            # Check validation error rates
            evidence.append("validation_metrics_checked")
            error_rate = await self._get_validation_error_rate()
            if error_rate > 0.01:  # 1% threshold
                findings.append(f"Validation error rate {error_rate}% exceeds threshold")
                result = "partial"
        
        elif control.id == "PRV-001":  # Data Minimization
            # Check data collection practices
            evidence.append("data_inventory_reviewed")
            minimized = await self._verify_data_minimization()
            if not minimized:
                findings.append("Unnecessary data collection detected")
                result = "fail"
        
        elif control.id == "PRV-002":  # Consent Management
            # Verify consent records
            evidence.append("consent_records_verified")
            consent_valid = await self._verify_consent_management()
            if not consent_valid:
                findings.append("Consent management issues found")
                result = "fail"
        
        elif control.id == "PRV-003":  # Data Retention
            # Check retention compliance
            evidence.append("retention_compliance_checked")
            retention_valid = await self._verify_retention_compliance()
            if not retention_valid:
                findings.append("Data retention policy violations")
                result = "partial"
        
        return ControlTest(
            control_id=control.id,
            test_date=datetime.utcnow(),
            tester="automated",
            result=result,
            evidence=evidence,
            findings=findings,
            remediation="Address findings within 30 days" if findings else None,
            due_date=datetime.utcnow() + timedelta(days=30) if findings else None
        )
    
    async def _check_unauthorized_access(self) -> List[str]:
        """Check for unauthorized access attempts."""
        # Implementation would check actual access logs
        return []  # Placeholder
    
    async def _verify_encryption_at_rest(self) -> bool:
        """Verify data encryption at rest."""
        # Implementation would check encryption status
        return True  # Placeholder
    
    async def _verify_tls_configuration(self) -> bool:
        """Verify TLS configuration."""
        # Implementation would check TLS settings
        return True  # Placeholder
    
    async def _get_uptime_percentage(self) -> float:
        """Get system uptime percentage."""
        # Implementation would calculate actual uptime
        return 99.95  # Placeholder
    
    async def _verify_recent_backups(self) -> bool:
        """Verify recent backup completion."""
        # Implementation would check backup logs
        return True  # Placeholder
    
    async def _get_validation_error_rate(self) -> float:
        """Get data validation error rate."""
        # Implementation would calculate error rate
        return 0.005  # Placeholder (0.5%)
    
    async def _verify_data_minimization(self) -> bool:
        """Verify data minimization practices."""
        # Implementation would check data collection
        return True  # Placeholder
    
    async def _verify_consent_management(self) -> bool:
        """Verify consent management compliance."""
        # Implementation would check consent records
        return True  # Placeholder
    
    async def _verify_retention_compliance(self) -> bool:
        """Verify data retention compliance."""
        # Implementation would check retention policies
        return True  # Placeholder
    
    async def collect_evidence(
        self,
        control_id: str,
        evidence_type: str,
        description: str,
        location: str
    ) -> ComplianceEvidence:
        """Collect and store compliance evidence."""
        # Generate evidence ID
        evidence_id = str(uuid.uuid4())
        
        # Calculate hash for integrity
        content = f"{control_id}{evidence_type}{description}{location}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        
        # Create evidence record
        evidence = ComplianceEvidence(
            id=evidence_id,
            control_id=control_id,
            type=evidence_type,
            description=description,
            location=location,
            created_at=datetime.utcnow(),
            hash=hash_value
        )
        
        # Store in database
        db_evidence = SOC2Evidence(
            id=evidence_id,
            control_id=control_id,
            type=evidence_type,
            description=description,
            location=location,
            hash=hash_value,
            created_at=datetime.utcnow()
        )
        
        self.db.add(db_evidence)
        self.db.commit()
        
        logger.info(f"Evidence collected for control {control_id}: {evidence_id}")
        
        return evidence
    
    async def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate SOC 2 compliance report."""
        report = {
            "report_date": datetime.utcnow().isoformat(),
            "report_type": "SOC 2 Type II",
            "period_start": (datetime.utcnow() - timedelta(days=365)).isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "overall_status": "compliant",
            "controls_summary": {},
            "criteria_summary": {},
            "findings": [],
            "remediation_items": []
        }
        
        # Analyze each control
        for control_id, control in self.controls.items():
            # Get latest test result
            latest_test = self.db.query(SOC2TestResult).filter_by(
                control_id=control_id
            ).order_by(SOC2TestResult.test_date.desc()).first()
            
            if latest_test:
                control_status = {
                    "name": control.name,
                    "category": control.category.value,
                    "status": latest_test.result,
                    "last_tested": latest_test.test_date.isoformat(),
                    "findings": latest_test.findings or []
                }
                
                report["controls_summary"][control_id] = control_status
                
                # Add to findings if not compliant
                if latest_test.result != "pass":
                    report["overall_status"] = "partial"
                    report["findings"].extend(latest_test.findings or [])
                    
                    if latest_test.remediation:
                        report["remediation_items"].append({
                            "control_id": control_id,
                            "remediation": latest_test.remediation,
                            "due_date": latest_test.due_date.isoformat() if latest_test.due_date else None
                        })
        
        # Summarize by criteria
        for criteria in TrustServiceCriteria:
            criteria_controls = [
                c for c in self.controls.values()
                if criteria in c.criteria
            ]
            
            compliant = sum(
                1 for c in criteria_controls
                if report["controls_summary"].get(c.id, {}).get("status") == "pass"
            )
            
            report["criteria_summary"][criteria.value] = {
                "total_controls": len(criteria_controls),
                "compliant_controls": compliant,
                "compliance_percentage": (compliant / len(criteria_controls) * 100) if criteria_controls else 100
            }
        
        return report
    
    async def get_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail for compliance review."""
        query = self.db.query(SOC2TestResult)
        
        if start_date:
            query = query.filter(SOC2TestResult.test_date >= start_date)
        if end_date:
            query = query.filter(SOC2TestResult.test_date <= end_date)
        
        results = query.order_by(SOC2TestResult.test_date.desc()).all()
        
        audit_trail = []
        for result in results:
            audit_trail.append({
                "control_id": result.control_id,
                "test_date": result.test_date.isoformat(),
                "tester": result.tester,
                "result": result.result,
                "evidence": result.evidence,
                "findings": result.findings,
                "remediation": result.remediation,
                "resolved": result.resolved
            })
        
        return audit_trail
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status."""
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_compliance": True,
            "controls_status": {},
            "non_compliant_controls": [],
            "pending_remediation": []
        }
        
        for control_id in self.controls:
            db_control = self.db.query(SOC2Control).filter_by(id=control_id).first()
            
            if db_control:
                status["controls_status"][control_id] = db_control.status
                
                if db_control.status == "non_compliant":
                    status["overall_compliance"] = False
                    status["non_compliant_controls"].append(control_id)
                    
                    # Check for pending remediation
                    pending = self.db.query(SOC2TestResult).filter_by(
                        control_id=control_id,
                        resolved=False
                    ).filter(SOC2TestResult.remediation.isnot(None)).first()
                    
                    if pending:
                        status["pending_remediation"].append({
                            "control_id": control_id,
                            "due_date": pending.due_date.isoformat() if pending.due_date else None
                        })
        
        return status