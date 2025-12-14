"""
Core synthetic data generation engine using DSPy framework.

This module implements the main data generation logic using DSPy's language model
programming capabilities with domain-specific knowledge and validation.
"""

import json
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, Union
from uuid import uuid4

import numpy as np
import pandas as pd
from faker import Faker
from loguru import logger
from pydantic import BaseModel

# Make dspy optional to avoid dependency conflicts
try:
    import dspy
    USE_DSPY = True
except (ImportError, AttributeError) as e:
    logger.warning(f"DSPy not available or has dependency issues: {e}")
    logger.info("Falling back to non-DSPy generation methods")
    USE_DSPY = False

from ..schemas.base import DataDomain, PrivacyLevel
from ..schemas.healthcare import (
    PatientRecord, ClinicalTrial, HealthcareClaim,
    PatientDemographics, Gender, Race, InsuranceType, AdmissionType, DischargeDisposition
)
from ..schemas.finance import (
    Transaction, CreditRecord, TradingData,
    CustomerDemographics, TransactionType, TransactionCategory
)
from ..ingestion.knowledge_loader import DynamicKnowledgeLoader
from ..ingestion.pattern_analyzer import PatternAnalyzer


if USE_DSPY:
    class HealthcareDataSignature(dspy.Signature):
        """DSPy signature for healthcare data generation."""
        
        domain_context = dspy.InputField(desc="Healthcare domain context and requirements")
        data_type = dspy.InputField(desc="Specific healthcare data type to generate")
        patient_profile = dspy.InputField(desc="Patient demographic and clinical profile")
        compliance_requirements = dspy.InputField(desc="HIPAA and regulatory compliance requirements")
        
        synthetic_record = dspy.OutputField(desc="Generated synthetic healthcare record in JSON format")
        compliance_notes = dspy.OutputField(desc="Notes on compliance and privacy protection applied")


    class FinanceDataSignature(dspy.Signature):
        """DSPy signature for financial data generation."""
        
        domain_context = dspy.InputField(desc="Financial domain context and requirements")
        data_type = dspy.InputField(desc="Specific financial data type to generate")
        customer_profile = dspy.InputField(desc="Customer demographic and financial profile")
        compliance_requirements = dspy.InputField(desc="SOX, PCI DSS and regulatory compliance requirements")
        
        synthetic_record = dspy.OutputField(desc="Generated synthetic financial record in JSON format")
        compliance_notes = dspy.OutputField(desc="Notes on compliance and privacy protection applied")


    class SchemaGenerationSignature(dspy.Signature):
        """DSPy signature for generating domain schemas."""
        
        domain = dspy.InputField(desc="Target domain (healthcare, finance, custom)")
        data_type = dspy.InputField(desc="Specific data structure type")
        compliance_requirements = dspy.InputField(desc="Required compliance frameworks")
        existing_schemas = dspy.InputField(desc="Existing schema examples for reference")
        
        schema_definition = dspy.OutputField(desc="Generated Pydantic schema definition")
        validation_rules = dspy.OutputField(desc="Compliance validation rules")
        field_descriptions = dspy.OutputField(desc="Detailed field descriptions and constraints")


