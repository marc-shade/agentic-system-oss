"""
Multi-format data ingestion pipeline for learning from real data.
"""

import io
import json
import csv
from typing import Any, Dict, List, Optional, Union, IO, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import hashlib
from datetime import datetime

from ..privacy.engine import PrivacyEngine
from .pattern_analyzer import PatternAnalyzer


class DataIngestionPipeline:
    """Multi-format data ingestion pipeline with privacy protection."""
    
    def __init__(self, privacy_engine: Optional[PrivacyEngine] = None):
        """
        Initialize the ingestion pipeline.
        
        Args:
            privacy_engine: Optional privacy engine for PII detection/removal
        """
        self.privacy_engine = privacy_engine or PrivacyEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.supported_formats = {
            'csv': self._ingest_csv,
            'json': self._ingest_json,
            'excel': self._ingest_excel,
            'parquet': self._ingest_parquet,
            'sql': self._ingest_sql,
            'api': self._ingest_api,
            'dict': self._ingest_dict
        }
        
    async def ingest(
        self,
        source: Union[str, bytes, IO, List[Dict], pd.DataFrame],
        format: str = 'auto',
        anonymize: bool = True,
        learn_patterns: bool = True,
        sample_size: Optional[int] = None,
        credit_card_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest data from various sources and learn patterns.
        
        Args:
            source: Data source (file path, bytes, file object, or data)
            format: Data format (auto-detect if not specified)
            anonymize: Whether to anonymize PII before analysis
            learn_patterns: Whether to extract patterns from data
            sample_size: Optional sample size for large datasets
            credit_card_provider: Optional credit card provider for test numbers
                                 (visa, mastercard, amex, discover, etc.)
            
        Returns:
            Ingestion result with patterns and metadata
        """
        try:
            # Auto-detect format if needed
            if format == 'auto':
                format = self._detect_format(source)
                
            logger.info(f"Ingesting data in {format} format")
            
            # Parse the data
            if format not in self.supported_formats:
                raise ValueError(f"Unsupported format: {format}")
                
            raw_data = await self.supported_formats[format](source)
            
            # Sample if needed
            if sample_size and len(raw_data) > sample_size:
                raw_data = self._sample_data(raw_data, sample_size)
                
            # Convert to DataFrame for processing
            df = pd.DataFrame(raw_data) if isinstance(raw_data, list) else raw_data
            
            # Detect and optionally anonymize PII
            pii_report = None
            if anonymize:
                df, pii_report = await self._anonymize_data(df, credit_card_provider)
                
            # Learn patterns if requested
            patterns = None
            if learn_patterns:
                patterns = self.pattern_analyzer.generate_pattern_summary(df)
                
            # Generate pattern ID for reference
            pattern_id = self._generate_pattern_id(df)
            
            # Store the learned pattern
            result = {
                "pattern_id": pattern_id,
                "format": format,
                "rows_ingested": len(df),
                "columns": list(df.columns),
                "data_types": df.dtypes.astype(str).to_dict(),
                "patterns": patterns,
                "pii_report": pii_report,
                "metadata": {
                    "ingested_at": datetime.now().isoformat(),
                    "anonymized": anonymize,
                    "sample_size": sample_size,
                    "original_size": len(raw_data) if isinstance(raw_data, list) else len(df)
                }
            }
            
            # Store the pattern for later use
            self._store_pattern(pattern_id, result)
            
            logger.info(f"Successfully ingested {len(df)} rows with pattern ID: {pattern_id}")
            return result
            
        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            raise
            
    def _detect_format(self, source: Any) -> str:
        """Auto-detect data format from source."""
        if isinstance(source, pd.DataFrame):
            return 'dataframe'
        elif isinstance(source, list) and source and isinstance(source[0], dict):
            return 'dict'
        elif isinstance(source, str):
            if source.endswith('.csv'):
                return 'csv'
            elif source.endswith('.json'):
                return 'json'
            elif source.endswith('.xlsx') or source.endswith('.xls'):
                return 'excel'
            elif source.endswith('.parquet'):
                return 'parquet'
            elif source.startswith('http'):
                return 'api'
        elif isinstance(source, bytes):
            # Try to decode and detect
            try:
                decoded = source.decode('utf-8')
                if decoded.startswith('[') or decoded.startswith('{'):
                    return 'json'
                else:
                    return 'csv'
            except:
                return 'binary'
                
        return 'unknown'
        
    async def _ingest_csv(self, source: Union[str, bytes, IO]) -> pd.DataFrame:
        """Ingest CSV data."""
        if isinstance(source, str):
            if Path(source).exists():
                return pd.read_csv(source)
            else:
                # Assume it's CSV content
                return pd.read_csv(io.StringIO(source))
        elif isinstance(source, bytes):
            return pd.read_csv(io.BytesIO(source))
        else:
            return pd.read_csv(source)
            
    async def _ingest_json(self, source: Union[str, bytes, IO]) -> Union[List[Dict], pd.DataFrame]:
        """Ingest JSON data."""
        if isinstance(source, str):
            if Path(source).exists():
                with open(source, 'r') as f:
                    data = json.load(f)
            else:
                data = json.loads(source)
        elif isinstance(source, bytes):
            data = json.loads(source.decode('utf-8'))
        else:
            data = json.load(source)
            
        # Convert to DataFrame if it's a list of records
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Handle nested JSON
            return pd.json_normalize(data)
        else:
            return data
            
    async def _ingest_excel(self, source: Union[str, bytes, IO]) -> pd.DataFrame:
        """Ingest Excel data."""
        if isinstance(source, str):
            return pd.read_excel(source)
        elif isinstance(source, bytes):
            return pd.read_excel(io.BytesIO(source))
        else:
            return pd.read_excel(source)
            
    async def _ingest_parquet(self, source: Union[str, bytes, IO]) -> pd.DataFrame:
        """Ingest Parquet data."""
        if isinstance(source, str):
            return pd.read_parquet(source)
        elif isinstance(source, bytes):
            return pd.read_parquet(io.BytesIO(source))
        else:
            return pd.read_parquet(source)
            
    async def _ingest_sql(self, source: str) -> pd.DataFrame:
        """Ingest data from SQL query."""
        # This would require database connection details
        # For now, raise not implemented
        raise NotImplementedError("SQL ingestion requires database connection setup")
        
    async def _ingest_api(self, source: str) -> Union[List[Dict], pd.DataFrame]:
        """Ingest data from API endpoint."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(source) as response:
                data = await response.json()
                if isinstance(data, list):
                    return pd.DataFrame(data)
                else:
                    return pd.json_normalize(data)
                    
    async def _ingest_dict(self, source: List[Dict]) -> pd.DataFrame:
        """Ingest list of dictionaries."""
        return pd.DataFrame(source)
        
    def _sample_data(self, data: Union[List, pd.DataFrame], sample_size: int) -> Union[List, pd.DataFrame]:
        """Sample data for large datasets."""
        if isinstance(data, pd.DataFrame):
            return data.sample(n=min(sample_size, len(data)), random_state=42)
        else:
            import random
            random.seed(42)
            return random.sample(data, min(sample_size, len(data)))
            
    async def _anonymize_data(self, df: pd.DataFrame, credit_card_provider: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Anonymize PII in the data.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Tuple of (anonymized DataFrame, PII report)
        """
        pii_report = {
            "detected_columns": [],
            "anonymization_applied": {},
            "risk_score": 0.0
        }
        
        anonymized_df = df.copy()
        
        for col in df.columns:
            # Check for PII patterns
            if self._is_potential_pii(col, df[col]):
                pii_report["detected_columns"].append(col)
                
                # Apply anonymization based on data type
                if 'email' in col.lower():
                    anonymized_df[col] = self._anonymize_email(df[col])
                    pii_report["anonymization_applied"][col] = "email_hash"
                elif 'phone' in col.lower():
                    anonymized_df[col] = self._anonymize_phone(df[col])
                    pii_report["anonymization_applied"][col] = "phone_mask"
                elif 'ssn' in col.lower() or 'social' in col.lower():
                    anonymized_df[col] = self._anonymize_ssn(df[col])
                    pii_report["anonymization_applied"][col] = "ssn_mask"
                elif 'credit' in col.lower() or 'card' in col.lower():
                    anonymized_df[col] = self._anonymize_credit_card(df[col], credit_card_provider)
                    pii_report["anonymization_applied"][col] = "credit_card_test_numbers"
                elif 'name' in col.lower():
                    anonymized_df[col] = self._anonymize_name(df[col])
                    pii_report["anonymization_applied"][col] = "name_generalize"
                elif 'address' in col.lower():
                    anonymized_df[col] = self._anonymize_address(df[col])
                    pii_report["anonymization_applied"][col] = "address_generalize"
                elif 'date' in col.lower() and 'birth' in col.lower():
                    anonymized_df[col] = self._anonymize_dob(df[col])
                    pii_report["anonymization_applied"][col] = "dob_generalize"
                    
        # Calculate privacy risk score
        if pii_report["detected_columns"]:
            pii_report["risk_score"] = len(pii_report["detected_columns"]) / len(df.columns)
            
        return anonymized_df, pii_report
        
    def _is_potential_pii(self, col_name: str, series: pd.Series) -> bool:
        """Check if a column potentially contains PII."""
        pii_keywords = [
            'name', 'email', 'phone', 'address', 'ssn', 'social',
            'dob', 'birth', 'passport', 'license', 'account',
            'card', 'patient', 'member', 'customer'
        ]
        
        # Check column name
        col_lower = col_name.lower()
        if any(keyword in col_lower for keyword in pii_keywords):
            return True
            
        # Check data patterns
        if series.dtype == 'object':
            sample = series.dropna().head(10)
            # Email pattern
            if sample.str.contains(r'@', na=False).any():
                return True
            # Phone pattern
            if sample.str.contains(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', na=False).any():
                return True
            # SSN pattern
            if sample.str.contains(r'\d{3}-\d{2}-\d{4}', na=False).any():
                return True
                
        return False
        
    def _anonymize_email(self, series: pd.Series) -> pd.Series:
        """Anonymize email addresses."""
        def hash_email(email):
            if pd.isna(email):
                return email
            # Hash the entire email to prevent domain leakage
            full_hash = hashlib.md5(str(email).encode()).hexdigest()[:8]
            # Use generic domain to prevent information leakage
            return f"user_{full_hash}@example.com"
        return series.apply(hash_email)
        
    def _anonymize_phone(self, series: pd.Series) -> pd.Series:
        """Anonymize phone numbers."""
        def mask_phone(phone):
            if pd.isna(phone):
                return phone
            phone_str = str(phone)
            if len(phone_str) >= 10:
                return phone_str[:3] + '-XXX-XX' + phone_str[-2:]
            return 'XXX-XXX-XXXX'
        return series.apply(mask_phone)
        
    def _anonymize_ssn(self, series: pd.Series) -> pd.Series:
        """Anonymize SSN."""
        return series.apply(lambda x: 'XXX-XX-' + str(x)[-4:] if pd.notna(x) and len(str(x)) >= 4 else 'XXX-XX-XXXX')
        
    def _anonymize_name(self, series: pd.Series) -> pd.Series:
        """Anonymize names."""
        return series.apply(lambda x: f"Person_{hashlib.md5(str(x).encode()).hexdigest()[:6]}" if pd.notna(x) else x)
        
    def _anonymize_address(self, series: pd.Series) -> pd.Series:
        """Anonymize addresses."""
        return series.apply(lambda x: "Address_Redacted" if pd.notna(x) else x)
    
    def _anonymize_credit_card(self, series: pd.Series, provider: Optional[str] = None) -> pd.Series:
        """
        Anonymize credit card numbers using test card numbers from various providers.
        
        Args:
            series: Series containing credit card numbers
            provider: Optional specific provider to use (visa, mastercard, amex, etc.)
        """
        import random
        
        # Official test card numbers from various providers
        # These are publicly documented test numbers that will never work in production
        test_cards = {
            'visa': [
                '4242-4242-4242-4242',  # Stripe test card
                '4111-1111-1111-1111',  # Common test card
                '4012-8888-8888-1881',  # Visa test
                '4000-0566-5566-5556',  # Visa debit
            ],
            'mastercard': [
                '5555-5555-5555-4444',  # Mastercard test
                '5200-8282-8282-8210',  # Mastercard debit
                '5105-1051-0510-5100',  # Mastercard prepaid
                '2223-0031-2200-3222',  # Mastercard 2-series
            ],
            'amex': [
                '3782-822463-10005',   # AmEx test
                '3714-496353-98431',   # AmEx test
                '3787-344936-21000',   # AmEx corporate
            ],
            'discover': [
                '6011-1111-1111-1117',  # Discover test
                '6011-0009-9013-9424',  # Discover test
                '6011-5012-3456-7890',  # Discover test
            ],
            'diners': [
                '3056-930902-5904',     # Diners Club
                '3600-666666-6666',     # Diners test
            ],
            'jcb': [
                '3530-1113-3330-0000',  # JCB test
                '3566-0020-2036-0505',  # JCB test
            ],
            'unionpay': [
                '6200-0000-0000-0005',  # UnionPay test
                '6250-9470-0000-0016',  # UnionPay debit
            ]
        }
        
        def get_test_card(card_value):
            if pd.isna(card_value):
                return card_value
            
            # If a specific provider is requested
            if provider and provider.lower() in test_cards:
                return random.choice(test_cards[provider.lower()])
            
            # Otherwise, select from all providers with weighted distribution
            # Visa and Mastercard are more common
            provider_weights = {
                'visa': 0.4,
                'mastercard': 0.3,
                'amex': 0.1,
                'discover': 0.1,
                'diners': 0.03,
                'jcb': 0.03,
                'unionpay': 0.04
            }
            
            selected_provider = random.choices(
                list(provider_weights.keys()),
                weights=list(provider_weights.values())
            )[0]
            
            return random.choice(test_cards[selected_provider])
        
        return series.apply(get_test_card)
        
    def _anonymize_dob(self, series: pd.Series) -> pd.Series:
        """Anonymize date of birth to year only."""
        if pd.api.types.is_datetime64_any_dtype(series):
            return series.dt.year
        return series
        
    def _generate_pattern_id(self, df: pd.DataFrame) -> str:
        """Generate unique pattern ID from data structure."""
        # Create a hash from column names and types
        structure_str = json.dumps({
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "shape": df.shape
        }, sort_keys=True)
        
        pattern_hash = hashlib.sha256(structure_str.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        return f"pattern_{timestamp}_{pattern_hash}"
        
    def _store_pattern(self, pattern_id: str, pattern_data: Dict[str, Any]) -> None:
        """Store learned pattern for future use."""
        # In a real implementation, this would save to a database or file
        # For now, we'll store in memory
        if not hasattr(self, '_pattern_store'):
            self._pattern_store = {}
        self._pattern_store[pattern_id] = pattern_data
        
    def get_stored_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored pattern by ID."""
        if hasattr(self, '_pattern_store'):
            return self._pattern_store.get(pattern_id)
        return None
        
    def list_stored_patterns(self) -> List[str]:
        """List all stored pattern IDs."""
        if hasattr(self, '_pattern_store'):
            return list(self._pattern_store.keys())
        return []