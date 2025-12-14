"""
Base schemas and enums for the synthetic data platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class DataDomain(str, Enum):
    """Supported data domains."""
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    CUSTOM = "custom"


class OutputFormat(str, Enum):
    """Supported output formats."""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    DATABASE = "database"


class PrivacyLevel(str, Enum):
    """Privacy protection levels with corresponding epsilon values."""
    LOW = "low"           # ε = 10.0
    MEDIUM = "medium"     # ε = 1.0
    HIGH = "high"         # ε = 0.1
    MAXIMUM = "maximum"   # ε = 0.01


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    # Healthcare
    HIPAA = "hipaa"
    FDA = "fda"
    HITECH = "hitech"
    
    # Finance
    SOX = "sox"
    PCI_DSS = "pci_dss"
    BASEL_III = "basel_iii"
    MIFID_II = "mifid_ii"
    DODD_FRANK = "dodd_frank"
    
    # Privacy
    GDPR = "gdpr"
    CCPA = "ccpa"
    COPPA = "coppa"
    FERPA = "ferpa"
    
    # Custom
    CUSTOM = "custom"


class GenerationStatus(str, Enum):
    """Status of data generation operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class InferenceMode(str, Enum):
    """LLM inference mode for data generation."""
    LOCAL = "local"        # Ollama - Fully private, on-premises
    CLOUD = "cloud"        # OpenAI - Cloud-based inference
    HYBRID = "hybrid"      # Mixed mode based on data sensitivity
    FALLBACK = "fallback"  # Mock generation for testing


class BaseRecord(BaseModel):
    """Base model for all synthetic records."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the record")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    synthetic: bool = Field(default=True, description="Flag indicating this is synthetic data")
    version: str = Field(default="1.0", description="Schema version")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ComplianceMetadata(BaseModel):
    """Metadata for compliance validation."""
    
    frameworks: List[ComplianceFramework] = Field(description="Applied compliance frameworks")
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    privacy_level: PrivacyLevel = Field(description="Applied privacy level")
    audit_trail_id: Optional[str] = Field(default=None, description="Associated audit trail identifier")
    
    @validator('frameworks')
    def validate_frameworks(cls, v):
        """Ensure frameworks are unique."""
        return list(set(v))


class PrivacyMetadata(BaseModel):
    """Metadata for privacy protection."""
    
    differential_privacy: Dict[str, float] = Field(
        default_factory=dict,
        description="Differential privacy parameters (epsilon, delta, etc.)"
    )
    anonymization_techniques: List[str] = Field(
        default_factory=list,
        description="Applied anonymization techniques"
    )
    risk_assessment: Dict[str, float] = Field(
        default_factory=dict,
        description="Privacy risk scores and metrics"
    )
    privacy_budget: Dict[str, float] = Field(
        default_factory=dict,
        description="Privacy budget allocation and usage"
    )


class StatisticalMetadata(BaseModel):
    """Metadata for statistical validation."""
    
    fidelity_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Statistical fidelity scores"
    )
    distribution_tests: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Distribution comparison test results"
    )
    correlation_preservation: Dict[str, float] = Field(
        default_factory=dict,
        description="Correlation structure preservation metrics"
    )
    utility_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Utility preservation for ML tasks"
    )


class DatasetMetadata(BaseModel):
    """Comprehensive metadata for synthetic datasets."""
    
    domain: DataDomain = Field(description="Data domain")
    dataset_type: str = Field(description="Specific dataset type")
    record_count: int = Field(description="Number of records")
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata components
    compliance: Optional[ComplianceMetadata] = None
    privacy: Optional[PrivacyMetadata] = None
    statistical: Optional[StatisticalMetadata] = None
    
    # Generation info
    generated_at: datetime = Field(default_factory=datetime.now)
    generator_version: str = Field(default="0.1.0")
    seed: Optional[int] = Field(default=None, description="Random seed used for generation")


class SyntheticDataset(BaseModel):
    """Container for synthetic datasets with metadata."""
    
    records: List[BaseRecord] = Field(description="Synthetic data records")
    metadata: DatasetMetadata = Field(description="Dataset metadata")
    
    def __len__(self) -> int:
        """Return the number of records."""
        return len(self.records)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "records": [record.dict() for record in self.records],
            "metadata": self.metadata.dict()
        }
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert records to list of dictionaries."""
        return [record.dict() for record in self.records]


class ValidationResult(BaseModel):
    """Result of validation operations."""
    
    passed: bool = Field(description="Whether validation passed")
    score: float = Field(description="Validation score (0.0-1.0)", ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed validation results")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    timestamp: datetime = Field(default_factory=datetime.now)


class ComplianceResult(ValidationResult):
    """Result of compliance validation."""
    
    framework: ComplianceFramework = Field(description="Validated framework")
    risk_score: float = Field(description="Compliance risk score", ge=0.0, le=1.0)
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="Compliance violations found")
    certification_ready: bool = Field(description="Ready for regulatory certification")


class PrivacyResult(ValidationResult):
    """Result of privacy analysis."""
    
    privacy_level: PrivacyLevel = Field(description="Assessed privacy level")
    reidentification_risk: float = Field(description="Re-identification risk", ge=0.0, le=1.0)
    attack_resistance: Dict[str, float] = Field(
        default_factory=dict,
        description="Resistance to different privacy attacks"
    )
    privacy_budget_remaining: Dict[str, float] = Field(
        default_factory=dict,
        description="Remaining privacy budget"
    )


class StatisticalResult(ValidationResult):
    """Result of statistical validation."""
    
    fidelity_score: float = Field(description="Overall statistical fidelity", ge=0.0, le=1.0)
    distribution_similarity: Dict[str, float] = Field(
        default_factory=dict,
        description="Distribution similarity scores"
    )
    correlation_preservation: float = Field(
        description="Correlation structure preservation", ge=0.0, le=1.0
    )
    utility_preservation: Dict[str, float] = Field(
        default_factory=dict,
        description="ML utility preservation scores"
    )


# Utility functions

def get_epsilon_for_privacy_level(privacy_level: PrivacyLevel) -> float:
    """Get differential privacy epsilon value for privacy level."""
    epsilon_map = {
        PrivacyLevel.LOW: 10.0,
        PrivacyLevel.MEDIUM: 1.0,
        PrivacyLevel.HIGH: 0.1,
        PrivacyLevel.MAXIMUM: 0.01
    }
    return epsilon_map[privacy_level]


def get_compliance_requirements(framework: ComplianceFramework) -> Dict[str, Any]:
    """Get compliance requirements for a framework."""
    requirements = {
        ComplianceFramework.HIPAA: {
            "pii_removal": ["ssn", "name", "address", "phone", "email", "dob"],
            "safe_harbor_identifiers": 18,
            "risk_threshold": 0.04,
            "documentation_required": True
        },
        ComplianceFramework.GDPR: {
            "lawful_basis_required": True,
            "consent_tracking": True,
            "data_minimization": True,
            "right_to_explanation": True,
            "risk_threshold": 0.01
        },
        ComplianceFramework.SOX: {
            "internal_controls": True,
            "audit_trail": True,
            "data_integrity": True,
            "change_management": True
        },
        ComplianceFramework.PCI_DSS: {
            "cardholder_data_protection": True,
            "encryption_required": True,
            "access_controls": True,
            "monitoring_required": True
        }
    }
    return requirements.get(framework, {})