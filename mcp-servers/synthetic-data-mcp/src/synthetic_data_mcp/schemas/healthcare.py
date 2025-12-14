"""
Healthcare-specific Pydantic schemas for synthetic data generation.

This module defines data models for healthcare data types including patient records,
clinical trials, medical claims, and other healthcare-related data structures
that comply with HIPAA and other healthcare regulations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseRecord


class Gender(str, Enum):
    """Gender enumeration."""
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    UNKNOWN = "U"


class Race(str, Enum):
    """Race/ethnicity categories (US Census)."""
    WHITE = "white"
    BLACK_AFRICAN_AMERICAN = "black_african_american"
    ASIAN = "asian"
    AMERICAN_INDIAN_ALASKA_NATIVE = "american_indian_alaska_native"
    NATIVE_HAWAIIAN_PACIFIC_ISLANDER = "native_hawaiian_pacific_islander"
    HISPANIC_LATINO = "hispanic_latino"
    TWO_OR_MORE_RACES = "two_or_more_races"
    OTHER = "other"
    UNKNOWN = "unknown"


class InsuranceType(str, Enum):
    """Insurance type categories."""
    COMMERCIAL = "commercial"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    TRICARE = "tricare"
    SELF_PAY = "self_pay"
    OTHER = "other"
    UNKNOWN = "unknown"


class AdmissionType(str, Enum):
    """Hospital admission types."""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ELECTIVE = "elective"
    NEWBORN = "newborn"
    TRAUMA = "trauma"


class DischargeDisposition(str, Enum):
    """Patient discharge disposition."""
    HOME = "home"
    HOME_WITH_SERVICES = "home_with_services"
    SNF = "skilled_nursing_facility"
    REHABILITATION = "rehabilitation"
    HOSPICE = "hospice"
    TRANSFER = "transfer_to_hospital"
    EXPIRED = "expired"


class VitalStatus(str, Enum):
    """Patient vital status."""
    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


class PatientDemographics(BaseModel):
    """Patient demographic information (de-identified)."""
    
    age_group: str = Field(description="Age group (e.g., 18-24, 25-34, etc.)")
    gender: Gender = Field(description="Patient gender")
    race: Race = Field(description="Patient race/ethnicity")
    zip_code_3digit: Optional[str] = Field(description="3-digit ZIP code for geographic region")
    state: Optional[str] = Field(description="US state abbreviation")
    
    @validator('age_group')
    def validate_age_group(cls, v):
        """Validate age group format."""
        valid_groups = [
            "0-17", "18-24", "25-34", "35-44", "45-54", 
            "55-64", "65-74", "75-84", "85+"
        ]
        if v not in valid_groups:
            raise ValueError(f"Age group must be one of {valid_groups}")
        return v
    
    @validator('zip_code_3digit')
    def validate_zip_code(cls, v):
        """Validate 3-digit ZIP code."""
        if v and (len(v) != 3 or not v.isdigit()):
            raise ValueError("ZIP code must be exactly 3 digits")
        return v


class MedicalCondition(BaseModel):
    """Medical condition/diagnosis."""
    
    icd10_code: str = Field(description="ICD-10 diagnosis code")
    description: str = Field(description="Condition description")
    severity: str = Field(description="Condition severity (mild, moderate, severe)")
    onset_date: date = Field(description="Condition onset date")
    status: str = Field(description="Condition status (active, resolved, chronic)")
    
    @validator('icd10_code')
    def validate_icd10(cls, v):
        """Basic ICD-10 code format validation."""
        if not v or len(v) < 3:
            raise ValueError("ICD-10 code must be at least 3 characters")
        return v.upper()


class Medication(BaseModel):
    """Medication information."""
    
    ndc_code: Optional[str] = Field(description="NDC (National Drug Code)")
    generic_name: str = Field(description="Generic medication name")
    brand_name: Optional[str] = Field(description="Brand medication name")
    dosage: str = Field(description="Medication dosage")
    frequency: str = Field(description="Dosing frequency")
    start_date: date = Field(description="Medication start date")
    end_date: Optional[date] = Field(description="Medication end date")
    prescribing_specialty: str = Field(description="Prescribing physician specialty")


class LabResult(BaseModel):
    """Laboratory test result."""
    
    test_code: str = Field(description="Laboratory test code (LOINC)")
    test_name: str = Field(description="Laboratory test name")
    result_value: Optional[str] = Field(description="Test result value")
    result_numeric: Optional[Decimal] = Field(description="Numeric result value")
    unit: Optional[str] = Field(description="Result unit of measurement")
    reference_range: Optional[str] = Field(description="Normal reference range")
    abnormal_flag: Optional[str] = Field(description="Abnormal result flag")
    test_date: date = Field(description="Test performance date")


class Procedure(BaseModel):
    """Medical procedure information."""
    
    cpt_code: str = Field(description="CPT (Current Procedural Terminology) code")
    description: str = Field(description="Procedure description")
    procedure_date: date = Field(description="Procedure performance date")
    provider_specialty: str = Field(description="Performing provider specialty")
    setting: str = Field(description="Procedure setting (inpatient, outpatient, etc.)")
    duration_minutes: Optional[int] = Field(description="Procedure duration in minutes")


class Encounter(BaseModel):
    """Healthcare encounter/visit."""
    
    encounter_type: str = Field(description="Type of encounter (inpatient, outpatient, ED)")
    admission_date: date = Field(description="Admission/visit date")
    discharge_date: Optional[date] = Field(description="Discharge date (for inpatient)")
    length_of_stay: Optional[int] = Field(description="Length of stay in days")
    admission_type: Optional[AdmissionType] = Field(description="Admission type")
    discharge_disposition: Optional[DischargeDisposition] = Field(description="Discharge disposition")
    primary_diagnosis: str = Field(description="Primary diagnosis ICD-10 code")
    secondary_diagnoses: List[str] = Field(default_factory=list, description="Secondary diagnosis codes")
    procedures: List[Procedure] = Field(default_factory=list, description="Procedures performed")
    total_charges: Optional[Decimal] = Field(description="Total encounter charges")


class PatientRecord(BaseRecord):
    """Complete synthetic patient record with HIPAA-compliant de-identification."""
    
    # Patient demographics (de-identified)
    demographics: PatientDemographics = Field(description="De-identified patient demographics")
    
    # Insurance information (de-identified)
    insurance_type: InsuranceType = Field(description="Primary insurance type")
    
    # Clinical information
    conditions: List[MedicalCondition] = Field(default_factory=list, description="Medical conditions")
    medications: List[Medication] = Field(default_factory=list, description="Medications")
    lab_results: List[LabResult] = Field(default_factory=list, description="Laboratory results")
    encounters: List[Encounter] = Field(default_factory=list, description="Healthcare encounters")
    
    # Risk factors and outcomes
    comorbidity_count: int = Field(description="Number of comorbid conditions", ge=0)
    total_encounters: int = Field(description="Total number of encounters", ge=0)
    total_cost: Optional[Decimal] = Field(description="Total healthcare cost")
    
    # Temporal information (relative dates to protect privacy)
    first_encounter_days_ago: int = Field(description="Days since first encounter", ge=0)
    last_encounter_days_ago: int = Field(description="Days since last encounter", ge=0)
    
    # Vital status
    vital_status: VitalStatus = Field(description="Patient vital status")
    
    class Config:
        """Configuration for PatientRecord."""
        schema_extra = {
            "example": {
                "demographics": {
                    "age_group": "45-54",
                    "gender": "F",
                    "race": "white",
                    "zip_code_3digit": "123",
                    "state": "CA"
                },
                "insurance_type": "commercial",
                "conditions": [
                    {
                        "icd10_code": "E11.9",
                        "description": "Type 2 diabetes mellitus without complications",
                        "severity": "moderate",
                        "onset_date": "2020-01-15",
                        "status": "active"
                    }
                ],
                "comorbidity_count": 2,
                "total_encounters": 8,
                "vital_status": "alive"
            }
        }


class ClinicalTrialPhase(str, Enum):
    """Clinical trial phases."""
    PHASE_0 = "phase_0"
    PHASE_I = "phase_1"
    PHASE_II = "phase_2"
    PHASE_III = "phase_3"
    PHASE_IV = "phase_4"


class TrialStatus(str, Enum):
    """Clinical trial status."""
    NOT_YET_RECRUITING = "not_yet_recruiting"
    RECRUITING = "recruiting"
    ENROLLING = "enrolling_by_invitation"
    ACTIVE = "active_not_recruiting"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class AdverseEvent(BaseModel):
    """Adverse event in clinical trial."""
    
    event_term: str = Field(description="Adverse event term (MedDRA)")
    severity_grade: int = Field(description="Severity grade (1-5)", ge=1, le=5)
    relationship_to_treatment: str = Field(description="Relationship to study treatment")
    outcome: str = Field(description="Event outcome")
    days_from_start: int = Field(description="Days from treatment start", ge=0)
    resolved: bool = Field(description="Whether event resolved")


class ClinicalTrialParticipant(BaseModel):
    """De-identified clinical trial participant."""
    
    participant_id: str = Field(description="De-identified participant ID")
    demographics: PatientDemographics = Field(description="Participant demographics")
    enrollment_date: date = Field(description="Trial enrollment date")
    randomization_arm: str = Field(description="Treatment arm assignment")
    baseline_conditions: List[str] = Field(description="Baseline medical conditions")
    
    # Outcomes
    primary_endpoint_met: Optional[bool] = Field(description="Primary endpoint achievement")
    secondary_endpoints: Dict[str, Any] = Field(default_factory=dict, description="Secondary endpoint results")
    adverse_events: List[AdverseEvent] = Field(default_factory=list, description="Adverse events")
    
    # Trial completion
    completed_trial: bool = Field(description="Whether participant completed trial")
    discontinuation_reason: Optional[str] = Field(description="Reason for discontinuation")
    days_on_study: int = Field(description="Days on study", ge=0)


class ClinicalTrial(BaseRecord):
    """Synthetic clinical trial dataset."""
    
    trial_id: str = Field(description="De-identified trial identifier")
    phase: ClinicalTrialPhase = Field(description="Clinical trial phase")
    status: TrialStatus = Field(description="Trial status")
    therapeutic_area: str = Field(description="Therapeutic area")
    intervention_type: str = Field(description="Type of intervention")
    
    # Trial design
    study_design: str = Field(description="Study design (RCT, observational, etc.)")
    blinding: str = Field(description="Blinding type (single, double, open-label)")
    randomization: bool = Field(description="Whether randomized")
    placebo_controlled: bool = Field(description="Whether placebo-controlled")
    
    # Participants
    participants: List[ClinicalTrialParticipant] = Field(description="Trial participants")
    target_enrollment: int = Field(description="Target enrollment", gt=0)
    actual_enrollment: int = Field(description="Actual enrollment", ge=0)
    
    # Endpoints
    primary_endpoint: str = Field(description="Primary endpoint description")
    secondary_endpoints: List[str] = Field(default_factory=list, description="Secondary endpoints")
    
    # Timeline
    start_date: date = Field(description="Trial start date")
    end_date: Optional[date] = Field(description="Trial end date")
    duration_months: int = Field(description="Trial duration in months", ge=1)
    
    # Results (if completed)
    primary_endpoint_met: Optional[bool] = Field(description="Primary endpoint achievement")
    statistical_significance: Optional[bool] = Field(description="Statistical significance achieved")
    
    class Config:
        """Configuration for ClinicalTrial."""
        schema_extra = {
            "example": {
                "trial_id": "TRIAL_001",
                "phase": "phase_2",
                "status": "completed",
                "therapeutic_area": "oncology",
                "intervention_type": "drug",
                "study_design": "randomized_controlled_trial",
                "target_enrollment": 200,
                "actual_enrollment": 189,
                "primary_endpoint": "Overall Response Rate",
                "duration_months": 24
            }
        }


class HealthcareClaim(BaseRecord):
    """Healthcare insurance claim (de-identified)."""
    
    claim_id: str = Field(description="De-identified claim identifier")
    member_demographics: PatientDemographics = Field(description="Member demographics")
    
    # Claim details
    service_date: date = Field(description="Date of service")
    claim_type: str = Field(description="Claim type (medical, pharmacy, dental)")
    place_of_service: str = Field(description="Place of service code")
    provider_specialty: str = Field(description="Provider specialty")
    
    # Diagnoses and procedures
    primary_diagnosis: str = Field(description="Primary diagnosis ICD-10")
    secondary_diagnoses: List[str] = Field(default_factory=list, description="Secondary diagnoses")
    procedures: List[str] = Field(default_factory=list, description="Procedure codes (CPT/HCPCS)")
    
    # Financial information
    billed_amount: Decimal = Field(description="Provider billed amount", ge=0)
    allowed_amount: Decimal = Field(description="Insurance allowed amount", ge=0)
    paid_amount: Decimal = Field(description="Insurance paid amount", ge=0)
    member_liability: Decimal = Field(description="Member out-of-pocket", ge=0)
    
    # Processing information
    claim_status: str = Field(description="Claim processing status")
    denial_reason: Optional[str] = Field(description="Denial reason if applicable")
    processed_date: date = Field(description="Claim processing date")
    
    @validator('allowed_amount')
    def allowed_not_exceed_billed(cls, v, values):
        """Ensure allowed amount doesn't exceed billed amount."""
        if 'billed_amount' in values and v > values['billed_amount']:
            raise ValueError("Allowed amount cannot exceed billed amount")
        return v


