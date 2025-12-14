"""
Synthetic Data Platform MCP

A domain-specific Model Context Protocol server for generating compliant,
high-fidelity synthetic datasets for healthcare and finance companies.
"""

__version__ = "0.1.0"
__author__ = "Marc Shade"
__email__ = "marc@2acrestudios.com"
__license__ = "MIT"

from .server import app
from .core.generator import SyntheticDataGenerator
from .compliance.validator import ComplianceValidator
from .privacy.engine import PrivacyEngine
from .schemas.healthcare import PatientRecord, ClinicalTrial
from .schemas.finance import Transaction, CreditRecord

__all__ = [
    "app",
    "SyntheticDataGenerator",
    "ComplianceValidator",
    "PrivacyEngine",
    "PatientRecord",
    "ClinicalTrial",
    "Transaction",
    "CreditRecord",
]