class SyntheticDataGenerator:
    """Main synthetic data generation engine."""
    
    def __init__(self):
        """Initialize the generator with DSPy modules and Faker."""
        self.faker = Faker()
        Faker.seed(0)  # For reproducible synthetic data
        
        # Initialize Ollama config
        self.ollama_config = None
        
        # Configure DSPy with a language model or fallback
        if USE_DSPY:
            self.use_llm = self._configure_dspy()
            
            # Initialize DSPy modules
            self.healthcare_generator = dspy.ChainOfThought(HealthcareDataSignature)
            self.finance_generator = dspy.ChainOfThought(FinanceDataSignature)
            self.schema_generator = dspy.ChainOfThought(SchemaGenerationSignature)
        else:
            self.use_llm = False
            self.healthcare_generator = None
            self.finance_generator = None
            self.schema_generator = None
            logger.info("DSPy disabled - using fallback generation methods")
        
        # Initialize dynamic knowledge loader instead of hardcoded knowledge
        self.knowledge_loader = DynamicKnowledgeLoader()
        self.pattern_analyzer = PatternAnalyzer()
        
        # Pattern storage for learned patterns
        self.learned_patterns = {}
        
        # Load dynamic knowledge (not hardcoded)
        self.healthcare_knowledge = self.knowledge_loader.get_healthcare_knowledge()
        self.finance_knowledge = self.knowledge_loader.get_finance_knowledge()
        
        logger.info("Synthetic Data Generator initialized with dynamic knowledge loading")
    
    def _configure_dspy(self) -> bool:
        """Configure DSPy with available LM or fallback mode."""
        
        # Priority 1: Try Ollama (fully private local inference)
        if self._try_configure_ollama():
            return True
            
        # Priority 2: Try OpenAI (cloud-based)
        if self._try_configure_openai():
            return True
            
        # Priority 3: Fallback to mock for testing
        return self._configure_fallback_mock()
    
    def _try_configure_ollama(self) -> bool:
        """Try to configure DSPy with Ollama server."""
        try:
            # Check for Ollama configuration
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Test if Ollama server is available and get available models
            import requests
            response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    # Select the best available model
                    model_preferences = [
                        'mistral-small3.2:latest',
                        'mistral-small3.1:latest', 
                        'qwen3:14b-q8_0',
                        'llama3.1:8b-instruct-q8_0',
                        'mistral:7b-instruct-v0.3-q8_0',
                        'mistral:instruct'
                    ]
                    
                    available_model_names = [m['name'] for m in models]
                    selected_model = None
                    
                    # Find the first preferred model that's available
                    for pref_model in model_preferences:
                        if pref_model in available_model_names:
                            selected_model = pref_model
                            break
                    
                    # If no preferred model found, use the first available
                    if not selected_model and available_model_names:
                        selected_model = available_model_names[0]
                    
                    if selected_model:
                        ollama_model = os.getenv("OLLAMA_MODEL", selected_model)
                        logger.info(f"✅ Ollama server detected - Using model: {ollama_model}")
                        logger.info(f"🔒 Privacy Mode: FULLY LOCAL INFERENCE")
                        
                        # Configure DSPy with Ollama
                        if USE_DSPY:
                            try:
                                # Use OpenAI-compatible endpoint for Ollama
                                lm = dspy.LM(
                                    model=f'ollama/{ollama_model}',
                                    api_base=ollama_base_url,
                                    api_key='ollama',  # Ollama doesn't need a real key
                                    max_tokens=2000,
                                    temperature=0.7
                                )
                                dspy.settings.configure(lm=lm)
                                logger.info(f"✅ DSPy configured with Ollama model: {ollama_model}")
                                return True
                            except Exception as e:
                                logger.warning(f"DSPy-Ollama integration failed, using direct Ollama: {e}")
                                # Store Ollama config for direct use
                                self.ollama_config = {
                                    'base_url': ollama_base_url,
                                    'model': ollama_model
                                }
                                return True
                    
            else:
                logger.debug(f"Ollama server not available at {ollama_base_url}")
                
        except requests.exceptions.RequestException:
            logger.debug("Ollama server not accessible")
        except Exception as e:
            logger.debug(f"Ollama configuration failed: {e}")
            
        return False
    
    def _try_configure_openai(self) -> bool:
        """Try to configure DSPy with OpenAI."""
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            # Only try OpenAI if we have a valid key and it starts with 'sk-'
            if openai_key and openai_key.startswith("sk-") and len(openai_key) > 20:
                # Test the key is valid with a simple request
                import openai
                try:
                    client = openai.OpenAI(api_key=openai_key)
                    # Simple test to validate key
                    response = client.models.list()
                    
                    # If we get here, the key works
                    if USE_DSPY:
                        lm = dspy.LM(
                            model='gpt-4',
                            api_key=openai_key,
                            max_tokens=2000,
                            temperature=0.7
                        )
                        dspy.settings.configure(lm=lm)
                    logger.info("DSPy configured with OpenAI GPT-4")
                    logger.warning("⚠️  Privacy Mode: CLOUD INFERENCE (OpenAI)")
                    return True
                except openai.AuthenticationError:
                    logger.debug("OpenAI API key is invalid")
                except Exception as e:
                    logger.debug(f"OpenAI API test failed: {e}")
            else:
                logger.debug("No valid OpenAI API key found")
        except Exception as e:
            logger.warning(f"Failed to configure OpenAI: {e}")
        return False
    
    def _call_ollama_direct(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """Call Ollama directly for generation when DSPy doesn't work."""
        if not self.ollama_config:
            # Fallback to basic generation
            return {
                "generated": True,
                "data": self._generate_fallback_record()
            }
        
        try:
            import requests
            
            url = f"{self.ollama_config['base_url']}/api/generate"
            
            # Prepare the prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.ollama_config['model'],
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                
                # Try to parse JSON from the response
                import re
                json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        return {
                            "generated": True,
                            "data": data,
                            "model": self.ollama_config['model']
                        }
                    except json.JSONDecodeError:
                        pass
                
                # If no JSON found, return the text response
                return {
                    "generated": True,
                    "text": generated_text,
                    "model": self.ollama_config['model']
                }
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                return {
                    "generated": False,
                    "error": f"Ollama API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.warning(f"Direct Ollama call failed: {e}")
            return {
                "generated": False,
                "error": str(e)
            }
    
    def _generate_fallback_record(self) -> Dict[str, Any]:
        """Generate a basic fallback record using Faker."""
        return {
            "id": str(uuid4()),
            "name": self.faker.name(),
            "email": self.faker.email(),
            "phone": self.faker.phone_number(),
            "address": self.faker.address(),
            "created_at": datetime.now().isoformat(),
            "value": self.faker.random_int(min=100, max=10000),
            "category": self.faker.random_element(['A', 'B', 'C', 'D']),
            "description": self.faker.text(max_nb_chars=100)
        }
    
    def _configure_fallback_mock(self) -> bool:
        """Configure fallback for when no LLM is available."""
        logger.info("No LLM provider configured - using Faker-based generation")
        logger.info("🔧 Fallback Mode: LOCAL GENERATION (No LLM)")
        return False
    
    async def learn_from_data(
        self,
        data_samples: Union[List[Dict], pd.DataFrame],
        domain: str = "custom"
    ) -> str:
        """
        Learn patterns from user-provided real data.
        
        Args:
            data_samples: Real data samples to learn from
            domain: Domain category (healthcare, finance, custom)
            
        Returns:
            Pattern ID for future generation
        """
        import pandas as pd
        
        # Learn patterns using the pattern analyzer
        pattern_summary = self.pattern_analyzer.generate_pattern_summary(data_samples)
        
        # Store in knowledge loader
        knowledge = self.knowledge_loader.load_from_samples(data_samples, domain)
        
        # Generate unique pattern ID
        pattern_id = f"pattern_{domain}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Store the learned pattern
        self.learned_patterns[pattern_id] = {
            "domain": domain,
            "pattern_summary": pattern_summary,
            "knowledge": knowledge,
            "sample_count": len(data_samples) if isinstance(data_samples, list) else len(data_samples)
        }
        
        # Update domain knowledge
        if domain == "healthcare":
            self.healthcare_knowledge = knowledge
        elif domain == "finance":
            self.finance_knowledge = knowledge
            
        logger.info(f"Learned patterns from {len(data_samples)} samples, pattern ID: {pattern_id}")
        return pattern_id
        
    def register_pattern(self, pattern_id: str, pattern_data: Dict[str, Any]) -> None:
        """Register a learned pattern for later use."""
        self.learned_patterns[pattern_id] = pattern_data
        logger.info(f"Registered pattern: {pattern_id}")
    
    async def generate_from_pattern(
        self,
        pattern_id: str,
        record_count: int,
        variation: float = 0.3,
        privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM
    ) -> Dict[str, Any]:
        """
        Generate synthetic data based on previously learned patterns.
        
        Args:
            pattern_id: ID of the learned pattern
            record_count: Number of records to generate
            variation: Amount of variation (0.0-1.0)
            privacy_level: Privacy protection level
            
        Returns:
            Generated synthetic dataset
        """
        if pattern_id not in self.learned_patterns:
            # Try to return a simple response with generated data if pattern not found
            logger.warning(f"Pattern ID {pattern_id} not found, generating default data")
            return {"data": [], "error": f"Pattern ID {pattern_id} not found"}
            
        pattern_info = self.learned_patterns[pattern_id]
        pattern_summary = pattern_info["pattern_summary"]
        knowledge = pattern_info["knowledge"]
        
        # Generate data based on learned patterns
        synthetic_data = []
        
        for i in range(record_count):
            record = {}
            
            # Generate each field based on learned distributions
            for col_name, distribution in pattern_summary.get("distributions", {}).items():
                if distribution.get("type") == "numeric":
                    # Generate numeric value based on learned distribution
                    mean = distribution.get("mean", 0)
                    std = distribution.get("std", 1) * variation
                    value = np.random.normal(mean, std)
                    record[col_name] = float(value)
                    
                elif distribution.get("type") == "categorical":
                    # Generate categorical value based on learned frequencies
                    frequencies = distribution.get("frequencies", {})
                    if frequencies:
                        values = list(frequencies.keys())
                        probabilities = list(frequencies.values())
                        value = np.random.choice(values, p=probabilities)
                        record[col_name] = value
                    else:
                        record[col_name] = f"synthetic_{i}"
                        
                elif distribution.get("type") == "temporal":
                    # Generate temporal value based on learned patterns
                    min_date = distribution.get("min_date", datetime.now())
                    max_date = distribution.get("max_date", datetime.now())
                    record[col_name] = self.faker.date_time_between(
                        start_date=min_date, 
                        end_date=max_date
                    ).isoformat()
                    
                else:
                    # Default generation
                    record[col_name] = self.faker.text(max_nb_chars=50)
                    
            synthetic_data.append(record)
            
        return {
            "success": True,
            "pattern_id": pattern_id,
            "records_generated": record_count,
            "data": synthetic_data,
            "metadata": {
                "variation": variation,
                "privacy_level": privacy_level.value,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    async def generate_dataset(
        self,
        domain: DataDomain,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate synthetic dataset for specified domain and type.
        
        Args:
            domain: Target data domain
            dataset_type: Specific data type to generate
            record_count: Number of records to generate
            privacy_level: Privacy protection level
            custom_schema: Optional custom schema definition
            seed: Random seed for reproducibility
            
        Returns:
            Structured response with status, metadata, and dataset
        """
        try:
            if seed:
                random.seed(seed)
                self.faker.seed_instance(seed)
            
            logger.info(f"Generating {record_count} {dataset_type} records for {domain} domain")
            
            # Generate records based on domain
            if domain == DataDomain.HEALTHCARE:
                records = await self._generate_healthcare_dataset(
                    dataset_type, record_count, privacy_level, custom_schema
                )
            elif domain == DataDomain.FINANCE:
                records = await self._generate_finance_dataset(
                    dataset_type, record_count, privacy_level, custom_schema
                )
            else:
                records = await self._generate_custom_dataset(
                    dataset_type, record_count, privacy_level, custom_schema
                )
            
            # Return structured response
            return {
                "status": "success",
                "metadata": {
                    "total_records": len(records),
                    "domain": domain.value if hasattr(domain, 'value') else str(domain),
                    "dataset_type": dataset_type,
                    "privacy_level": privacy_level.value if hasattr(privacy_level, 'value') else str(privacy_level),
                    "generated_at": datetime.now().isoformat(),
                    "inference_mode": "local" if self.use_llm else "fallback"
                },
                "dataset": records
            }
            
        except Exception as e:
            logger.error(f"Failed to generate dataset: {e}")
            return {
                "status": "error",
                "error": str(e),
                "metadata": {
                    "total_records": 0,
                    "domain": domain.value if hasattr(domain, 'value') else str(domain),
                    "dataset_type": dataset_type,
                    "privacy_level": privacy_level.value if hasattr(privacy_level, 'value') else str(privacy_level),
                    "generated_at": datetime.now().isoformat(),
                    "inference_mode": "local" if self.use_llm else "fallback"
                },
                "dataset": []
            }
    
    async def _generate_healthcare_dataset(
        self,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate healthcare-specific datasets."""
        
        if dataset_type == "patient_records":
            return await self._generate_patient_records(record_count, privacy_level)
        elif dataset_type == "clinical_trials":
            return await self._generate_clinical_trials(record_count, privacy_level)
        elif dataset_type == "medical_claims":
            return await self._generate_medical_claims(record_count, privacy_level)
        else:
            # Use DSPy for custom healthcare data types
            return await self._generate_with_dspy(
                domain="healthcare",
                dataset_type=dataset_type,
                record_count=record_count,
                privacy_level=privacy_level,
                custom_schema=custom_schema
            )
    
    async def _generate_finance_dataset(
        self,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate finance-specific datasets."""
        
        if dataset_type == "transaction_records":
            return await self._generate_transactions(record_count, privacy_level)
        elif dataset_type == "credit_assessments":
            return await self._generate_credit_records(record_count, privacy_level)
        elif dataset_type == "trading_data":
            return await self._generate_trading_data(record_count, privacy_level)
        else:
            # Use DSPy for custom financial data types
            return await self._generate_with_dspy(
                domain="finance",
                dataset_type=dataset_type,
                record_count=record_count,
                privacy_level=privacy_level,
                custom_schema=custom_schema
            )
    
    async def _generate_patient_records(
        self, record_count: int, privacy_level: PrivacyLevel
    ) -> List[Dict[str, Any]]:
        """Generate synthetic patient records."""
        records = []
        
        for _ in range(record_count):
            # Generate demographics with privacy protection
            demographics = self._generate_patient_demographics(privacy_level)
            
            # Generate medical conditions based on age and demographics
            conditions = self._generate_medical_conditions(demographics["age_group"])
            
            # Generate encounters based on conditions
            encounters = self._generate_encounters(conditions, demographics)
            
            # Create patient record
            record = PatientRecord(
                demographics=PatientDemographics(**demographics),
                insurance_type=self.faker.random_element(elements=list(InsuranceType)),
                conditions=conditions,
                encounters=encounters,
                comorbidity_count=len(conditions),
                total_encounters=len(encounters),
                total_cost=sum(enc.get("total_charges", 0) if isinstance(enc, dict) else getattr(enc, "total_charges", 0) for enc in encounters),
                first_encounter_days_ago=self.faker.random_int(min=30, max=1095),
                last_encounter_days_ago=self.faker.random_int(min=0, max=30),
                vital_status="alive"
            )
            
            records.append(record.dict())
        
        return records
    
    async def _generate_transactions(
        self, record_count: int, privacy_level: PrivacyLevel
    ) -> List[Dict[str, Any]]:
        """Generate synthetic transaction records."""
        records = []
        
        # Generate base accounts for transaction patterns
        # Ensure at least 1 account even for small record counts
        num_accounts = max(1, record_count // 20)
        account_ids = [f"ACCT_{uuid4().hex[:8].upper()}" for _ in range(num_accounts)]
        
        for _ in range(record_count):
            # Generate transaction with realistic patterns
            account_id = self.faker.random_element(elements=account_ids)
            
            # Generate amount based on category and privacy level
            category = self.faker.random_element(elements=list(TransactionCategory))
            amount = self._generate_transaction_amount(category, privacy_level)
            
            # Generate transaction with temporal patterns
            transaction_date = self.faker.date_between(start_date='-1y', end_date='today')
            
            record = Transaction(
                transaction_id=f"TXN_{uuid4().hex[:8].upper()}",
                account_id=account_id,
                transaction_date=transaction_date,
                post_date=transaction_date + timedelta(days=self.faker.random_int(0, 2)),
                transaction_type=self.faker.random_element(elements=list(TransactionType)),
                category=category,
                amount=Decimal(str(amount)),
                amount_range=self._categorize_amount(amount),
                merchant_category=self._get_merchant_category(category),
                merchant_location_zip3=self.faker.zipcode()[:3],
                merchant_location_state=self.faker.state_abbr(),
                payment_method=self.faker.random_element(elements=[
                    "debit_card", "credit_card", "ach", "online"
                ]),
                transaction_zip3=self.faker.zipcode()[:3],
                transaction_state=self.faker.state_abbr(),
                fraud_score=self._generate_fraud_score(category, amount),
                is_fraud=False,  # Will be set based on fraud_score
                hour_of_day=self._generate_transaction_hour(category),
                day_of_week=transaction_date.weekday(),
                day_of_month=transaction_date.day,
                balance_after_range=self._generate_balance_range(privacy_level)
            )
            
            # Set fraud flag based on score
            record.is_fraud = record.fraud_score > 0.8
            
            records.append(record.dict())
        
        return records
    
    def _generate_patient_demographics(self, privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """Generate patient demographics with appropriate privacy protection."""
        age = self.faker.random_int(min=18, max=89)
        
        return {
            "age_group": self._get_age_group(age),
            "gender": self.faker.random_element(elements=list(Gender)),
            "race": self.faker.random_element(elements=list(Race)),
            "zip_code_3digit": self.faker.zipcode()[:3] if privacy_level != PrivacyLevel.MAXIMUM else None,
            "state": self.faker.state_abbr() if privacy_level != PrivacyLevel.MAXIMUM else None
        }
    
    def _generate_medical_conditions(self, age_group: str) -> List[Dict[str, Any]]:
        """Generate medical conditions based on age group and prevalence."""
        conditions = []
        
        # Get age-appropriate conditions
        age_conditions = self.healthcare_knowledge["age_condition_correlation"].get(age_group, [])
        common_conditions = self.healthcare_knowledge["common_conditions"]
        
        # Randomly select 0-3 conditions based on age
        num_conditions = self.faker.random_int(min=0, max=3)
        
        for _ in range(num_conditions):
            condition = self.faker.random_element(elements=common_conditions)
            conditions.append({
                "icd10_code": condition["icd10"],
                "description": condition["name"],
                "severity": self.faker.random_element(elements=["mild", "moderate", "severe"]),
                "onset_date": self.faker.date_between(start_date='-5y', end_date='-30d'),
                "status": self.faker.random_element(elements=["active", "resolved", "chronic"])
            })
        
        return conditions
    
    def _generate_encounters(self, conditions: List[Dict], demographics: Dict) -> List[Dict]:
        """Generate healthcare encounters based on conditions."""
        encounters = []
        
        # Generate 1-5 encounters based on condition severity
        num_encounters = max(1, len(conditions) + self.faker.random_int(-1, 2))
        
        for _ in range(num_encounters):
            admission_date = self.faker.date_between(start_date='-1y', end_date='today')
            encounter_type = self.faker.random_element(elements=[
                "outpatient", "inpatient", "emergency"
            ])
            
            # Generate admission_type based on encounter_type
            if encounter_type == "emergency":
                admission_type = self.faker.random_element(elements=[
                    AdmissionType.EMERGENCY, AdmissionType.TRAUMA, AdmissionType.URGENT
                ])
            elif encounter_type == "inpatient":
                admission_type = self.faker.random_element(elements=[
                    AdmissionType.ELECTIVE, AdmissionType.URGENT, AdmissionType.EMERGENCY
                ])
            else:  # outpatient
                admission_type = AdmissionType.ELECTIVE
            
            # Generate discharge_disposition based on encounter_type and severity
            if encounter_type == "emergency":
                # Use random.choices for weighted selection
                import random
                discharge_disposition = random.choices(
                    population=[
                        DischargeDisposition.HOME, DischargeDisposition.HOME_WITH_SERVICES,
                        DischargeDisposition.TRANSFER, DischargeDisposition.SNF
                    ],
                    weights=[0.6, 0.2, 0.15, 0.05]
                )[0]
            elif encounter_type == "inpatient":
                import random
                discharge_disposition = random.choices(
                    population=[
                        DischargeDisposition.HOME, DischargeDisposition.HOME_WITH_SERVICES,
                        DischargeDisposition.SNF, DischargeDisposition.REHABILITATION
                    ],
                    weights=[0.7, 0.15, 0.1, 0.05]
                )[0]
            else:  # outpatient
                discharge_disposition = DischargeDisposition.HOME
            
            encounter = {
                "encounter_type": encounter_type,
                "admission_date": admission_date,
                "discharge_date": admission_date + timedelta(days=self.faker.random_int(0, 7)),
                "length_of_stay": self.faker.random_int(min=1, max=7),
                "admission_type": admission_type,
                "discharge_disposition": discharge_disposition,
                "primary_diagnosis": conditions[0]["icd10_code"] if conditions else "Z00.00",
                "secondary_diagnoses": [c["icd10_code"] for c in conditions[1:3]],
                "total_charges": Decimal(str(self.faker.random_int(min=500, max=50000)))
            }
            
            encounters.append(encounter)
        
        return encounters
    
    def _generate_transaction_amount(self, category: TransactionCategory, privacy_level: PrivacyLevel) -> float:
        """Generate realistic transaction amounts based on category."""
        
        # Category-based amount ranges
        amount_ranges = {
            TransactionCategory.GROCERIES: (20, 200),
            TransactionCategory.RESTAURANTS: (15, 150),
            TransactionCategory.GAS_FUEL: (25, 100),
            TransactionCategory.RETAIL: (30, 500),
            TransactionCategory.UTILITIES: (50, 300),
            TransactionCategory.HEALTHCARE: (25, 1000),
            TransactionCategory.TRAVEL: (100, 2000),
            TransactionCategory.ENTERTAINMENT: (20, 200),
            TransactionCategory.EDUCATION: (100, 5000),
            TransactionCategory.INSURANCE: (100, 1000)
        }
        
        min_amt, max_amt = amount_ranges.get(category, (10, 100))
        amount = self.faker.random_int(min=min_amt, max=max_amt)
        
        # Add some randomness
        amount *= self.faker.random.uniform(0.7, 1.3)
        
        # Apply privacy level adjustments
        if privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM]:
            # Round to nearest $5 or $10 to reduce precision
            amount = round(amount / 10) * 10
        
        return round(amount, 2)
    
    def _categorize_amount(self, amount: float) -> str:
        """Categorize amount into ranges for privacy."""
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
        else:
            return "5k+"
    
    def _generate_fraud_score(self, category: TransactionCategory, amount: float) -> float:
        """Generate fraud score based on transaction characteristics."""
        base_score = 0.1
        
        # Category-based risk
        high_risk_categories = [
            TransactionCategory.CASH_ATM,
            TransactionCategory.GAS_FUEL,
            TransactionCategory.RETAIL
        ]
        
        if category in high_risk_categories:
            base_score += 0.2
        
        # Amount-based risk
        if amount > 1000:
            base_score += 0.3
        elif amount < 5:
            base_score += 0.4  # Micro-transactions can be testing
        
        # Add randomness
        score = base_score + self.faker.random.uniform(-0.1, 0.3)
        
        return max(0.0, min(1.0, score))
    
    def _generate_transaction_hour(self, category: TransactionCategory) -> int:
        """Generate realistic transaction hour based on category."""
        
        # Category-specific hour patterns
        if category == TransactionCategory.GROCERIES:
            # Peak at lunch and evening
            return self.faker.random_element(elements=list(range(11, 14)) + list(range(17, 20)))
        elif category == TransactionCategory.RESTAURANTS:
            # Peak at meal times
            return self.faker.random_element(elements=list(range(11, 14)) + list(range(17, 22)))
        elif category == TransactionCategory.GAS_FUEL:
            # More spread out but peak during commute
            return self.faker.random_element(elements=list(range(7, 9)) + list(range(17, 19)) + list(range(10, 16)))
        else:
            # General business hours
            return self.faker.random_int(min=8, max=20)
    
    def _get_merchant_category(self, category: TransactionCategory) -> str:
        """Get merchant category code equivalent."""
        category_mapping = {
            TransactionCategory.GROCERIES: "grocery_stores",
            TransactionCategory.RESTAURANTS: "restaurants",
            TransactionCategory.GAS_FUEL: "gas_stations",
            TransactionCategory.RETAIL: "retail_stores",
            TransactionCategory.UTILITIES: "utilities",
            TransactionCategory.HEALTHCARE: "medical_services",
            TransactionCategory.TRANSPORTATION: "transportation",
            TransactionCategory.ENTERTAINMENT: "entertainment"
        }
        
        return category_mapping.get(category, "miscellaneous")
    
    def _generate_balance_range(self, privacy_level: PrivacyLevel) -> str:
        """Generate account balance range for privacy."""
        balance = self.faker.random_int(min=100, max=50000)
        
        if balance < 500:
            return "0-500"
        elif balance < 2000:
            return "500-2k"
        elif balance < 10000:
            return "2k-10k"
        elif balance < 25000:
            return "10k-25k"
        else:
            return "25k+"
    
    def _get_age_group(self, age: int) -> str:
        """Convert age to HIPAA-compliant age group."""
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
    
    async def _generate_with_dspy(
        self,
        domain: str,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate data using LLM (DSPy or Ollama) for custom or complex data types."""
        
        # If we have Ollama configured but DSPy isn't working, use Ollama directly
        if self.ollama_config and not self.use_llm:
            return await self._generate_with_ollama(
                domain, dataset_type, record_count, privacy_level, custom_schema
            )
        
        # If no LLM is available at all, use fallback generation
        if not self.use_llm and not self.ollama_config:
            return await self._generate_fallback_data(
                domain, dataset_type, record_count, privacy_level, custom_schema
            )
        
        records = []
        
        # Generate records using DSPy
        for i in range(record_count):
            if domain == "healthcare":
                # Generate healthcare record with DSPy
                context = f"Healthcare domain: {dataset_type}, Record {i+1}/{record_count}"
                patient_profile = self._get_random_patient_profile()
                compliance_req = f"HIPAA Safe Harbor compliance, Privacy level: {privacy_level}"
                
                try:
                    result = self.healthcare_generator(
                        domain_context=context,
                        data_type=dataset_type,
                        patient_profile=patient_profile,
                        compliance_requirements=compliance_req
                    )
                    
                    record_data = json.loads(result.synthetic_record)
                    records.append(record_data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to generate with DSPy: {e}")
                    # Use fallback for this record
                    fallback_record = await self._generate_single_fallback_record(
                        domain, dataset_type, i
                    )
                    records.append(fallback_record)
            
            elif domain == "finance":
                # Generate financial record with DSPy
                context = f"Financial domain: {dataset_type}, Record {i+1}/{record_count}"
                customer_profile = self._get_random_customer_profile()
                compliance_req = f"SOX and PCI DSS compliance, Privacy level: {privacy_level}"
                
                result = self.finance_generator(
                    domain_context=context,
                    data_type=dataset_type,
                    customer_profile=customer_profile,
                    compliance_requirements=compliance_req
                )
                
                try:
                    record_data = json.loads(result.synthetic_record)
                    records.append(record_data)
                except json.JSONDecodeError:
                    # Handle decode error - use fallback record
                    logger.warning(f"Failed to parse DSPy output for finance record {i+1}")
                    fallback_record = await self._generate_single_fallback_record(
                        domain, dataset_type, i
                    )
                    records.append(fallback_record)
        
        return records
    
    async def _generate_with_ollama(
        self,
        domain: str,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate data using Ollama directly."""
        records = []
        
        # Create system prompt based on domain
        if domain == "healthcare":
            system_prompt = """You are a synthetic healthcare data generator. 
Generate realistic patient records with HIPAA compliance.
Return data as valid JSON objects with fields appropriate for healthcare records.
Include demographics, conditions, encounters, and insurance information."""
        elif domain == "finance":
            system_prompt = """You are a synthetic financial data generator.
Generate realistic financial transactions with PCI DSS compliance.
Return data as valid JSON objects with fields appropriate for financial records.
Include transaction IDs, amounts, dates, categories, and merchant information."""
        else:
            system_prompt = """You are a synthetic data generator.
Generate realistic data records based on the requested type.
Return data as valid JSON objects."""
        
        for i in range(record_count):
            prompt = f"""Generate a synthetic {dataset_type} record (#{i+1}).
Privacy level: {privacy_level.value}
Domain: {domain}

Return a single JSON object with realistic, synthetic data.
Important: Return ONLY the JSON object, no explanation or markdown."""
            
            result = self._call_ollama_direct(prompt, system_prompt)
            
            if result.get("generated"):
                if "data" in result and isinstance(result["data"], dict):
                    records.append(result["data"])
                else:
                    # Generate fallback if Ollama didn't return proper JSON
                    fallback_record = await self._generate_single_fallback_record(
                        domain, dataset_type, i
                    )
                    records.append(fallback_record)
            else:
                # Use fallback if Ollama failed
                fallback_record = await self._generate_single_fallback_record(
                    domain, dataset_type, i
                )
                records.append(fallback_record)
        
        logger.info(f"Generated {len(records)} records using Ollama model: {self.ollama_config.get('model')}")
        return records
    
    def _get_random_patient_profile(self) -> str:
        """Generate a random patient profile for DSPy context."""
        demographics = self._generate_patient_demographics(PrivacyLevel.MEDIUM)
        return f"Patient: {demographics['age_group']} years old, {demographics['gender']}, {demographics['race']}, {demographics['state']}"
    
    def _get_random_customer_profile(self) -> str:
        """Generate a random customer profile for DSPy context."""
        age_group = self.faker.random_element(elements=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"])
        income = self.faker.random_element(elements=["25k-50k", "50k-75k", "75k-100k", "100k+"])
        return f"Customer: {age_group} years old, Income: {income}, {self.faker.state_abbr()}"
    
    async def generate_schema(
        self,
        domain: DataDomain,
        data_type: str,
        compliance_requirements: List[str],
        custom_fields: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate Pydantic schema for custom data types."""
        
        # Use DSPy to generate schema
        existing_schemas = self._get_example_schemas(domain)
        
        result = self.schema_generator(
            domain=str(domain),
            data_type=data_type,
            compliance_requirements=", ".join(compliance_requirements),
            existing_schemas=existing_schemas
        )
        
        return {
            "schema": result.schema_definition,
            "validation_rules": result.validation_rules,
            "field_descriptions": result.field_descriptions,
            "examples": [],
            "documentation": f"Generated schema for {domain} {data_type}"
        }
    
    def _get_example_schemas(self, domain: DataDomain) -> str:
        """Get example schemas for DSPy context."""
        if domain == DataDomain.HEALTHCARE:
            return "Examples: PatientRecord, ClinicalTrial, HealthcareClaim with HIPAA compliance"
        elif domain == DataDomain.FINANCE:
            return "Examples: Transaction, CreditRecord, TradingData with SOX/PCI DSS compliance"
        else:
            return "Custom domain schemas with privacy protection"
    
    async def _generate_custom_dataset(
        self,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate custom dataset based on provided schema."""
        
        records = []
        
        for _ in range(record_count):
            # Generate basic record structure
            record = {
                "id": str(uuid4()),
                "created_at": datetime.now().isoformat(),
                "synthetic": True,
                "type": dataset_type,
                "privacy_level": str(privacy_level)
            }
            
            # Add custom fields if schema provided
            if custom_schema:
                for field_name, field_def in custom_schema.get("properties", {}).items():
                    record[field_name] = self._generate_field_value(field_def)
            
            records.append(record)
        
        return records
    
    def _generate_field_value(self, field_def: Dict[str, Any]) -> Any:
        """Generate value for custom field based on definition."""
        field_type = field_def.get("type", "string")
        
        if field_type == "string":
            return self.faker.word()
        elif field_type == "integer":
            return self.faker.random_int(min=1, max=1000)
        elif field_type == "number":
            return round(self.faker.random.uniform(0.0, 1000.0), 2)
        elif field_type == "boolean":
            return self.faker.boolean()
        elif field_type == "array":
            return [self.faker.word() for _ in range(self.faker.random_int(1, 5))]
        else:
            return None
    
    async def _generate_fallback_data(
        self,
        domain: str,
        dataset_type: str,
        record_count: int,
        privacy_level: PrivacyLevel,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate synthetic data using Faker when DSPy/LLM is not available."""
        if domain == "healthcare":
            return await self._generate_patient_records(record_count, privacy_level)
        elif domain == "finance":
            return await self._generate_transactions(record_count, privacy_level)
        elif domain == "custom" and custom_schema:
            return await self._generate_custom_dataset(dataset_type, record_count, privacy_level, custom_schema)
        else:
            # Generic fallback
            records = []
            for i in range(record_count):
                record = {
                    "id": str(uuid4()),
                    "name": self.faker.name(),
                    "email": self.faker.email(),
                    "created_at": self.faker.date_time_this_year().isoformat(),
                    "value": round(random.uniform(0, 1000), 2)
                }
                records.append(record)
            return records
    
    async def _generate_single_fallback_record(
        self,
        domain: str,
        dataset_type: str,
        index: int
    ) -> Dict[str, Any]:
        """Generate a single fallback record."""
        if domain == "healthcare":
            return {
                "patient_id": f"P{100000 + index}",
                "name": self.faker.name(),
                "dob": self.faker.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
                "gender": random.choice(["Male", "Female", "Other"]),
                "diagnosis": random.choice(["Hypertension", "Diabetes", "Asthma", "Healthy"]),
                "treatment": random.choice(["Medication", "Therapy", "Surgery", "None"])
            }
        elif domain == "finance":
            return {
                "transaction_id": str(uuid4()),
                "account": f"ACC{random.randint(100000, 999999)}",
                "amount": round(random.uniform(10, 10000), 2),
                "type": random.choice(["deposit", "withdrawal", "transfer", "payment"]),
                "timestamp": self.faker.date_time_this_year().isoformat()
            }
        else:
            return {
                "id": str(uuid4()),
                "type": dataset_type,
                "value": f"fallback_{index}",
                "synthetic": True
            }
    
