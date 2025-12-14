"""
Finance-specific Pydantic schemas for synthetic data generation.

This module defines data models for financial data types including transactions,
credit records, trading data, and other finance-related data structures that
comply with SOX, PCI DSS, and other financial regulations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseRecord


class AccountType(str, Enum):
    """Bank account types."""
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"
    CD = "certificate_of_deposit"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    INVESTMENT = "investment"


class TransactionType(str, Enum):
    """Transaction types."""
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    INTEREST = "interest"
    DIVIDEND = "dividend"


class TransactionCategory(str, Enum):
    """Transaction categories for spending analysis."""
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    GAS_FUEL = "gas_fuel"
    RETAIL = "retail"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    TRAVEL = "travel"
    EDUCATION = "education"
    INSURANCE = "insurance"
    INVESTMENTS = "investments"
    TAXES = "taxes"
    CHARITY = "charity"
    CASH_ATM = "cash_atm"
    OTHER = "other"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CASH = "cash"
    CHECK = "check"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    ACH = "ach"
    WIRE = "wire"
    MOBILE_PAYMENT = "mobile_payment"
    ONLINE = "online"
    OTHER = "other"


class CreditRiskTier(str, Enum):
    """Credit risk tiers."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    BAD = "bad"


class LoanStatus(str, Enum):
    """Loan status categories."""
    CURRENT = "current"
    PAST_DUE_30 = "past_due_30"
    PAST_DUE_60 = "past_due_60"
    PAST_DUE_90 = "past_due_90"
    DEFAULT = "default"
    CHARGED_OFF = "charged_off"
    PAID_OFF = "paid_off"


class MarketSector(str, Enum):
    """Market sectors for trading data."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    MATERIALS = "materials"
    TELECOMMUNICATIONS = "telecommunications"


class InstrumentType(str, Enum):
    """Financial instrument types."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    OPTION = "option"
    FUTURE = "future"
    COMMODITY = "commodity"
    FOREX = "forex"
    CRYPTO = "cryptocurrency"


class CustomerDemographics(BaseModel):
    """De-identified customer demographic information."""
    
    age_group: str = Field(description="Age group (e.g., 18-24, 25-34, etc.)")
    income_bracket: str = Field(description="Income bracket (e.g., 50k-75k)")
    education_level: str = Field(description="Education level")
    employment_status: str = Field(description="Employment status")
    marital_status: str = Field(description="Marital status")
    zip_code_3digit: Optional[str] = Field(description="3-digit ZIP code")
    state: Optional[str] = Field(description="US state abbreviation")
    credit_score_range: str = Field(description="Credit score range (e.g., 650-700)")
    
    @validator('age_group')
    def validate_age_group(cls, v):
        """Validate age group format."""
        valid_groups = [
            "18-24", "25-34", "35-44", "45-54", 
            "55-64", "65-74", "75-84", "85+"
        ]
        if v not in valid_groups:
            raise ValueError(f"Age group must be one of {valid_groups}")
        return v
    
    @validator('income_bracket')
    def validate_income_bracket(cls, v):
        """Validate income bracket format."""
        valid_brackets = [
            "0-25k", "25k-50k", "50k-75k", "75k-100k",
            "100k-150k", "150k-200k", "200k+"
        ]
        if v not in valid_brackets:
            raise ValueError(f"Income bracket must be one of {valid_brackets}")
        return v


class AccountInfo(BaseModel):
    """De-identified account information."""
    
    account_id: str = Field(description="De-identified account identifier")
    account_type: AccountType = Field(description="Type of account")
    product_name: str = Field(description="Financial product name")
    open_date: date = Field(description="Account opening date")
    close_date: Optional[date] = Field(description="Account closing date if applicable")
    status: str = Field(description="Account status (active, closed, suspended)")
    
    # Account balances (anonymized amounts)
    balance_range: str = Field(description="Current balance range")
    available_credit_range: Optional[str] = Field(description="Available credit range")
    credit_limit_range: Optional[str] = Field(description="Credit limit range")


