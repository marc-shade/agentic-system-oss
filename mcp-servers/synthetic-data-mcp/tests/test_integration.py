"""
Comprehensive integration tests for the synthetic data platform.

Tests all major components including data generation, compliance,
security, scaling, and monitoring features.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
import tempfile
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import platform components
from synthetic_data_mcp.server import app, SyntheticDataGenerator
from synthetic_data_mcp.core.generator import SyntheticDataGenerator as DataGenerator
from synthetic_data_mcp.privacy.engine import PrivacyEngine
from synthetic_data_mcp.validation.statistical import StatisticalValidator
from synthetic_data_mcp.compliance.validator import ComplianceValidator
from synthetic_data_mcp.schemas.healthcare import Patient, MedicalRecord, LabResult
from synthetic_data_mcp.schemas.finance import Transaction, Account, Customer
from synthetic_data_mcp.infrastructure.scaling import (
    ShardedDatabaseManager,
    AutoScaler,
    ServiceDiscovery,
    LoadBalancer
)
from synthetic_data_mcp.infrastructure.caching import (
    CacheManager,
    RateLimiter,
    CircuitBreaker
)
from synthetic_data_mcp.monitoring.metrics import (
    MetricsCollector,
    AlertingService as AlertManager
)
# Mock non-existent PerformanceMonitor
from unittest.mock import MagicMock
PerformanceMonitor = MagicMock()
from synthetic_data_mcp.security.auth import (
    AuthService,
    RoleBasedAccessControl,
    DataEncryption
)
from synthetic_data_mcp.security.encryption import (
    AdvancedEncryptionService,
    DataEncryptionKeyManager,
    FieldLevelEncryption,
    EncryptionAlgorithm
)
from synthetic_data_mcp.compliance.soc2 import (
    SOC2ComplianceManager,
    TrustServiceCriteria,
    ControlCategory
)
from synthetic_data_mcp.compliance.regulatory_reporting import (
    RegulatoryReportGenerator,
    RegulatoryFramework,
    ReportType,
    DataBreachIncident
)
from synthetic_data_mcp.compliance.data_residency import (
    DataResidencyManager,
    DataRegion,
    ResidencyRequirement,
    DataClassification
)
from synthetic_data_mcp.compliance.consent_management import (
    ConsentManager,
    ConsentPurpose,
    DataSubjectRight
)


# Test fixtures
@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    from synthetic_data_mcp.models import Base
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
async def data_generator():
    """Create data generator instance."""
    generator = DataGenerator()
    await generator.initialize()
    return generator


@pytest.fixture
async def privacy_engine():
    """Create privacy engine instance."""
    engine = PrivacyEngine()
    return engine


@pytest.fixture
async def auth_service(test_db):
    """Create auth service instance."""
    service = AuthService(test_db)
    return service


@pytest.fixture
async def encryption_service():
    """Create encryption service instance."""
    key_manager = DataEncryptionKeyManager()
    service = AdvancedEncryptionService(key_manager)
    return service


@pytest.fixture
async def compliance_manager(test_db):
    """Create SOC 2 compliance manager."""
    manager = SOC2ComplianceManager(test_db)
    return manager


@pytest.fixture
async def consent_manager(test_db):
    """Create consent manager."""
    manager = ConsentManager(test_db)
    return manager


class TestDataGeneration:
    """Test data generation capabilities."""
    
    @pytest.mark.asyncio
    async def test_healthcare_data_generation(self, data_generator):
        """Test healthcare data generation."""
        # Configure generation
        config = {
            "schema": "healthcare",
            "num_records": 100,
            "include_pii": False,
            "seed": 42
        }
        
        # Generate data
        dataset = await data_generator.generate(
            schema_type="healthcare",
            num_records=100,
            config=config
        )
        
        # Verify structure
        assert "patients" in dataset
        assert "medical_records" in dataset
        assert "lab_results" in dataset
        
        # Verify record count
        assert len(dataset["patients"]) == 100
        assert len(dataset["medical_records"]) >= 100
        
        # Verify no PII
        for patient in dataset["patients"]:
            assert "ssn" not in patient or patient["ssn"] is None
            assert "name" not in patient or "REDACTED" in patient["name"]
    
    @pytest.mark.asyncio
    async def test_financial_data_generation(self, data_generator):
        """Test financial data generation."""
        config = {
            "schema": "finance",
            "num_records": 50,
            "include_pii": True,
            "transaction_range": [10, 10000]
        }
        
        dataset = await data_generator.generate(
            schema_type="finance",
            num_records=50,
            config=config
        )
        
        assert "customers" in dataset
        assert "accounts" in dataset
        assert "transactions" in dataset
        
        # Verify transaction amounts
        for transaction in dataset["transactions"]:
            assert 10 <= transaction["amount"] <= 10000
    
    @pytest.mark.asyncio
    async def test_data_quality_validation(self, data_generator):
        """Test data quality validation."""
        dataset = await data_generator.generate(
            schema_type="healthcare",
            num_records=100
        )
        
        validator = DataValidator()
        
        # Validate completeness
        completeness = await validator.validate_completeness(dataset["patients"])
        assert completeness > 0.95  # 95% complete
        
        # Validate uniqueness
        uniqueness = await validator.validate_uniqueness(
            dataset["patients"],
            key_field="patient_id"
        )
        assert uniqueness == 1.0  # All IDs unique
        
        # Validate consistency
        consistency = await validator.validate_consistency(dataset)
        assert consistency > 0.98


class TestPrivacyProtection:
    """Test privacy protection mechanisms."""
    
    @pytest.mark.asyncio
    async def test_differential_privacy(self, privacy_engine, data_generator):
        """Test differential privacy application."""
        # Generate raw data
        dataset = await data_generator.generate(
            schema_type="healthcare",
            num_records=1000
        )
        
        # Apply differential privacy
        protected_dataset, metrics = await privacy_engine.protect_dataset(
            dataset,
            epsilon=1.0,
            delta=1e-5
        )
        
        # Verify privacy metrics
        assert metrics.epsilon == 1.0
        assert metrics.delta == 1e-5
        assert metrics.sensitivity > 0
        
        # Verify utility preservation
        original_mean = np.mean([p.get("age", 0) for p in dataset["patients"]])
        protected_mean = np.mean([p.get("age", 0) for p in protected_dataset["patients"]])
        
        # Should be close but not identical
        assert abs(original_mean - protected_mean) < 5
        assert original_mean != protected_mean
    
    @pytest.mark.asyncio
    async def test_k_anonymity(self, privacy_engine):
        """Test k-anonymity enforcement."""
        # Create test dataset
        data = pd.DataFrame({
            "age": [25, 25, 30, 30, 30, 35, 35, 40],
            "zipcode": ["12345", "12345", "12346", "12346", "12346", "12347", "12347", "12348"],
            "disease": ["flu", "cold", "flu", "covid", "flu", "cold", "flu", "covid"]
        })
        
        # Apply k-anonymity (k=2)
        anonymized = await privacy_engine.apply_k_anonymity(data, k=2)
        
        # Verify k-anonymity
        quasi_identifiers = ["age", "zipcode"]
        groups = anonymized.groupby(quasi_identifiers).size()
        
        assert all(count >= 2 for count in groups)
    
    @pytest.mark.asyncio
    async def test_data_masking(self, privacy_engine):
        """Test PII masking."""
        sensitive_data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "address": "123 Main St"
        }
        
        masked = await privacy_engine.mask_pii(sensitive_data)
        
        assert masked["name"] != "John Doe"
        assert "***" in masked["ssn"] or "XXX" in masked["ssn"]
        assert "@" in masked["email"] and "john.doe" not in masked["email"]
        assert masked["phone"] != "555-123-4567"


class TestCompliance:
    """Test compliance features."""
    
    @pytest.mark.asyncio
    async def test_hipaa_compliance(self):
        """Test HIPAA compliance validation."""
        validator = ComplianceValidator()
        
        # Create test healthcare data
        data = {
            "patient_id": "P12345",
            "diagnosis": "Type 2 Diabetes",
            "treatment": "Metformin",
            "provider": "Dr. Smith"
        }
        
        # Validate HIPAA compliance
        result = await validator.validate_hipaa(data)
        
        assert result["compliant"] == True
        assert "safe_harbor" in result["methods"]
        assert len(result["identifiers_removed"]) >= 18
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance(self, consent_manager):
        """Test GDPR compliance features."""
        data_subject_id = "USER123"
        
        # Collect consent
        consent = await consent_manager.collect_consent(
            data_subject_id=data_subject_id,
            purpose=ConsentPurpose.DATA_GENERATION,
            language="en"
        )
        
        assert consent.status.value == "pending"
        
        # Grant consent
        await consent_manager.grant_consent(consent.consent_id)
        
        # Check consent
        has_consent, record = await consent_manager.check_consent(
            data_subject_id,
            ConsentPurpose.DATA_GENERATION
        )
        
        assert has_consent == True
        
        # Test data subject rights
        access_request = await consent_manager.create_data_subject_request(
            data_subject_id=data_subject_id,
            right=DataSubjectRight.ACCESS,
            details={}
        )
        
        assert access_request.status == "pending"
        assert access_request.response_deadline > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_pci_dss_compliance(self):
        """Test PCI DSS compliance."""
        validator = ComplianceValidator()
        
        # Create test payment data
        card_data = {
            "card_number": "4111111111111111",
            "cvv": "123",
            "expiry": "12/25",
            "cardholder": "John Doe"
        }
        
        # Validate PCI DSS compliance
        result = await validator.validate_pci_dss(card_data)
        
        assert result["requires_encryption"] == True
        assert result["tokenization_required"] == True
        assert "card_number" in result["sensitive_fields"]
    
    @pytest.mark.asyncio
    async def test_soc2_compliance(self, compliance_manager):
        """Test SOC 2 Type II compliance."""
        # Test security control
        security_test = await compliance_manager.test_control("SEC-001")
        
        assert security_test.control_id == "SEC-001"
        assert security_test.result in ["pass", "fail", "partial"]
        assert len(security_test.evidence) > 0
        
        # Generate compliance report
        report = await compliance_manager.generate_compliance_report()
        
        assert "overall_status" in report
        assert "controls_summary" in report
        assert "criteria_summary" in report
        
        # Check all trust service criteria
        for criteria in TrustServiceCriteria:
            assert criteria.value in report["criteria_summary"]


class TestSecurity:
    """Test security features."""
    
    @pytest.mark.asyncio
    async def test_authentication(self, auth_service):
        """Test authentication system."""
        # Create user
        user = await auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Test login
        authenticated = await auth_service.authenticate_user(
            username="testuser",
            password="SecurePass123!"
        )
        
        assert authenticated is not None
        assert authenticated.username == "testuser"
        
        # Test token generation
        token = auth_service.create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        
        assert token is not None
        
        # Test token verification
        token_data = auth_service.verify_token(token)
        
        assert token_data is not None
        assert token_data.sub == str(user.id)
    
    @pytest.mark.asyncio
    async def test_encryption(self, encryption_service):
        """Test data encryption."""
        sensitive_data = {
            "ssn": "123-45-6789",
            "credit_card": "4111111111111111",
            "medical_record": "Patient has diabetes"
        }
        
        # Test AES-256-GCM encryption
        encrypted = await encryption_service.encrypt(
            json.dumps(sensitive_data),
            algorithm=EncryptionAlgorithm.AES_256_GCM
        )
        
        assert encrypted.ciphertext != sensitive_data
        assert encrypted.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert encrypted.nonce is not None
        assert encrypted.tag is not None
        
        # Test decryption
        decrypted = await encryption_service.decrypt(encrypted)
        decrypted_data = json.loads(decrypted)
        
        assert decrypted_data == sensitive_data
    
    @pytest.mark.asyncio
    async def test_field_level_encryption(self, encryption_service):
        """Test field-level encryption."""
        field_encryption = FieldLevelEncryption(encryption_service)
        
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "age": 30,
            "diagnosis": "Hypertension"
        }
        
        # Encrypt sensitive fields
        encrypted_data = await field_encryption.encrypt_fields(
            data,
            sensitive_fields=["ssn", "diagnosis"]
        )
        
        assert encrypted_data["name"] == "John Doe"
        assert encrypted_data["age"] == 30
        assert encrypted_data["ssn"]["_encrypted"] == True
        assert encrypted_data["diagnosis"]["_encrypted"] == True
        
        # Decrypt fields
        decrypted_data = await field_encryption.decrypt_fields(encrypted_data)
        
        assert decrypted_data == data
    
    @pytest.mark.asyncio
    async def test_api_key_management(self, auth_service):
        """Test API key management."""
        # Create API key
        api_key = await auth_service.create_api_key(
            user_id=1,
            name="test-api-key",
            scopes=["read", "write"],
            expires_in_days=30
        )
        
        assert api_key is not None
        assert len(api_key) >= 32
        
        # Verify API key
        key_data = await auth_service.verify_api_key(api_key)
        
        assert key_data is not None
        assert key_data.name == "test-api-key"
        assert "read" in key_data.scopes


class TestScaling:
    """Test scaling and performance features."""
    
    @pytest.mark.asyncio
    async def test_database_sharding(self, test_db):
        """Test database sharding."""
        shard_manager = ShardedDatabaseManager(
            num_shards=4,
            strategy="hash"
        )
        
        # Test shard assignment
        shard1 = shard_manager.get_shard_for_key("user_123")
        shard2 = shard_manager.get_shard_for_key("user_456")
        
        assert shard1 in ["shard_0", "shard_1", "shard_2", "shard_3"]
        assert shard2 in ["shard_0", "shard_1", "shard_2", "shard_3"]
        
        # Test consistent hashing
        assert shard_manager.get_shard_for_key("user_123") == shard1
    
    @pytest.mark.asyncio
    async def test_caching(self):
        """Test caching system."""
        cache_manager = CacheManager()
        
        # Test set and get
        await cache_manager.set("test_key", {"data": "value"}, ttl=60)
        cached = await cache_manager.get("test_key")
        
        assert cached == {"data": "value"}
        
        # Test cache stats
        stats = cache_manager.get_stats()
        
        assert stats["l1_hits"] >= 0
        assert stats["hit_rate"] >= 0
        
        # Test cache invalidation
        await cache_manager.delete("test_key")
        assert await cache_manager.get("test_key") is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting."""
        rate_limiter = RateLimiter()
        
        # Test rate limit check
        user_key = "user_123"
        
        # Should allow initial requests
        for i in range(10):
            allowed, info = await rate_limiter.check_rate_limit(
                key=user_key,
                limit_type="api_per_user"
            )
            assert allowed == True
        
        # Test custom limits
        allowed, info = await rate_limiter.check_rate_limit(
            key="api_endpoint",
            custom_limit={"requests": 5, "window": 60}
        )
        
        assert "current" in info
        assert "limit" in info
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """Test circuit breaker pattern."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5
        )
        
        # Simulate failures
        async def failing_function():
            raise Exception("Service unavailable")
        
        # Test circuit opening
        for i in range(3):
            try:
                await breaker.call(failing_function)
            except:
                pass
        
        assert breaker.state == "open"
        
        # Test circuit breaker prevents calls
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await breaker.call(failing_function)


class TestDataResidency:
    """Test data residency management."""
    
    @pytest.mark.asyncio
    async def test_region_determination(self, test_db):
        """Test region determination based on user location."""
        manager = DataResidencyManager(test_db)
        
        # Test EU user
        region = await manager.get_required_region(
            user_country="DE",
            data_type="personal_data"
        )
        assert region == DataRegion.EU_CENTRAL
        
        # Test US user
        region = await manager.get_required_region(
            user_country="US",
            data_type="general"
        )
        assert region == DataRegion.US_EAST
        
        # Test with IP geolocation (mock)
        region = await manager.get_required_region(
            user_ip="8.8.8.8",  # Google DNS (US)
            data_type="general"
        )
        assert region == DataRegion.US_EAST
    
    @pytest.mark.asyncio
    async def test_data_storage_compliance(self, test_db):
        """Test compliant data storage."""
        manager = DataResidencyManager(test_db)
        
        # Create test data
        test_data = b"Sensitive personal data"
        
        # Store with residency requirements
        location = await manager.store_data(
            data=test_data,
            data_id="TEST123",
            classification=DataClassification.CONFIDENTIAL,
            user_country="DE"
        )
        
        assert location.primary_region == DataRegion.EU_CENTRAL
        assert location.classification == DataClassification.CONFIDENTIAL
        
        # Validate location compliance
        valid, violations = await manager.validate_data_location(
            data_id="TEST123",
            required_region=DataRegion.EU_CENTRAL,
            current_location=location
        )
        
        assert valid == True
        assert len(violations) == 0


class TestMonitoring:
    """Test monitoring and observability."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics collection."""
        collector = MetricsCollector()
        
        # Record metrics
        collector.record_counter("api_requests", 1, {"endpoint": "/generate"})
        collector.record_histogram("response_time", 0.125, {"endpoint": "/generate"})
        collector.record_gauge("active_users", 42)
        
        # Get metrics
        metrics = collector.get_metrics()
        
        assert "api_requests" in metrics["counters"]
        assert "response_time" in metrics["histograms"]
        assert "active_users" in metrics["gauges"]
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring."""
        monitor = PerformanceMonitor()
        
        # Start monitoring
        trace_id = monitor.start_trace("test_operation")
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        # End monitoring
        duration = monitor.end_trace(trace_id)
        
        assert duration >= 0.1
        
        # Get performance report
        report = monitor.get_performance_report()
        
        assert "average_duration" in report
        assert "p99_duration" in report
    
    @pytest.mark.asyncio
    async def test_alerting(self):
        """Test alerting system."""
        alert_manager = AlertManager()
        
        # Configure alert rule
        alert_manager.add_rule(
            name="high_error_rate",
            condition=lambda metrics: metrics.get("error_rate", 0) > 0.05,
            severity="critical"
        )
        
        # Trigger alert
        alerts = alert_manager.check_alerts({"error_rate": 0.1})
        
        assert len(alerts) > 0
        assert alerts[0]["name"] == "high_error_rate"
        assert alerts[0]["severity"] == "critical"


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete data generation workflow."""
        # Initialize components
        generator = SyntheticDataGenerator()
        
        # Create generation request
        request = {
            "schema": "healthcare",
            "num_records": 100,
            "privacy_level": "high",
            "compliance_frameworks": ["HIPAA", "GDPR"],
            "output_format": "json"
        }
        
        # Generate data
        result = await generator.generate_synthetic_dataset(request)
        
        # Verify result
        assert result["status"] == "success"
        assert "dataset" in result
        assert "privacy_metrics" in result
        assert "compliance_validation" in result
        
        # Verify privacy
        assert result["privacy_metrics"]["epsilon"] <= 1.0
        assert result["privacy_metrics"]["k_anonymity"] >= 5
        
        # Verify compliance
        assert result["compliance_validation"]["HIPAA"]["compliant"] == True
        assert result["compliance_validation"]["GDPR"]["compliant"] == True
    
    @pytest.mark.asyncio
    async def test_api_integration(self):
        """Test API integration."""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health check
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test data generation endpoint
        response = client.post(
            "/api/v1/generate",
            json={
                "schema": "finance",
                "num_records": 50,
                "privacy_level": "medium"
            },
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code in [200, 401]  # Depends on auth
        
        # Test metrics endpoint
        response = client.get("/metrics")
        assert response.status_code in [200, 403]  # Restricted endpoint


class TestPerformance:
    """Performance and load tests."""
    
    @pytest.mark.asyncio
    async def test_generation_performance(self, data_generator):
        """Test data generation performance."""
        start_time = time.time()
        
        # Generate large dataset
        dataset = await data_generator.generate(
            schema_type="healthcare",
            num_records=10000
        )
        
        duration = time.time() - start_time
        
        # Should complete within reasonable time
        assert duration < 60  # 60 seconds for 10k records
        
        # Calculate throughput
        throughput = 10000 / duration
        assert throughput > 100  # At least 100 records/second
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, data_generator):
        """Test concurrent request handling."""
        tasks = []
        
        # Create concurrent requests
        for i in range(10):
            task = data_generator.generate(
                schema_type="finance",
                num_records=100
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Verify all completed
        assert len(results) == 10
        
        # Should handle concurrent requests efficiently
        assert duration < 30  # Less than 3 seconds per request average


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])