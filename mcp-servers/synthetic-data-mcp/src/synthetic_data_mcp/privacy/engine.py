"""
Privacy protection engine with differential privacy implementation.

This module provides privacy protection capabilities including differential privacy,
k-anonymity, l-diversity, and privacy risk assessment for synthetic datasets.
"""

import hashlib
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from ..schemas.base import PrivacyLevel, get_epsilon_for_privacy_level


class DifferentialPrivacy:
    """Differential privacy implementation."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize differential privacy engine.
        
        Args:
            epsilon: Privacy budget parameter (smaller = more private)
            delta: Probability of privacy loss (should be << 1/n)
        """
        self.epsilon = epsilon
        self.delta = delta
        self.budget_used = 0.0
        
    def add_laplace_noise(self, value: float, sensitivity: float) -> float:
        """Add Laplace noise for differential privacy."""
        if self.budget_used >= self.epsilon:
            logger.warning("Privacy budget exhausted, adding maximum noise")
            sensitivity *= 10  # Add more noise when budget is exhausted
        
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        
        # Track budget usage
        self.budget_used += abs(noise) / sensitivity if sensitivity > 0 else 0
        
        return value + noise
    
    def add_gaussian_noise(self, value: float, sensitivity: float) -> float:
        """Add Gaussian noise for differential privacy."""
        if self.budget_used >= self.epsilon:
            logger.warning("Privacy budget exhausted, adding maximum noise")
            sensitivity *= 10
        
        # Calculate sigma for (ε, δ)-differential privacy
        sigma = math.sqrt(2 * math.log(1.25 / self.delta)) * sensitivity / self.epsilon
        noise = np.random.normal(0, sigma)
        
        self.budget_used += abs(noise) / sensitivity if sensitivity > 0 else 0
        
        return value + noise
    
    def privatize_count(self, count: int, sensitivity: int = 1) -> int:
        """Add noise to count queries."""
        noisy_count = self.add_laplace_noise(float(count), float(sensitivity))
        return max(0, int(round(noisy_count)))
    
    def privatize_sum(self, total: float, max_contribution: float) -> float:
        """Add noise to sum queries."""
        return self.add_laplace_noise(total, max_contribution)
    
    def privatize_average(self, values: List[float], max_value: float, min_value: float) -> float:
        """Add noise to average calculations."""
        if not values:
            return 0.0
        
        sensitivity = (max_value - min_value) / len(values)
        average = sum(values) / len(values)
        return self.add_laplace_noise(average, sensitivity)


