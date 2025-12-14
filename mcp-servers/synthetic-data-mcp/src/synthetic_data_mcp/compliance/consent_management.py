"""
Consent management system for GDPR and privacy compliance.

Implements comprehensive consent collection, tracking, and management
for data processing activities in accordance with GDPR Articles 6 & 7.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import asyncio

from loguru import logger
from pydantic import BaseModel, EmailStr, Field as PydanticField
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, JSON, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import jwt

Base = declarative_base()


class ConsentPurpose(Enum):
    """GDPR-compliant consent purposes."""
    DATA_GENERATION = "data_generation"
    DATA_PROCESSING = "data_processing"
    DATA_SHARING = "data_sharing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    RESEARCH = "research"
    PROFILING = "profiling"
    AUTOMATED_DECISION = "automated_decision"
    CROSS_BORDER_TRANSFER = "cross_border_transfer"
    SENSITIVE_DATA = "sensitive_data"


class LegalBasis(Enum):
    """GDPR Article 6 legal basis for processing."""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class ConsentStatus(Enum):
    """Consent status states."""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class DataSubjectRight(Enum):
    """GDPR data subject rights."""
    ACCESS = "access"  # Article 15
    RECTIFICATION = "rectification"  # Article 16
    ERASURE = "erasure"  # Article 17 - Right to be forgotten
    RESTRICTION = "restriction"  # Article 18
    PORTABILITY = "portability"  # Article 20
    OBJECTION = "objection"  # Article 21
    AUTOMATED_DECISION = "automated_decision"  # Article 22


@dataclass
class ConsentRecord:
    """Individual consent record."""
    consent_id: str
    data_subject_id: str
    purpose: ConsentPurpose
    status: ConsentStatus
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    expires_at: Optional[datetime]
    version: str
    language: str
    collection_method: str  # web_form, api, paper, verbal
    ip_address: Optional[str]
    user_agent: Optional[str]
    parent_consent: Optional[str]  # For minors
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsentTemplate:
    """Consent request template."""
    template_id: str
    purpose: ConsentPurpose
    title: str
    description: str
    data_categories: List[str]
    retention_period: str
    third_parties: List[str]
    international_transfers: List[str]
    automated_processing: bool
    version: str
    created_at: datetime
    languages: List[str]
    child_appropriate: bool = False


@dataclass
class DataSubjectRequest:
    """Data subject request under GDPR."""
    request_id: str
    data_subject_id: str
    right: DataSubjectRight
    status: str  # pending, in_progress, completed, denied
    requested_at: datetime
    completed_at: Optional[datetime]
    response_deadline: datetime  # GDPR requires response within 30 days
    details: Dict[str, Any]
    verification_status: str
    handler: Optional[str]


class ConsentRecordDB(Base):
    """Consent record database model."""
    __tablename__ = "consent_records"
    
    consent_id = Column(String, primary_key=True)
    data_subject_id = Column(String, nullable=False, index=True)
    purpose = Column(String, nullable=False)
    status = Column(String, nullable=False)
    legal_basis = Column(String)
    granted_at = Column(DateTime)
    withdrawn_at = Column(DateTime)
    expires_at = Column(DateTime)
    version = Column(String)
    language = Column(String)
    collection_method = Column(String)
    ip_address = Column(String)
    user_agent = Column(Text)
    parent_consent = Column(String)
    consent_text = Column(Text)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsentAuditLog(Base):
    """Consent audit trail."""
    __tablename__ = "consent_audit_log"
    
    id = Column(Integer, primary_key=True)
    consent_id = Column(String, nullable=False, index=True)
    data_subject_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # granted, withdrawn, expired, modified
    timestamp = Column(DateTime, default=datetime.utcnow)
    old_value = Column(JSON)
    new_value = Column(JSON)
    reason = Column(Text)
    performed_by = Column(String)
    ip_address = Column(String)
    metadata = Column(JSON, default=dict)


class DataSubjectRequestDB(Base):
    """Data subject request database model."""
    __tablename__ = "data_subject_requests"
    
    request_id = Column(String, primary_key=True)
    data_subject_id = Column(String, nullable=False, index=True)
    right = Column(String, nullable=False)
    status = Column(String, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    response_deadline = Column(DateTime)
    details = Column(JSON, default=dict)
    verification_status = Column(String)
    handler = Column(String)
    response = Column(JSON)
    metadata = Column(JSON, default=dict)


class ConsentPreference(Base):
    """User consent preferences."""
    __tablename__ = "consent_preferences"
    
    id = Column(Integer, primary_key=True)
    data_subject_id = Column(String, nullable=False, unique=True, index=True)
    global_consent = Column(Boolean, default=False)
    purpose_consents = Column(JSON, default=dict)  # {purpose: bool}
    communication_channels = Column(JSON, default=dict)  # {email: bool, sms: bool, etc}
    language_preference = Column(String, default="en")
    minor_status = Column(Boolean, default=False)
    guardian_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsentManager:
    """Manages GDPR-compliant consent collection and tracking."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.templates: Dict[str, ConsentTemplate] = {}
        self._initialize_templates()
        self._start_monitoring()
    
    def _initialize_templates(self):
        """Initialize consent templates."""
        # Data generation consent
        self.templates["data_generation"] = ConsentTemplate(
            template_id="TMPL-001",
            purpose=ConsentPurpose.DATA_GENERATION,
            title="Synthetic Data Generation Consent",
            description="We would like to generate synthetic data based on patterns from your data",
            data_categories=["personal_data", "usage_patterns", "preferences"],
            retention_period="90 days",
            third_parties=[],
            international_transfers=[],
            automated_processing=True,
            version="1.0",
            created_at=datetime.utcnow(),
            languages=["en", "de", "fr", "es"],
            child_appropriate=False
        )
        
        # Marketing consent
        self.templates["marketing"] = ConsentTemplate(
            template_id="TMPL-002",
            purpose=ConsentPurpose.MARKETING,
            title="Marketing Communications",
            description="Receive updates about our products and services",
            data_categories=["contact_information", "preferences"],
            retention_period="Until withdrawn",
            third_parties=["Marketing partners"],
            international_transfers=[],
            automated_processing=False,
            version="1.0",
            created_at=datetime.utcnow(),
            languages=["en"],
            child_appropriate=False
        )
        
        # Research consent
        self.templates["research"] = ConsentTemplate(
            template_id="TMPL-003",
            purpose=ConsentPurpose.RESEARCH,
            title="Research Participation",
            description="Use your data for research and improvement",
            data_categories=["usage_data", "feedback", "patterns"],
            retention_period="3 years",
            third_parties=["Research institutions"],
            international_transfers=["USA", "UK"],
            automated_processing=True,
            version="1.0",
            created_at=datetime.utcnow(),
            languages=["en"],
            child_appropriate=False
        )
    
    def _start_monitoring(self):
        """Start consent monitoring tasks."""
        asyncio.create_task(self._monitor_expiry())
        asyncio.create_task(self._monitor_requests())
    
    async def _monitor_expiry(self):
        """Monitor and handle consent expiry."""
        while True:
            try:
                # Check for expired consents
                expired = self.db.query(ConsentRecordDB).filter(
                    ConsentRecordDB.expires_at <= datetime.utcnow(),
                    ConsentRecordDB.status == "granted"
                ).all()
                
                for consent in expired:
                    consent.status = "expired"
                    self._audit_log(
                        consent_id=consent.consent_id,
                        data_subject_id=consent.data_subject_id,
                        action="expired",
                        old_value={"status": "granted"},
                        new_value={"status": "expired"}
                    )
                
                self.db.commit()
                
                if expired:
                    logger.info(f"Expired {len(expired)} consent records")
                
                await asyncio.sleep(3600)  # Check hourly
                
            except Exception as e:
                logger.error(f"Consent expiry monitoring error: {e}")
                await asyncio.sleep(3600)
    
    async def _monitor_requests(self):
        """Monitor data subject requests for deadline compliance."""
        while True:
            try:
                # Check for overdue requests
                overdue = self.db.query(DataSubjectRequestDB).filter(
                    DataSubjectRequestDB.response_deadline <= datetime.utcnow(),
                    DataSubjectRequestDB.status.in_(["pending", "in_progress"])
                ).all()
                
                for request in overdue:
                    logger.warning(f"Overdue data subject request: {request.request_id}")
                    # In production, would send alerts
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error(f"Request monitoring error: {e}")
                await asyncio.sleep(86400)
    
    async def collect_consent(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose,
        language: str = "en",
        collection_method: str = "web_form",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        parent_consent_id: Optional[str] = None
    ) -> ConsentRecord:
        """Collect consent from data subject."""
        consent_id = f"CONSENT-{uuid.uuid4().hex[:12].upper()}"
        
        # Get template
        template = self.templates.get(purpose.value)
        if not template:
            raise ValueError(f"No template for purpose: {purpose}")
        
        # Check if minor requires parent consent
        if await self._is_minor(data_subject_id) and not parent_consent_id:
            raise ValueError("Parent consent required for minors")
        
        # Create consent record
        consent = ConsentRecord(
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            purpose=purpose,
            status=ConsentStatus.PENDING,
            granted_at=None,
            withdrawn_at=None,
            expires_at=datetime.utcnow() + timedelta(days=365),  # 1 year default
            version=template.version,
            language=language,
            collection_method=collection_method,
            ip_address=ip_address,
            user_agent=user_agent,
            parent_consent=parent_consent_id
        )
        
        # Store in database
        db_consent = ConsentRecordDB(
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            purpose=purpose.value,
            status=ConsentStatus.PENDING.value,
            legal_basis=LegalBasis.CONSENT.value,
            expires_at=consent.expires_at,
            version=template.version,
            language=language,
            collection_method=collection_method,
            ip_address=ip_address,
            user_agent=user_agent,
            parent_consent=parent_consent_id,
            consent_text=template.description
        )
        
        self.db.add(db_consent)
        self.db.commit()
        
        # Audit log
        self._audit_log(
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            action="created",
            new_value={"status": "pending", "purpose": purpose.value}
        )
        
        logger.info(f"Collected consent request {consent_id} for {data_subject_id}")
        
        return consent
    
    async def grant_consent(
        self,
        consent_id: str,
        granted_by: Optional[str] = None
    ) -> bool:
        """Grant consent."""
        consent = self.db.query(ConsentRecordDB).filter_by(consent_id=consent_id).first()
        
        if not consent:
            raise ValueError(f"Consent {consent_id} not found")
        
        if consent.status != "pending":
            raise ValueError(f"Consent {consent_id} is not pending")
        
        old_status = consent.status
        consent.status = ConsentStatus.GRANTED.value
        consent.granted_at = datetime.utcnow()
        
        self.db.commit()
        
        # Update preferences
        await self._update_preferences(
            consent.data_subject_id,
            ConsentPurpose(consent.purpose),
            True
        )
        
        # Audit log
        self._audit_log(
            consent_id=consent_id,
            data_subject_id=consent.data_subject_id,
            action="granted",
            old_value={"status": old_status},
            new_value={"status": "granted"},
            performed_by=granted_by
        )
        
        logger.info(f"Granted consent {consent_id}")
        
        return True
    
    async def withdraw_consent(
        self,
        consent_id: str,
        reason: Optional[str] = None,
        withdrawn_by: Optional[str] = None
    ) -> bool:
        """Withdraw consent (GDPR Article 7.3)."""
        consent = self.db.query(ConsentRecordDB).filter_by(consent_id=consent_id).first()
        
        if not consent:
            raise ValueError(f"Consent {consent_id} not found")
        
        if consent.status != "granted":
            raise ValueError(f"Consent {consent_id} is not granted")
        
        old_status = consent.status
        consent.status = ConsentStatus.WITHDRAWN.value
        consent.withdrawn_at = datetime.utcnow()
        
        self.db.commit()
        
        # Update preferences
        await self._update_preferences(
            consent.data_subject_id,
            ConsentPurpose(consent.purpose),
            False
        )
        
        # Audit log
        self._audit_log(
            consent_id=consent_id,
            data_subject_id=consent.data_subject_id,
            action="withdrawn",
            old_value={"status": old_status},
            new_value={"status": "withdrawn"},
            reason=reason,
            performed_by=withdrawn_by
        )
        
        logger.info(f"Withdrawn consent {consent_id}")
        
        # Trigger data processing cessation
        await self._cease_processing(consent.data_subject_id, ConsentPurpose(consent.purpose))
        
        return True
    
    async def _cease_processing(self, data_subject_id: str, purpose: ConsentPurpose):
        """Cease data processing for withdrawn consent."""
        # In production, would trigger actual data processing cessation
        logger.info(f"Ceasing {purpose.value} processing for {data_subject_id}")
    
    async def check_consent(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose
    ) -> Tuple[bool, Optional[ConsentRecord]]:
        """Check if valid consent exists."""
        consent = self.db.query(ConsentRecordDB).filter(
            ConsentRecordDB.data_subject_id == data_subject_id,
            ConsentRecordDB.purpose == purpose.value,
            ConsentRecordDB.status == ConsentStatus.GRANTED.value
        ).first()
        
        if not consent:
            return False, None
        
        # Check expiry
        if consent.expires_at and consent.expires_at < datetime.utcnow():
            return False, None
        
        record = ConsentRecord(
            consent_id=consent.consent_id,
            data_subject_id=consent.data_subject_id,
            purpose=ConsentPurpose(consent.purpose),
            status=ConsentStatus(consent.status),
            granted_at=consent.granted_at,
            withdrawn_at=consent.withdrawn_at,
            expires_at=consent.expires_at,
            version=consent.version,
            language=consent.language,
            collection_method=consent.collection_method,
            ip_address=consent.ip_address,
            user_agent=consent.user_agent,
            parent_consent=consent.parent_consent,
            metadata=consent.metadata or {}
        )
        
        return True, record
    
    async def create_data_subject_request(
        self,
        data_subject_id: str,
        right: DataSubjectRight,
        details: Dict[str, Any]
    ) -> DataSubjectRequest:
        """Create a data subject request (GDPR Chapter III)."""
        request_id = f"DSR-{uuid.uuid4().hex[:12].upper()}"
        
        # GDPR requires response within 30 days
        response_deadline = datetime.utcnow() + timedelta(days=30)
        
        request = DataSubjectRequest(
            request_id=request_id,
            data_subject_id=data_subject_id,
            right=right,
            status="pending",
            requested_at=datetime.utcnow(),
            completed_at=None,
            response_deadline=response_deadline,
            details=details,
            verification_status="pending",
            handler=None
        )
        
        # Store in database
        db_request = DataSubjectRequestDB(
            request_id=request_id,
            data_subject_id=data_subject_id,
            right=right.value,
            status="pending",
            requested_at=request.requested_at,
            response_deadline=response_deadline,
            details=details,
            verification_status="pending"
        )
        
        self.db.add(db_request)
        self.db.commit()
        
        logger.info(f"Created data subject request {request_id} for {right.value}")
        
        # Process request based on type
        asyncio.create_task(self._process_data_subject_request(request))
        
        return request
    
    async def _process_data_subject_request(self, request: DataSubjectRequest):
        """Process a data subject request."""
        try:
            if request.right == DataSubjectRight.ACCESS:
                await self._handle_access_request(request)
            elif request.right == DataSubjectRight.ERASURE:
                await self._handle_erasure_request(request)
            elif request.right == DataSubjectRight.PORTABILITY:
                await self._handle_portability_request(request)
            elif request.right == DataSubjectRight.RECTIFICATION:
                await self._handle_rectification_request(request)
            elif request.right == DataSubjectRight.RESTRICTION:
                await self._handle_restriction_request(request)
            elif request.right == DataSubjectRight.OBJECTION:
                await self._handle_objection_request(request)
            
        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            
            db_request = self.db.query(DataSubjectRequestDB).filter_by(
                request_id=request.request_id
            ).first()
            
            if db_request:
                db_request.status = "failed"
                db_request.response = {"error": str(e)}
                self.db.commit()
    
    async def _handle_access_request(self, request: DataSubjectRequest):
        """Handle data access request (GDPR Article 15)."""
        # Gather all data about the subject
        data = {
            "consents": [],
            "processing_purposes": [],
            "data_categories": [],
            "recipients": [],
            "retention_periods": {},
            "rights": list(DataSubjectRight),
            "automated_decisions": []
        }
        
        # Get consent records
        consents = self.db.query(ConsentRecordDB).filter_by(
            data_subject_id=request.data_subject_id
        ).all()
        
        for consent in consents:
            data["consents"].append({
                "purpose": consent.purpose,
                "status": consent.status,
                "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
                "expires_at": consent.expires_at.isoformat() if consent.expires_at else None
            })
            
            if consent.status == "granted":
                data["processing_purposes"].append(consent.purpose)
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = data
        
        self.db.commit()
        
        logger.info(f"Completed access request {request.request_id}")
    
    async def _handle_erasure_request(self, request: DataSubjectRequest):
        """Handle erasure request - Right to be forgotten (GDPR Article 17)."""
        # Check if erasure is allowed
        can_erase, reason = await self._can_erase(request.data_subject_id)
        
        if not can_erase:
            db_request = self.db.query(DataSubjectRequestDB).filter_by(
                request_id=request.request_id
            ).first()
            
            db_request.status = "denied"
            db_request.response = {"reason": reason}
            self.db.commit()
            
            return
        
        # Perform erasure
        # 1. Withdraw all consents
        consents = self.db.query(ConsentRecordDB).filter_by(
            data_subject_id=request.data_subject_id
        ).all()
        
        for consent in consents:
            if consent.status == "granted":
                consent.status = "withdrawn"
                consent.withdrawn_at = datetime.utcnow()
        
        # 2. Mark for deletion (in production, would trigger actual deletion)
        deletion_record = {
            "data_subject_id": request.data_subject_id,
            "deletion_requested": datetime.utcnow().isoformat(),
            "deletion_scheduled": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = deletion_record
        
        self.db.commit()
        
        logger.info(f"Completed erasure request {request.request_id}")
    
    async def _can_erase(self, data_subject_id: str) -> Tuple[bool, Optional[str]]:
        """Check if data can be erased."""
        # Check for legal obligations that prevent erasure
        # In production, would check actual legal requirements
        
        # Example checks:
        # - Active contracts
        # - Legal retention requirements
        # - Ongoing investigations
        
        return True, None
    
    async def _handle_portability_request(self, request: DataSubjectRequest):
        """Handle data portability request (GDPR Article 20)."""
        # Gather portable data
        portable_data = {
            "data_subject_id": request.data_subject_id,
            "export_date": datetime.utcnow().isoformat(),
            "consents": [],
            "preferences": {},
            "provided_data": {}
        }
        
        # Get consents
        consents = self.db.query(ConsentRecordDB).filter_by(
            data_subject_id=request.data_subject_id
        ).all()
        
        for consent in consents:
            portable_data["consents"].append({
                "purpose": consent.purpose,
                "status": consent.status,
                "granted_at": consent.granted_at.isoformat() if consent.granted_at else None
            })
        
        # Get preferences
        preferences = self.db.query(ConsentPreference).filter_by(
            data_subject_id=request.data_subject_id
        ).first()
        
        if preferences:
            portable_data["preferences"] = {
                "global_consent": preferences.global_consent,
                "purpose_consents": preferences.purpose_consents,
                "communication_channels": preferences.communication_channels,
                "language": preferences.language_preference
            }
        
        # Create downloadable file (JSON format)
        file_content = json.dumps(portable_data, indent=2)
        file_hash = hashlib.sha256(file_content.encode()).hexdigest()
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = {
            "download_url": f"/api/v1/gdpr/download/{request.request_id}",
            "format": "json",
            "size_bytes": len(file_content),
            "checksum": file_hash
        }
        
        self.db.commit()
        
        logger.info(f"Completed portability request {request.request_id}")
    
    async def _handle_rectification_request(self, request: DataSubjectRequest):
        """Handle rectification request (GDPR Article 16)."""
        # In production, would update the specified data
        corrections = request.details.get("corrections", {})
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = {
            "corrections_applied": list(corrections.keys()),
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        
        logger.info(f"Completed rectification request {request.request_id}")
    
    async def _handle_restriction_request(self, request: DataSubjectRequest):
        """Handle processing restriction request (GDPR Article 18)."""
        # Restrict processing for specified purposes
        purposes = request.details.get("purposes", [])
        
        for purpose in purposes:
            # Mark consents as restricted
            consents = self.db.query(ConsentRecordDB).filter(
                ConsentRecordDB.data_subject_id == request.data_subject_id,
                ConsentRecordDB.purpose == purpose
            ).all()
            
            for consent in consents:
                consent.metadata = consent.metadata or {}
                consent.metadata["restricted"] = True
                consent.metadata["restriction_date"] = datetime.utcnow().isoformat()
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = {
            "restricted_purposes": purposes,
            "restriction_applied": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        
        logger.info(f"Completed restriction request {request.request_id}")
    
    async def _handle_objection_request(self, request: DataSubjectRequest):
        """Handle objection request (GDPR Article 21)."""
        # Handle objection to processing
        purposes = request.details.get("purposes", [])
        
        for purpose in purposes:
            # Withdraw consent for objected purposes
            consents = self.db.query(ConsentRecordDB).filter(
                ConsentRecordDB.data_subject_id == request.data_subject_id,
                ConsentRecordDB.purpose == purpose,
                ConsentRecordDB.status == "granted"
            ).all()
            
            for consent in consents:
                consent.status = "withdrawn"
                consent.withdrawn_at = datetime.utcnow()
                consent.metadata = consent.metadata or {}
                consent.metadata["objection"] = True
        
        # Update request
        db_request = self.db.query(DataSubjectRequestDB).filter_by(
            request_id=request.request_id
        ).first()
        
        db_request.status = "completed"
        db_request.completed_at = datetime.utcnow()
        db_request.response = {
            "objected_purposes": purposes,
            "objection_processed": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        
        logger.info(f"Completed objection request {request.request_id}")
    
    async def _update_preferences(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose,
        granted: bool
    ):
        """Update consent preferences."""
        preferences = self.db.query(ConsentPreference).filter_by(
            data_subject_id=data_subject_id
        ).first()
        
        if not preferences:
            preferences = ConsentPreference(
                data_subject_id=data_subject_id,
                purpose_consents={}
            )
            self.db.add(preferences)
        
        preferences.purpose_consents = preferences.purpose_consents or {}
        preferences.purpose_consents[purpose.value] = granted
        preferences.updated_at = datetime.utcnow()
        
        self.db.commit()
    
    async def _is_minor(self, data_subject_id: str) -> bool:
        """Check if data subject is a minor."""
        preferences = self.db.query(ConsentPreference).filter_by(
            data_subject_id=data_subject_id
        ).first()
        
        return preferences.minor_status if preferences else False
    
    def _audit_log(
        self,
        consent_id: str,
        data_subject_id: str,
        action: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        reason: Optional[str] = None,
        performed_by: Optional[str] = None
    ):
        """Create audit log entry."""
        audit = ConsentAuditLog(
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            performed_by=performed_by or "system"
        )
        
        self.db.add(audit)
        self.db.commit()
    
    def get_consent_history(self, data_subject_id: str) -> List[Dict[str, Any]]:
        """Get complete consent history for data subject."""
        history = []
        
        # Get all consents
        consents = self.db.query(ConsentRecordDB).filter_by(
            data_subject_id=data_subject_id
        ).order_by(ConsentRecordDB.created_at.desc()).all()
        
        for consent in consents:
            # Get audit trail
            audit_trail = self.db.query(ConsentAuditLog).filter_by(
                consent_id=consent.consent_id
            ).order_by(ConsentAuditLog.timestamp.desc()).all()
            
            history.append({
                "consent_id": consent.consent_id,
                "purpose": consent.purpose,
                "status": consent.status,
                "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
                "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
                "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                "audit_trail": [
                    {
                        "action": audit.action,
                        "timestamp": audit.timestamp.isoformat(),
                        "performed_by": audit.performed_by
                    }
                    for audit in audit_trail
                ]
            })
        
        return history
    
    def generate_consent_report(self) -> Dict[str, Any]:
        """Generate consent management report."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_subjects": 0,
            "consent_stats": {
                "granted": 0,
                "denied": 0,
                "withdrawn": 0,
                "expired": 0,
                "pending": 0
            },
            "by_purpose": {},
            "data_requests": {
                "total": 0,
                "by_right": {},
                "average_response_time": None,
                "overdue": 0
            }
        }
        
        # Count unique data subjects
        subjects = self.db.query(ConsentRecordDB.data_subject_id).distinct().count()
        report["total_subjects"] = subjects
        
        # Consent statistics
        for status in ConsentStatus:
            count = self.db.query(ConsentRecordDB).filter_by(status=status.value).count()
            report["consent_stats"][status.value] = count
        
        # By purpose
        for purpose in ConsentPurpose:
            granted = self.db.query(ConsentRecordDB).filter(
                ConsentRecordDB.purpose == purpose.value,
                ConsentRecordDB.status == "granted"
            ).count()
            
            report["by_purpose"][purpose.value] = {
                "granted": granted,
                "total": self.db.query(ConsentRecordDB).filter_by(purpose=purpose.value).count()
            }
        
        # Data subject requests
        requests = self.db.query(DataSubjectRequestDB).all()
        report["data_requests"]["total"] = len(requests)
        
        for right in DataSubjectRight:
            count = sum(1 for r in requests if r.right == right.value)
            report["data_requests"]["by_right"][right.value] = count
        
        # Average response time
        completed_requests = [r for r in requests if r.completed_at]
        if completed_requests:
            total_time = sum(
                (r.completed_at - r.requested_at).total_seconds()
                for r in completed_requests
            )
            avg_time = total_time / len(completed_requests) / 86400  # Convert to days
            report["data_requests"]["average_response_time"] = f"{avg_time:.1f} days"
        
        # Overdue requests
        overdue = sum(
            1 for r in requests
            if r.response_deadline and r.response_deadline < datetime.utcnow()
            and r.status in ["pending", "in_progress"]
        )
        report["data_requests"]["overdue"] = overdue
        
        return report