class Transaction(BaseRecord):
    """Financial transaction record with PCI DSS compliance."""
    
    # Transaction identifiers (de-identified)
    transaction_id: str = Field(description="De-identified transaction identifier")
    account_id: str = Field(description="De-identified account identifier")
    
    # Transaction details
    transaction_date: date = Field(description="Transaction date")
    post_date: date = Field(description="Transaction posting date")
    transaction_type: TransactionType = Field(description="Type of transaction")
    category: TransactionCategory = Field(description="Transaction category")
    
    # Amount information (may be binned for privacy)
    amount: Decimal = Field(description="Transaction amount", decimal_places=2)
    amount_range: Optional[str] = Field(description="Amount range for privacy")
    
    # Merchant/counterparty (anonymized)
    merchant_category: str = Field(description="Merchant category code equivalent")
    merchant_location_zip3: Optional[str] = Field(description="Merchant 3-digit ZIP")
    merchant_location_state: Optional[str] = Field(description="Merchant state")
    
    # Payment method
    payment_method: PaymentMethod = Field(description="Payment method used")
    
    # Geographic information (generalized)
    transaction_zip3: Optional[str] = Field(description="Transaction 3-digit ZIP")
    transaction_state: Optional[str] = Field(description="Transaction state")
    
    # Fraud/risk indicators
    fraud_score: Optional[float] = Field(description="Fraud risk score", ge=0.0, le=1.0)
    is_fraud: bool = Field(description="Whether transaction was fraudulent", default=False)
    
    # Temporal features
    hour_of_day: int = Field(description="Hour of transaction (0-23)", ge=0, le=23)
    day_of_week: int = Field(description="Day of week (0=Monday)", ge=0, le=6)
    day_of_month: int = Field(description="Day of month", ge=1, le=31)
    
    # Account balance impact (generalized)
    balance_after_range: Optional[str] = Field(description="Account balance range after transaction")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount."""
        if v == 0:
            raise ValueError("Transaction amount cannot be zero")
        return v
    
    class Config:
        """Configuration for Transaction."""
        schema_extra = {
            "example": {
                "transaction_id": "TXN_ABC123",
                "account_id": "ACCT_DEF456",
                "transaction_date": "2024-01-15",
                "transaction_type": "debit",
                "category": "groceries",
                "amount": "45.67",
                "merchant_category": "grocery_stores",
                "payment_method": "debit_card",
                "hour_of_day": 14,
                "day_of_week": 0,
                "is_fraud": False
            }
        }


class CreditAssessment(BaseModel):
    """Credit risk assessment data."""
    
    # Credit scores (ranges for privacy)
    credit_score_range: str = Field(description="Credit score range")
    debt_to_income_range: str = Field(description="Debt-to-income ratio range")
    
    # Credit history
    credit_history_months: int = Field(description="Length of credit history in months", ge=0)
    number_of_accounts: int = Field(description="Total number of credit accounts", ge=0)
    number_of_inquiries_6mo: int = Field(description="Credit inquiries in last 6 months", ge=0)
    
    # Payment behavior
    payment_history_score: float = Field(description="Payment history score", ge=0.0, le=1.0)
    late_payments_12mo: int = Field(description="Late payments in last 12 months", ge=0)
    
    # Credit utilization
    credit_utilization_range: str = Field(description="Credit utilization percentage range")
    
    # Public records
    bankruptcies: int = Field(description="Number of bankruptcies", ge=0)
    tax_liens: int = Field(description="Number of tax liens", ge=0)
    
    # Assessment result
    risk_tier: CreditRiskTier = Field(description="Assigned credit risk tier")
    default_probability_range: str = Field(description="Default probability range")


class CreditRecord(BaseRecord):
    """Credit assessment record for loan applications."""
    
    # Application information
    application_id: str = Field(description="De-identified application ID")
    application_date: date = Field(description="Loan application date")
    loan_type: str = Field(description="Type of loan requested")
    loan_purpose: str = Field(description="Purpose of loan")
    
    # Applicant demographics (de-identified)
    demographics: CustomerDemographics = Field(description="Applicant demographics")
    
    # Loan details
    requested_amount_range: str = Field(description="Requested loan amount range")
    requested_term_months: int = Field(description="Requested loan term", gt=0)
    
    # Credit assessment
    credit_assessment: CreditAssessment = Field(description="Credit risk assessment")
    
    # Decision
    approval_status: str = Field(description="Loan approval status")
    approved_amount_range: Optional[str] = Field(description="Approved amount range")
    approved_rate_range: Optional[str] = Field(description="Approved interest rate range")
    
    # If funded
    funding_date: Optional[date] = Field(description="Loan funding date")
    current_status: Optional[LoanStatus] = Field(description="Current loan status")
    
    class Config:
        """Configuration for CreditRecord."""
        schema_extra = {
            "example": {
                "application_id": "APP_123456",
                "application_date": "2024-01-10",
                "loan_type": "personal",
                "loan_purpose": "debt_consolidation",
                "requested_amount_range": "10k-20k",
                "requested_term_months": 36,
                "approval_status": "approved"
            }
        }


class TradingData(BaseRecord):
    """De-identified trading/investment data."""
    
    # Trade identifiers
    trade_id: str = Field(description="De-identified trade identifier")
    account_id: str = Field(description="De-identified account identifier")
    
    # Trade details
    trade_date: date = Field(description="Trade execution date")
    settlement_date: date = Field(description="Trade settlement date")
    
    # Instrument information
    instrument_type: InstrumentType = Field(description="Type of financial instrument")
    sector: Optional[MarketSector] = Field(description="Market sector")
    
    # Trade execution
    trade_action: str = Field(description="Trade action (buy, sell)")
    quantity_range: str = Field(description="Quantity range for privacy")
    price_range: str = Field(description="Price range at execution")
    trade_value_range: str = Field(description="Total trade value range")
    
    # Market conditions
    market_volatility_percentile: float = Field(
        description="Market volatility percentile at trade time", ge=0.0, le=100.0
    )
    
    # Account information (generalized)
    account_value_range: str = Field(description="Account value range")
    portfolio_concentration: str = Field(description="Portfolio concentration level")
    
    # Risk metrics
    position_size_percent: float = Field(
        description="Position size as percentage of portfolio", ge=0.0, le=100.0
    )
    
    # Customer profile (anonymized)
    investor_profile: str = Field(description="Investor risk profile")
    experience_level: str = Field(description="Trading experience level")
    
    class Config:
        """Configuration for TradingData."""
        schema_extra = {
            "example": {
                "trade_id": "TRADE_789",
                "account_id": "INV_ACCT_101",
                "trade_date": "2024-01-16",
                "instrument_type": "stock",
                "sector": "technology",
                "trade_action": "buy",
                "quantity_range": "100-500",
                "price_range": "50-100",
                "trade_value_range": "5k-10k"
            }
        }


class FraudEvent(BaseModel):
    """Fraud event for fraud detection datasets."""
    
    # Event classification
    fraud_type: str = Field(description="Type of fraud detected")
    fraud_method: str = Field(description="Method used for fraud")
    
    # Detection information
    detection_method: str = Field(description="How fraud was detected")
    detection_time_hours: float = Field(description="Hours from event to detection", ge=0.0)
    
    # Impact assessment
    loss_amount_range: str = Field(description="Financial loss range")
    recovered_amount_range: Optional[str] = Field(description="Recovered amount range")
    
    # Investigation outcome
    confirmed_fraud: bool = Field(description="Whether fraud was confirmed")
    investigation_duration_days: Optional[int] = Field(description="Investigation duration", ge=0)


class MarketData(BaseRecord):
    """Market data for financial modeling."""
    
    # Market identifiers
    market_date: date = Field(description="Market data date")
    market_session: str = Field(description="Market session (regular, pre, post)")
    
    # Market indices (anonymized symbols)
    market_index_changes: Dict[str, float] = Field(
        default_factory=dict,
        description="Market index percentage changes"
    )
    
    # Volatility measures
    implied_volatility_percentile: float = Field(
        description="Implied volatility percentile", ge=0.0, le=100.0
    )
    historical_volatility_percentile: float = Field(
        description="Historical volatility percentile", ge=0.0, le=100.0
    )
    
    # Volume indicators
    market_volume_percentile: float = Field(
        description="Market volume percentile vs historical", ge=0.0, le=100.0
    )
    
    # Economic indicators (scaled/normalized)
    economic_indicators: Dict[str, float] = Field(
        default_factory=dict,
        description="Normalized economic indicators"
    )


# Finance utility functions

def anonymize_account_number(account_number: str) -> str:
    """Anonymize account number for PCI DSS compliance."""
    if len(account_number) < 8:
        return "XXXX" + account_number[-4:]
    return "XXXX-XXXX-XXXX-" + account_number[-4:]


def categorize_amount(amount: float) -> str:
    """Categorize transaction amount into ranges for privacy."""
    if amount < 0:
        amount = abs(amount)
    
    if amount < 10:
        return "0-10"
    elif amount < 50:
        return "10-50"
    elif amount < 100:
        return "50-100"
    elif amount < 500:
        return "100-500"
    elif amount < 1000:
        return "500-1k"
    elif amount < 5000:
        return "1k-5k"
    elif amount < 10000:
        return "5k-10k"
    elif amount < 50000:
        return "10k-50k"
    elif amount < 100000:
        return "50k-100k"
    else:
        return "100k+"


def is_pci_compliant_card_number(card_number: str) -> bool:
    """Check if card number representation is PCI DSS compliant."""
    # PCI DSS allows showing first 6 and last 4 digits
    # or masking all but last 4 digits
    if "XXXX" in card_number or "*" in card_number:
        return True
    # If showing actual digits, ensure it's not a complete card number
    return len(card_number.replace("-", "").replace(" ", "")) <= 10


def generate_credit_score_range(score: int) -> str:
    """Convert credit score to range for privacy protection."""
    if score < 580:
        return "300-579"
    elif score < 670:
        return "580-669"
    elif score < 740:
        return "670-739"
    elif score < 800:
        return "740-799"
    else:
        return "800-850"


# Schema constants for testing and validation
FINANCE_SCHEMA = {
    "domain": "finance",
    "fields": {
        "account_id": {"type": "string", "description": "Unique account identifier"},
        "customer_id": {"type": "string", "description": "Customer identifier"},
        "transaction_amount": {"type": "decimal", "description": "Transaction amount"},
        "transaction_type": {"type": "string", "enum": ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]},
        "transaction_date": {"type": "datetime", "description": "Transaction timestamp"}
    },
    "compliance": ["PCI-DSS", "SOX", "GDPR"],
    "privacy_level": "medium"
}