#!/usr/bin/env python3
"""
Token Rotation Manager - Implements Factor 13 (Identity)
Short-lived tokens with automatic rotation for MCP authentication
"""

import os
import json
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

class TokenRotationManager:
    """Manages short-lived tokens for MCP authentication"""
    
    def __init__(self):
        self.load_config()
        self.token_store_path = Path.home() / '.claude' / '.tokens'
        self.token_store_path.mkdir(exist_ok=True)
        self.active_tokens = {}
        self.token_permissions = {}
        self.load_existing_tokens()
        
    def load_config(self):
        """Load configuration from services.env"""
        env_path = Path.home() / '.claude' / 'services.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        # Token configuration
        self.rotation_interval = int(os.getenv('TOKEN_ROTATION_INTERVAL', '3600'))  # 1 hour
        self.refresh_threshold = int(os.getenv('TOKEN_REFRESH_THRESHOLD', '300'))   # 5 minutes
        self.use_short_lived = os.getenv('USE_SHORT_LIVED_TOKENS', 'true').lower() == 'true'
        
    def load_existing_tokens(self):
        """Load existing tokens from secure storage"""
        token_file = self.token_store_path / 'active_tokens.json'
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    # Validate tokens aren't expired
                    for service, token_data in data.items():
                        if self.is_token_valid(token_data):
                            self.active_tokens[service] = token_data
            except Exception as e:
                print(f"Error loading tokens: {e}")
                self.active_tokens = {}
    
    def save_tokens(self):
        """Save tokens to secure storage"""
        token_file = self.token_store_path / 'active_tokens.json'
        # Set restrictive permissions (owner read/write only)
        with open(token_file, 'w') as f:
            json.dump(self.active_tokens, f, indent=2)
        os.chmod(token_file, 0o600)
    
    def generate_token(self, service_name: str, scopes: list = None) -> str:
        """Generate a new short-lived token"""
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)
        
        # Create token metadata
        token_data = {
            'token': self.hash_token(token),
            'service': service_name,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=self.rotation_interval)).isoformat(),
            'scopes': scopes or self.get_default_scopes(service_name),
            'token_id': secrets.token_hex(8)
        }
        
        # Store token
        self.active_tokens[service_name] = token_data
        self.save_tokens()
        
        # Log token generation (Factor 11: Logs)
        print(f"✓ Generated token for {service_name} (expires: {token_data['expires_at']})")
        
        return token
    
    def hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def get_default_scopes(self, service_name: str) -> list:
        """Get default scopes based on service type (Least Privilege)"""
        scope_map = {
            'claude-flow': ['orchestrate', 'spawn', 'monitor'],
            'enhanced-memory': ['read', 'write', 'search'],
            'voice-mode': ['tts', 'stt', 'converse'],
            'task-manager': ['create', 'update', 'prioritize'],
            'admin': ['all']  # Admin gets full access
        }
        
        # Match service to scope pattern
        for pattern, scopes in scope_map.items():
            if pattern in service_name.lower():
                return scopes
        
        # Default minimal scopes
        return ['read']
    
    def rotate_token(self, service_name: str) -> Tuple[str, bool]:
        """Rotate token for a service"""
        old_token_data = self.active_tokens.get(service_name)
        
        # Generate new token
        new_token = self.generate_token(
            service_name,
            old_token_data['scopes'] if old_token_data else None
        )
        
        # Grace period for old token (30 seconds)
        if old_token_data:
            old_token_data['grace_expires_at'] = (
                datetime.now() + timedelta(seconds=30)
            ).isoformat()
            self.active_tokens[f"{service_name}_old"] = old_token_data
        
        print(f"⟳ Rotated token for {service_name}")
        return new_token, True
    
    def is_token_valid(self, token_data: Dict) -> bool:
        """Check if token is still valid"""
        if not token_data:
            return False
        
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        return datetime.now() < expires_at
    
    def needs_refresh(self, service_name: str) -> bool:
        """Check if token needs refresh"""
        token_data = self.active_tokens.get(service_name)
        if not token_data:
            return True
        
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        time_until_expiry = (expires_at - datetime.now()).total_seconds()
        
        return time_until_expiry < self.refresh_threshold
    
    def get_token(self, service_name: str) -> Optional[str]:
        """Get valid token for service, rotating if necessary"""
        if self.needs_refresh(service_name):
            token, _ = self.rotate_token(service_name)
            return token
        
        token_data = self.active_tokens.get(service_name)
        if token_data and self.is_token_valid(token_data):
            return token_data.get('token')
        
        # Generate new token if none exists
        return self.generate_token(service_name)
    
    def revoke_token(self, service_name: str):
        """Revoke token for a service"""
        if service_name in self.active_tokens:
            del self.active_tokens[service_name]
            self.save_tokens()
            print(f"✗ Revoked token for {service_name}")
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from storage"""
        expired = []
        for service, token_data in self.active_tokens.items():
            if not self.is_token_valid(token_data):
                expired.append(service)
        
        for service in expired:
            del self.active_tokens[service]
        
        if expired:
            self.save_tokens()
            print(f"🧹 Cleaned up {len(expired)} expired tokens")
    
    def get_token_report(self) -> Dict:
        """Get report of all active tokens"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'rotation_interval': self.rotation_interval,
                'refresh_threshold': self.refresh_threshold,
                'use_short_lived': self.use_short_lived
            },
            'tokens': {}
        }
        
        for service, token_data in self.active_tokens.items():
            if '_old' not in service:  # Skip grace period tokens
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                time_remaining = (expires_at - datetime.now()).total_seconds()
                
                report['tokens'][service] = {
                    'token_id': token_data.get('token_id'),
                    'created_at': token_data['created_at'],
                    'expires_at': token_data['expires_at'],
                    'time_remaining': f"{time_remaining:.0f}s",
                    'scopes': token_data.get('scopes', []),
                    'needs_refresh': self.needs_refresh(service)
                }
        
        return report

# Hook integration functions
def on_mcp_authenticate(service_name: str) -> str:
    """Hook called when MCP needs authentication"""
    manager = TokenRotationManager()
    return manager.get_token(service_name)

def on_token_refresh(service_name: str) -> str:
    """Hook called to refresh token"""
    manager = TokenRotationManager()
    token, _ = manager.rotate_token(service_name)
    return token

def on_service_disconnect(service_name: str):
    """Hook called when service disconnects"""
    manager = TokenRotationManager()
    manager.revoke_token(service_name)

def periodic_cleanup():
    """Periodic cleanup task"""
    manager = TokenRotationManager()
    manager.cleanup_expired_tokens()

if __name__ == "__main__":
    # Demo the token rotation manager
    manager = TokenRotationManager()
    
    print("Token Rotation Manager Demo")
    print("="*50)
    
    # Generate tokens for services
    services = ['claude-flow', 'enhanced-memory', 'voice-mode', 'admin']
    
    print("\n1. Generating tokens for services:")
    for service in services:
        token = manager.generate_token(service)
        print(f"   {service}: {token[:16]}...")
    
    print("\n2. Token Report:")
    report = manager.get_token_report()
    print(json.dumps(report, indent=2))
    
    print("\n3. Testing rotation:")
    time.sleep(2)
    token, rotated = manager.rotate_token('claude-flow')
    print(f"   New token: {token[:16]}...")
    
    print("\n4. Cleanup:")
    manager.cleanup_expired_tokens()
    
    print("\n✓ Token rotation system operational")