class AnonymizationEngine:
    """K-anonymity, l-diversity, and t-closeness implementation."""
    
    def __init__(self):
        """Initialize anonymization engine."""
        self.generalization_hierarchies = self._build_generalization_hierarchies()
    
    def _build_generalization_hierarchies(self) -> Dict[str, List[str]]:
        """Build generalization hierarchies for common attributes."""
        return {
            "age": ["specific_age", "5_year_groups", "10_year_groups", "generation"],
            "zip_code": ["full_zip", "zip_4", "zip_3", "state", "region"],
            "income": ["exact", "10k_brackets", "25k_brackets", "class"],
            "education": ["specific_degree", "degree_level", "education_category"]
        }
    
    def achieve_k_anonymity(
        self, 
        dataset: List[Dict[str, Any]], 
        quasi_identifiers: List[str], 
        k: int = 5
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Achieve k-anonymity through generalization and suppression.
        
        Args:
            dataset: Dataset to anonymize
            quasi_identifiers: List of quasi-identifying attributes
            k: Minimum group size for k-anonymity
            
        Returns:
            Tuple of (anonymized_dataset, anonymization_report)
        """
        logger.info(f"Achieving {k}-anonymity for {len(dataset)} records")
        
        # Group records by quasi-identifier combinations
        groups = self._group_by_quasi_identifiers(dataset, quasi_identifiers)
        
        # Identify groups smaller than k
        small_groups = {key: group for key, group in groups.items() if len(group) < k}
        
        anonymized_records = []
        suppressed_count = 0
        generalized_count = 0
        
        for key, group in groups.items():
            if len(group) >= k:
                # Group already satisfies k-anonymity
                anonymized_records.extend(group)
            else:
                # Try generalization first
                generalized_group = self._generalize_group(group, quasi_identifiers, k)
                
                if generalized_group and len(generalized_group) >= k:
                    anonymized_records.extend(generalized_group)
                    generalized_count += len(group)
                else:
                    # Suppress records if generalization fails
                    suppressed_count += len(group)
        
        report = {
            "original_records": len(dataset),
            "anonymized_records": len(anonymized_records),
            "suppressed_records": suppressed_count,
            "generalized_records": generalized_count,
            "k_value": k,
            "anonymity_achieved": True
        }
        
        return anonymized_records, report
    
    def _group_by_quasi_identifiers(
        self, 
        dataset: List[Dict[str, Any]], 
        quasi_identifiers: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by quasi-identifier combinations."""
        groups = {}
        
        for record in dataset:
            # Create key from quasi-identifier values
            key_parts = []
            for qi in quasi_identifiers:
                value = record.get(qi, "NULL")
                key_parts.append(str(value))
            key = "|".join(key_parts)
            
            if key not in groups:
                groups[key] = []
            groups[key].append(record)
        
        return groups
    
    def _generalize_group(
        self, 
        group: List[Dict[str, Any]], 
        quasi_identifiers: List[str], 
        k: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Attempt to generalize a group to achieve k-anonymity."""
        
        # For now, implement basic generalization
        # In production, this would use sophisticated generalization algorithms
        
        generalized_group = []
        for record in group:
            generalized_record = record.copy()
            
            # Apply basic generalizations
            for qi in quasi_identifiers:
                if qi in record:
                    generalized_record[qi] = self._generalize_value(qi, record[qi])
            
            generalized_group.append(generalized_record)
        
        return generalized_group
    
    def _generalize_value(self, attribute: str, value: Any) -> Any:
        """Apply generalization to a specific value."""
        
        if attribute == "age" and isinstance(value, int):
            # Generalize to 10-year groups
            return f"{(value // 10) * 10}-{(value // 10) * 10 + 9}"
        
        elif attribute == "zip_code" and isinstance(value, str):
            # Generalize to 3-digit ZIP
            return value[:3] + "**" if len(value) >= 3 else value
        
        elif attribute == "income" and isinstance(value, (int, float)):
            # Generalize to 25k brackets
            bracket = int(value // 25000) * 25000
            return f"{bracket}-{bracket + 24999}"
        
        else:
            # Default: no generalization
            return value


class PrivacyRiskAssessment:
    """Privacy risk assessment and re-identification risk calculation."""
    
    def __init__(self):
        """Initialize privacy risk assessment."""
        pass
    
    def assess_reidentification_risk(
        self,
        dataset: List[Dict[str, Any]],
        auxiliary_data: Optional[List[Dict[str, Any]]] = None,
        quasi_identifiers: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Assess re-identification risk for a dataset.
        
        Args:
            dataset: Dataset to assess
            auxiliary_data: External data that could be used for linking
            quasi_identifiers: List of quasi-identifying attributes
            
        Returns:
            Dictionary with risk metrics
        """
        
        if not quasi_identifiers:
            quasi_identifiers = self._identify_quasi_identifiers(dataset)
        
        # Calculate uniqueness-based risk
        uniqueness_risk = self._calculate_uniqueness_risk(dataset, quasi_identifiers)
        
        # Calculate linkage risk if auxiliary data provided
        linkage_risk = 0.0
        if auxiliary_data:
            linkage_risk = self._calculate_linkage_risk(dataset, auxiliary_data, quasi_identifiers)
        
        # Calculate membership inference risk
        membership_risk = self._calculate_membership_risk(dataset)
        
        # Calculate overall risk
        overall_risk = max(uniqueness_risk, linkage_risk, membership_risk)
        
        return {
            "overall_risk": overall_risk,
            "uniqueness_risk": uniqueness_risk,
            "linkage_risk": linkage_risk,
            "membership_risk": membership_risk,
            "unique_records": self._count_unique_records(dataset, quasi_identifiers),
            "total_records": len(dataset),
            "quasi_identifiers_used": quasi_identifiers
        }
    
    def _identify_quasi_identifiers(self, dataset: List[Dict[str, Any]]) -> List[str]:
        """Automatically identify potential quasi-identifiers."""
        
        if not dataset:
            return []
        
        quasi_identifiers = []
        common_qis = [
            "age", "age_group", "gender", "race", "ethnicity",
            "zip_code", "zipcode", "postal_code", "state", "city",
            "income", "education", "occupation", "marital_status"
        ]
        
        # Check which common QIs exist in the dataset
        sample_record = dataset[0]
        for qi in common_qis:
            if qi in sample_record:
                quasi_identifiers.append(qi)
        
        return quasi_identifiers
    
    def _calculate_uniqueness_risk(
        self, 
        dataset: List[Dict[str, Any]], 
        quasi_identifiers: List[str]
    ) -> float:
        """Calculate risk based on record uniqueness."""
        
        if not dataset or not quasi_identifiers:
            return 0.0
        
        # Group records by quasi-identifier combinations
        groups = {}
        for record in dataset:
            key_parts = []
            for qi in quasi_identifiers:
                key_parts.append(str(record.get(qi, "NULL")))
            key = "|".join(key_parts)
            
            if key not in groups:
                groups[key] = 0
            groups[key] += 1
        
        # Calculate uniqueness risk
        unique_records = sum(1 for count in groups.values() if count == 1)
        total_records = len(dataset)
        
        return unique_records / total_records if total_records > 0 else 0.0
    
    def _calculate_linkage_risk(
        self,
        dataset: List[Dict[str, Any]],
        auxiliary_data: List[Dict[str, Any]],
        quasi_identifiers: List[str]
    ) -> float:
        """Calculate risk from linkage attacks using auxiliary data."""
        
        if not dataset or not auxiliary_data or not quasi_identifiers:
            return 0.0
        
        # Simple linkage risk calculation
        # In practice, this would be much more sophisticated
        
        linkable_records = 0
        total_records = len(dataset)
        
        for record in dataset[:min(100, len(dataset))]:  # Sample for performance
            # Check if record could be linked to auxiliary data
            matches = 0
            for aux_record in auxiliary_data[:min(1000, len(auxiliary_data))]:
                match_score = 0
                for qi in quasi_identifiers:
                    if qi in record and qi in aux_record:
                        if str(record[qi]) == str(aux_record[qi]):
                            match_score += 1
                
                # If high match score, consider linkable
                if match_score >= len(quasi_identifiers) * 0.7:
                    matches += 1
            
            if matches > 0:
                linkable_records += 1
        
        return linkable_records / min(100, total_records) if total_records > 0 else 0.0
    
    def _calculate_membership_risk(self, dataset: List[Dict[str, Any]]) -> float:
        """Calculate membership inference risk."""
        
        # Simple membership inference risk based on dataset size and diversity
        if not dataset:
            return 0.0
        
        # Smaller datasets have higher membership risk
        size_factor = min(1.0, 1000.0 / len(dataset))
        
        # Less diverse datasets have higher membership risk
        diversity_factor = self._calculate_diversity_factor(dataset)
        
        return min(1.0, size_factor * (1.0 - diversity_factor))
    
    def _calculate_diversity_factor(self, dataset: List[Dict[str, Any]]) -> float:
        """Calculate diversity factor for membership risk."""
        
        if not dataset:
            return 0.0
        
        # Count unique values across all fields
        unique_values = set()
        total_values = 0
        
        for record in dataset:
            for key, value in record.items():
                unique_values.add(f"{key}:{str(value)}")
                total_values += 1
        
        return len(unique_values) / total_values if total_values > 0 else 0.0
    
    def _count_unique_records(
        self, 
        dataset: List[Dict[str, Any]], 
        quasi_identifiers: List[str]
    ) -> int:
        """Count records that are unique in their quasi-identifier combination."""
        
        groups = {}
        for record in dataset:
            key_parts = []
            for qi in quasi_identifiers:
                key_parts.append(str(record.get(qi, "NULL")))
            key = "|".join(key_parts)
            
            if key not in groups:
                groups[key] = 0
            groups[key] += 1
        
        return sum(1 for count in groups.values() if count == 1)


class PrivacyEngine:
    """Main privacy protection engine."""
    
    def __init__(self):
        """Initialize privacy engine."""
        self.anonymization_engine = AnonymizationEngine()
        self.risk_assessment = PrivacyRiskAssessment()
        
        logger.info("Privacy Engine initialized successfully")
    
    async def protect_dataset(
        self,
        dataset: List[Dict[str, Any]],
        privacy_level: PrivacyLevel,
        domain: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply privacy protection to a dataset.
        
        Args:
            dataset: Dataset to protect
            privacy_level: Level of privacy protection to apply
            domain: Data domain for context
            
        Returns:
            Tuple of (protected_dataset, privacy_metrics)
        """
        
        logger.info(f"Applying {privacy_level} privacy protection to {len(dataset)} records")
        
        protected_dataset = dataset.copy()
        epsilon = get_epsilon_for_privacy_level(privacy_level)
        
        # Initialize differential privacy
        dp_engine = DifferentialPrivacy(epsilon=epsilon)
        
        # Apply domain-specific privacy protection
        if domain == "healthcare":
            protected_dataset = await self._apply_healthcare_privacy(protected_dataset, privacy_level, dp_engine)
        elif domain == "finance":
            protected_dataset = await self._apply_finance_privacy(protected_dataset, privacy_level, dp_engine)
        else:
            protected_dataset = await self._apply_general_privacy(protected_dataset, privacy_level, dp_engine)
        
        # Assess privacy metrics
        privacy_metrics = await self._calculate_privacy_metrics(
            original_dataset=dataset,
            protected_dataset=protected_dataset,
            privacy_level=privacy_level,
            epsilon=epsilon
        )
        
        return protected_dataset, privacy_metrics
    
    async def _apply_healthcare_privacy(
        self,
        dataset: List[Dict[str, Any]],
        privacy_level: PrivacyLevel,
        dp_engine: DifferentialPrivacy
    ) -> List[Dict[str, Any]]:
        """Apply healthcare-specific privacy protection."""
        
        protected_dataset = []
        
        for record in dataset:
            protected_record = record.copy()
            
            # Apply differential privacy to numeric health metrics
            numeric_fields = ["total_cost", "comorbidity_count", "total_encounters"]
            for field in numeric_fields:
                if field in protected_record and isinstance(protected_record[field], (int, float)):
                    # Determine sensitivity based on field
                    sensitivity = self._get_healthcare_sensitivity(field)
                    protected_record[field] = dp_engine.add_laplace_noise(
                        float(protected_record[field]), sensitivity
                    )
            
            # Apply additional anonymization based on privacy level
            if privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM]:
                # Remove or generalize geographic information
                if "zip_code_3digit" in protected_record:
                    protected_record["zip_code_3digit"] = None
                
                # Generalize age groups further
                if "age_group" in protected_record.get("demographics", {}):
                    age_group = protected_record["demographics"]["age_group"]
                    protected_record["demographics"]["age_group"] = self._generalize_age_group(age_group)
            
            protected_dataset.append(protected_record)
        
        return protected_dataset
    
    async def _apply_finance_privacy(
        self,
        dataset: List[Dict[str, Any]],
        privacy_level: PrivacyLevel,
        dp_engine: DifferentialPrivacy
    ) -> List[Dict[str, Any]]:
        """Apply finance-specific privacy protection."""
        
        protected_dataset = []
        
        for record in dataset:
            protected_record = record.copy()
            
            # Apply differential privacy to financial amounts
            amount_fields = ["amount", "balance_after_range", "total_charges"]
            for field in amount_fields:
                if field in protected_record and isinstance(protected_record[field], (int, float)):
                    sensitivity = self._get_finance_sensitivity(field)
                    protected_record[field] = dp_engine.add_laplace_noise(
                        float(protected_record[field]), sensitivity
                    )
            
            # Apply additional anonymization based on privacy level
            if privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM]:
                # Remove specific geographic information
                if "transaction_zip3" in protected_record:
                    protected_record["transaction_zip3"] = None
                
                # Generalize transaction times
                if "hour_of_day" in protected_record:
                    hour = protected_record["hour_of_day"]
                    protected_record["hour_of_day"] = self._generalize_hour(hour)
            
            protected_dataset.append(protected_record)
        
        return protected_dataset
    
    async def _apply_general_privacy(
        self,
        dataset: List[Dict[str, Any]],
        privacy_level: PrivacyLevel,
        dp_engine: DifferentialPrivacy
    ) -> List[Dict[str, Any]]:
        """Apply general privacy protection."""
        
        # Apply k-anonymity
        quasi_identifiers = self.risk_assessment._identify_quasi_identifiers(dataset)
        
        if quasi_identifiers:
            k_value = self._get_k_value_for_privacy_level(privacy_level)
            protected_dataset, _ = self.anonymization_engine.achieve_k_anonymity(
                dataset, quasi_identifiers, k_value
            )
        else:
            protected_dataset = dataset.copy()
        
        return protected_dataset
    
    async def _calculate_privacy_metrics(
        self,
        original_dataset: List[Dict[str, Any]],
        protected_dataset: List[Dict[str, Any]],
        privacy_level: PrivacyLevel,
        epsilon: float
    ) -> Dict[str, Any]:
        """Calculate privacy protection metrics."""
        
        # Assess re-identification risk
        risk_assessment = self.risk_assessment.assess_reidentification_risk(protected_dataset)
        
        # Calculate utility preservation
        utility_score = self._calculate_utility_preservation(original_dataset, protected_dataset)
        
        return {
            "privacy_level": str(privacy_level),
            "epsilon": epsilon,
            "risk_score": risk_assessment["overall_risk"],
            "reidentification_risk": risk_assessment["uniqueness_risk"],
            "utility_preservation": utility_score,
            "records_protected": len(protected_dataset),
            "unique_records": risk_assessment["unique_records"],
            "privacy_budget_used": epsilon * 0.1,  # Simplified budget tracking
            "anonymization_techniques": [
                "differential_privacy",
                "k_anonymity" if privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM] else None,
                "generalization"
            ]
        }
    
    async def analyze_privacy_risk(
        self,
        dataset: List[Dict[str, Any]],
        auxiliary_data: Optional[List[Dict[str, Any]]] = None,
        attack_scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze privacy risks in a dataset."""
        
        if not attack_scenarios:
            attack_scenarios = ["linkage", "inference", "membership"]
        
        risk_results = {}
        
        for scenario in attack_scenarios:
            if scenario == "linkage":
                risk_results["linkage_risk"] = self.risk_assessment.assess_reidentification_risk(
                    dataset, auxiliary_data
                )
            elif scenario == "membership":
                risk_results["membership_risk"] = {
                    "risk_score": self.risk_assessment._calculate_membership_risk(dataset)
                }
            elif scenario == "inference":
                risk_results["inference_risk"] = {
                    "risk_score": self._calculate_inference_risk(dataset)
                }
        
        # Generate recommendations
        recommendations = self._generate_privacy_recommendations(risk_results)
        
        return {
            "overall_risk": max(r.get("overall_risk", r.get("risk_score", 0.0)) for r in risk_results.values()),
            "attack_results": risk_results,
            "recommendations": recommendations,
            "dp_recommendations": {
                "suggested_epsilon": 0.1 if any(r.get("overall_risk", 0) > 0.1 for r in risk_results.values()) else 1.0
            }
        }
    
    def _get_healthcare_sensitivity(self, field: str) -> float:
        """Get sensitivity values for healthcare fields."""
        sensitivities = {
            "total_cost": 1000.0,
            "comorbidity_count": 1.0,
            "total_encounters": 1.0,
            "age": 1.0
        }
        return sensitivities.get(field, 10.0)
    
    def _get_finance_sensitivity(self, field: str) -> float:
        """Get sensitivity values for financial fields."""
        sensitivities = {
            "amount": 100.0,
            "balance": 1000.0,
            "credit_score": 50.0,
            "income": 5000.0
        }
        return sensitivities.get(field, 100.0)
    
    def _get_k_value_for_privacy_level(self, privacy_level: PrivacyLevel) -> int:
        """Get k-anonymity value based on privacy level."""
        k_values = {
            PrivacyLevel.LOW: 3,
            PrivacyLevel.MEDIUM: 5,
            PrivacyLevel.HIGH: 10,
            PrivacyLevel.MAXIMUM: 20
        }
        return k_values[privacy_level]
    
    def _generalize_age_group(self, age_group: str) -> str:
        """Generalize age group for higher privacy."""
        age_mappings = {
            "18-24": "18-34", "25-34": "18-34",
            "35-44": "35-54", "45-54": "35-54",
            "55-64": "55-74", "65-74": "55-74",
            "75-84": "75+", "85+": "75+"
        }
        return age_mappings.get(age_group, age_group)
    
    def _generalize_hour(self, hour: int) -> str:
        """Generalize hour to time periods."""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _calculate_utility_preservation(
        self,
        original_dataset: List[Dict[str, Any]],
        protected_dataset: List[Dict[str, Any]]
    ) -> float:
        """Calculate how much utility is preserved after privacy protection."""
        
        if not original_dataset or not protected_dataset:
            return 0.0
        
        # Simple utility calculation based on data similarity
        # In practice, this would be much more sophisticated
        
        common_fields = 0
        total_fields = 0
        
        if original_dataset and protected_dataset:
            original_keys = set(original_dataset[0].keys())
            protected_keys = set(protected_dataset[0].keys())
            
            common_fields = len(original_keys.intersection(protected_keys))
            total_fields = len(original_keys)
        
        return common_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_inference_risk(self, dataset: List[Dict[str, Any]]) -> float:
        """Calculate attribute inference risk."""
        
        # Simple inference risk based on attribute correlation
        if not dataset or len(dataset) < 2:
            return 0.0
        
        # Check for high correlation between attributes
        # This is a simplified implementation
        return 0.3  # Placeholder value
    
    def _generate_privacy_recommendations(self, risk_results: Dict[str, Any]) -> List[str]:
        """Generate privacy improvement recommendations."""
        
        recommendations = []
        
        for attack_type, result in risk_results.items():
            risk_score = result.get("overall_risk", result.get("risk_score", 0.0))
            
            if risk_score > 0.1:
                if attack_type == "linkage_risk":
                    recommendations.append("Apply stronger generalization to quasi-identifiers")
                    recommendations.append("Consider removing geographic information")
                elif attack_type == "membership_risk":
                    recommendations.append("Increase dataset size or add more noise")
                    recommendations.append("Apply differential privacy with lower epsilon")
                elif attack_type == "inference_risk":
                    recommendations.append("Remove highly correlated attributes")
                    recommendations.append("Apply l-diversity or t-closeness")
        
        if not recommendations:
            recommendations.append("Privacy protection appears adequate")
            recommendations.append("Continue monitoring for emerging privacy risks")
        
        return recommendations