# Healthcare utility functions

def generate_synthetic_mrn() -> str:
    """Generate a synthetic Medical Record Number."""
    import random
    return f"MRN{random.randint(100000, 999999)}"


def generate_age_group_from_age(age: int) -> str:
    """Convert age to age group for privacy protection."""
    if age < 18:
        return "0-17"
    elif age < 25:
        return "18-24"
    elif age < 35:
        return "25-34"
    elif age < 45:
        return "35-44"
    elif age < 55:
        return "45-54"
    elif age < 65:
        return "55-64"
    elif age < 75:
        return "65-74"
    elif age < 85:
        return "75-84"
    else:
        return "85+"


def is_hipaa_compliant_age_group(age_group: str) -> bool:
    """Check if age group meets HIPAA Safe Harbor requirements."""
    # HIPAA allows age groups but requires special handling for ages 90+
    return age_group != "90+" and age_group in [
        "0-17", "18-24", "25-34", "35-44", "45-54", 
        "55-64", "65-74", "75-84", "85+"
    ]


# Schema constants for testing and validation
HEALTHCARE_SCHEMA = {
    "domain": "healthcare", 
    "fields": {
        "patient_id": {"type": "string", "description": "Unique patient identifier"},
        "age": {"type": "integer", "description": "Patient age", "min": 0, "max": 120},
        "gender": {"type": "string", "enum": ["M", "F", "O", "U"]},
        "diagnosis": {"type": "string", "description": "Primary diagnosis"},
        "admission_date": {"type": "date", "description": "Hospital admission date"}
    },
    "compliance": ["HIPAA", "Safe Harbor"],
    "privacy_level": "high"
}