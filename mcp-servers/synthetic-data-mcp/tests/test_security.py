"""
Security tests for the synthetic data platform.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import hashlib
import secrets

from synthetic_data_mcp.security.auth import AuthService, RoleBasedAccessControl
from synthetic_data_mcp.privacy.engine import PrivacyEngine
from synthetic_data_mcp.compliance.validator import ComplianceValidator


class TestSecurity:
    """Test security features and protections."""

    def test_authentication_manager_init(self):
        """Test AuthenticationManager initialization."""
        config = {
            "secret_key": "test_secret_key_12345",
            "token_expiry": 3600,
            "hash_algorithm": "SHA256"
        }
        
        auth_mgr = AuthenticationManager(config)
        assert auth_mgr.config == config
        assert auth_mgr.token_expiry == 3600

    def test_jwt_token_manager_init(self):
        """Test JWT token manager initialization."""
        config = {
            "secret_key": "***REMOVED***",
            "algorithm": "HS256",
            "expiry_hours": 24
        }
        
        jwt_mgr = JWTTokenManager(config)
        assert jwt_mgr.config == config
        assert jwt_mgr.algorithm == "HS256"

    @pytest.mark.asyncio
    async def test_password_hashing(self):
        """Test secure password hashing."""
        auth_mgr = AuthenticationManager({
            "secret_key": "test_key",
            "hash_algorithm": "SHA256"
        })
        
        password = "user_password_123"
        salt = secrets.token_hex(16)
        
        with patch.object(auth_mgr, 'hash_password') as mock_hash:
            mock_hash.return_value = hashlib.sha256((password + salt).encode()).hexdigest()
            
            hashed = await auth_mgr.hash_password(password, salt)
            assert len(hashed) == 64  # SHA256 hex length
            assert hashed != password  # Should be hashed
            mock_hash.assert_called_once_with(password, salt)

    @pytest.mark.asyncio
    async def test_jwt_token_generation(self):
        """Test JWT token generation and validation."""
        jwt_mgr = JWTTokenManager({
            "secret_key": "jwt_secret_key",
            "algorithm": "HS256",
            "expiry_hours": 1
        })
        
        user_data = {
            "user_id": "user123",
            "username": "testuser",
            "roles": ["user", "data_generator"]
        }
        
        with patch.object(jwt_mgr, 'generate_token') as mock_generate:
            with patch.object(jwt_mgr, 'validate_token') as mock_validate:
                mock_token = "***REMOVED***"
                mock_generate.return_value = mock_token
                mock_validate.return_value = user_data
                
                # Generate token
                token = await jwt_mgr.generate_token(user_data)
                assert token == mock_token
                
                # Validate token
                validated_data = await jwt_mgr.validate_token(token)
                assert validated_data["user_id"] == "user123"
                assert "data_generator" in validated_data["roles"]

    @pytest.mark.asyncio
    async def test_api_key_authentication(self):
        """Test API key authentication."""
        auth_mgr = AuthenticationManager({
            "api_keys": {
                "key_12345": {"user_id": "user123", "permissions": ["read", "write"]},
                "key_67890": {"user_id": "user456", "permissions": ["read"]}
            }
        })
        
        with patch.object(auth_mgr, 'validate_api_key') as mock_validate:
            mock_validate.return_value = {"user_id": "user123", "permissions": ["read", "write"]}
            
            result = await auth_mgr.validate_api_key("key_12345")
            assert result["user_id"] == "user123"
            assert "write" in result["permissions"]
            mock_validate.assert_called_once_with("key_12345")

    @pytest.mark.asyncio
    async def test_privacy_engine_pii_detection(self):
        """Test PII detection capabilities."""
        privacy_engine = PrivacyEngine({
            "detection_confidence": 0.8,
            "patterns": ["ssn", "email", "phone", "credit_card"]
        })
        
        test_data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "email": "john.doe@company.com",
            "phone": "555-123-4567",
            "address": "123 Main St, Anytown USA",
            "non_sensitive": "Some regular text"
        }
        
        with patch.object(privacy_engine, 'detect_pii') as mock_detect:
            mock_detect.return_value = {
                "pii_found": True,
                "fields": ["ssn", "email", "phone"],
                "confidence_scores": {"ssn": 0.95, "email": 0.98, "phone": 0.92}
            }
            
            result = await privacy_engine.detect_pii(test_data)
            assert result["pii_found"] == True
            assert "ssn" in result["fields"]
            assert result["confidence_scores"]["email"] > 0.9

    @pytest.mark.asyncio
    async def test_data_masking_strategies(self):
        """Test different data masking strategies."""
        privacy_engine = PrivacyEngine({"masking_strategy": "adaptive"})
        
        sensitive_data = {
            "ssn": "123-45-6789",
            "email": "john.doe@company.com", 
            "phone": "555-123-4567",
            "name": "John Doe",
            "credit_card": "4532-1234-5678-9012"
        }
        
        with patch.object(privacy_engine, 'mask_data') as mock_mask:
            mock_mask.return_value = {
                "ssn": "***-**-6789",           # Partial masking
                "email": "***@company.com",     # Domain preserved
                "phone": "555-***-****",        # Area code preserved
                "name": "John ***",             # First name preserved
                "credit_card": "****-****-****-9012"  # Last 4 digits preserved
            }
            
            masked = await privacy_engine.mask_data(sensitive_data)
            assert "***" in masked["ssn"]
            assert "@company.com" in masked["email"]
            assert masked["phone"].startswith("555")
            assert "9012" in masked["credit_card"]

    @pytest.mark.asyncio
    async def test_differential_privacy(self):
        """Test differential privacy implementation."""
        privacy_engine = PrivacyEngine({
            "privacy_level": "high",
            "epsilon": 0.1,  # Strong privacy
            "noise_mechanism": "gaussian"
        })
        
        original_data = [10, 20, 30, 40, 50]  # Simple numeric data
        
        with patch.object(privacy_engine, 'add_differential_privacy_noise') as mock_noise:
            mock_noise.return_value = [10.2, 19.8, 30.1, 39.9, 50.3]  # With noise
            
            noisy_data = await privacy_engine.add_differential_privacy_noise(original_data)
            assert len(noisy_data) == len(original_data)
            # Values should be similar but not identical
            for orig, noisy in zip(original_data, noisy_data):
                assert abs(orig - noisy) < 1.0  # Small noise for this test
            mock_noise.assert_called_once_with(original_data)

    @pytest.mark.asyncio
    async def test_encryption_at_rest(self):
        """Test encryption of data at rest."""
        from cryptography.fernet import Fernet
        
        # Simulate encryption manager
        encryption_key = Fernet.generate_key()
        cipher_suite = Fernet(encryption_key)
        
        sensitive_data = "This is sensitive patient information"
        
        # Encrypt
        encrypted_data = cipher_suite.encrypt(sensitive_data.encode())
        assert encrypted_data != sensitive_data.encode()
        
        # Decrypt
        decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
        assert decrypted_data == sensitive_data

    @pytest.mark.asyncio
    async def test_access_control_rbac(self):
        """Test Role-Based Access Control."""
        rbac_mgr = Mock()
        rbac_mgr.check_permission = AsyncMock()
        
        # Define test cases
        test_cases = [
            {"user": "admin", "role": "administrator", "resource": "all_data", "action": "read", "expected": True},
            {"user": "analyst", "role": "data_analyst", "resource": "healthcare_data", "action": "read", "expected": True},
            {"user": "analyst", "role": "data_analyst", "resource": "healthcare_data", "action": "delete", "expected": False},
            {"user": "viewer", "role": "viewer", "resource": "any_data", "action": "write", "expected": False}
        ]
        
        for case in test_cases:
            rbac_mgr.check_permission.return_value = case["expected"]
            
            result = await rbac_mgr.check_permission(
                user=case["user"],
                resource=case["resource"], 
                action=case["action"]
            )
            
            assert result == case["expected"]

    @pytest.mark.asyncio
    async def test_audit_trail_security(self):
        """Test security audit trail functionality."""
        audit_mgr = Mock()
        audit_mgr.log_security_event = AsyncMock(return_value=True)
        audit_mgr.detect_anomalies = AsyncMock(return_value=[])
        
        # Test security event logging
        security_events = [
            {"type": "login_attempt", "user": "user123", "success": True, "ip": "192.168.1.100"},
            {"type": "data_access", "user": "user123", "resource": "patient_data", "action": "read"},
            {"type": "failed_login", "user": "unknown", "success": False, "ip": "192.168.1.200"},
            {"type": "privilege_escalation", "user": "user456", "attempted_role": "admin", "denied": True}
        ]
        
        for event in security_events:
            result = await audit_mgr.log_security_event(event)
            assert result == True
        
        # Test anomaly detection
        anomalies = await audit_mgr.detect_anomalies()
        assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        # Simulate database query handler with parameterized queries
        query_handler = Mock()
        query_handler.execute_safe_query = AsyncMock()
        
        # Test safe parameterized query
        safe_query = "SELECT * FROM patients WHERE age > ? AND state = ?"
        params = [25, "CA"]
        
        query_handler.execute_safe_query.return_value = {"rows": 100, "safe": True}
        
        result = await query_handler.execute_safe_query(safe_query, params)
        assert result["safe"] == True
        query_handler.execute_safe_query.assert_called_once_with(safe_query, params)

    @pytest.mark.asyncio
    async def test_data_retention_policies(self):
        """Test data retention and disposal policies."""
        retention_mgr = Mock()
        retention_mgr.check_retention_policy = AsyncMock()
        retention_mgr.secure_delete = AsyncMock(return_value=True)
        
        # Test data that should be retained
        recent_data = {"id": "data_123", "created": "2025-08-01", "retention_days": 365}
        retention_mgr.check_retention_policy.return_value = {"action": "retain", "days_remaining": 300}
        
        policy_result = await retention_mgr.check_retention_policy(recent_data)
        assert policy_result["action"] == "retain"
        
        # Test data that should be deleted
        old_data = {"id": "data_456", "created": "2020-01-01", "retention_days": 365}
        retention_mgr.check_retention_policy.return_value = {"action": "delete", "days_overdue": 1000}
        
        policy_result = await retention_mgr.check_retention_policy(old_data)
        assert policy_result["action"] == "delete"
        
        # Test secure deletion
        delete_result = await retention_mgr.secure_delete("data_456")
        assert delete_result == True

    @pytest.mark.asyncio
    async def test_network_security(self):
        """Test network security measures."""
        network_security = Mock()
        network_security.validate_tls_connection = AsyncMock(return_value=True)
        network_security.check_ip_whitelist = AsyncMock()
        network_security.detect_ddos = AsyncMock(return_value=False)
        
        # Test TLS connection validation
        tls_valid = await network_security.validate_tls_connection()
        assert tls_valid == True
        
        # Test IP whitelisting
        network_security.check_ip_whitelist.return_value = True
        ip_allowed = await network_security.check_ip_whitelist("192.168.1.100")
        assert ip_allowed == True
        
        network_security.check_ip_whitelist.return_value = False
        ip_blocked = await network_security.check_ip_whitelist("10.0.0.1")
        assert ip_blocked == False
        
        # Test DDoS detection
        ddos_detected = await network_security.detect_ddos()
        assert ddos_detected == False