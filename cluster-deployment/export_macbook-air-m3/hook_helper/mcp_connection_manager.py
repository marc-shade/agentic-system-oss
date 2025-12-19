#!/usr/bin/env python3
"""
MCP Connection Manager with Exponential Backoff
Implements 12-factor app principles for backing services
"""

import os
import time
import json
import random
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

class MCPConnectionManager:
    """Manages MCP connections with retry logic and health checks"""
    
    def __init__(self):
        self.load_config()
        self.connection_cache = {}
        self.health_status = {}
        self.last_health_check = {}
        
    def load_config(self):
        """Load configuration from services.env"""
        env_path = Path.home() / '.claude' / 'services.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        # Expand environment variables
                        value = os.path.expandvars(value)
                        os.environ[key] = value
        
        # Load retry configuration
        self.max_attempts = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
        self.backoff_base = int(os.getenv('RETRY_BACKOFF_BASE', '2'))
        self.max_delay = int(os.getenv('RETRY_MAX_DELAY', '30'))
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        self.health_check_timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '5'))
        
    def connect_with_retry(self, service_name: str, endpoint: str) -> Optional[Dict]:
        """
        Connect to MCP service with exponential backoff retry
        Factor 4: Treating backing services as attached resources
        """
        attempt = 0
        delay = 1
        
        while attempt < self.max_attempts:
            try:
                # Attempt connection
                result = self._attempt_connection(service_name, endpoint)
                
                if result:
                    self.connection_cache[service_name] = {
                        'endpoint': endpoint,
                        'connected_at': datetime.now().isoformat(),
                        'attempts': attempt + 1
                    }
                    self.health_status[service_name] = 'healthy'
                    print(f"✓ Connected to {service_name} after {attempt + 1} attempts")
                    return result
                    
            except Exception as e:
                attempt += 1
                if attempt >= self.max_attempts:
                    self.health_status[service_name] = 'unhealthy'
                    print(f"✗ Failed to connect to {service_name} after {self.max_attempts} attempts: {e}")
                    return None
                
                # Exponential backoff with jitter
                delay = min(self.backoff_base ** attempt + random.uniform(0, 1), self.max_delay)
                print(f"⟳ Retrying {service_name} in {delay:.1f}s (attempt {attempt}/{self.max_attempts})")
                time.sleep(delay)
        
        return None
    
    def _attempt_connection(self, service_name: str, endpoint: str) -> Optional[Dict]:
        """Simulate connection attempt (replace with actual MCP connection logic)"""
        # This would be replaced with actual MCP connection code
        # For now, simulate with a success probability
        if random.random() > 0.3:  # 70% success rate for demo
            return {'service': service_name, 'status': 'connected'}
        raise ConnectionError(f"Failed to connect to {endpoint}")
    
    def health_check(self, service_name: str) -> bool:
        """
        Perform health check on MCP service
        Factor 8: Concurrency - ensuring services are ready
        """
        last_check = self.last_health_check.get(service_name)
        now = datetime.now()
        
        # Skip if checked recently
        if last_check and (now - last_check).seconds < self.health_check_interval:
            return self.health_status.get(service_name) == 'healthy'
        
        # Perform health check
        try:
            endpoint = self.connection_cache.get(service_name, {}).get('endpoint')
            if endpoint:
                # Simulate health check (replace with actual check)
                is_healthy = random.random() > 0.1  # 90% healthy for demo
                self.health_status[service_name] = 'healthy' if is_healthy else 'degraded'
                self.last_health_check[service_name] = now
                return is_healthy
        except Exception as e:
            self.health_status[service_name] = 'unhealthy'
            print(f"Health check failed for {service_name}: {e}")
        
        return False
    
    def get_service_endpoint(self, service_name: str) -> str:
        """Get service endpoint from environment configuration"""
        # Map service names to environment variables
        service_map = {
            'claude-flow': 'CLAUDE_FLOW_PORT',
            'enhanced-memory': 'ENHANCED_MEMORY_PORT',
            'voice-mode': 'VOICE_MODE_PORT',
            'chatterbox': 'CHATTERBOX_ENDPOINT',
            'whisper': 'WHISPER_ENDPOINT'
        }
        
        if service_name in ['chatterbox', 'whisper']:
            return os.getenv(service_map[service_name], '')
        
        port = os.getenv(service_map.get(service_name, ''), '3000')
        return f"http://localhost:{port}"
    
    def graceful_disconnect(self, service_name: str):
        """
        Gracefully disconnect from service
        Factor 9: Disposability - graceful shutdown
        """
        if service_name in self.connection_cache:
            print(f"↓ Gracefully disconnecting from {service_name}")
            # Perform cleanup tasks here
            del self.connection_cache[service_name]
            if service_name in self.health_status:
                del self.health_status[service_name]
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report of all services"""
        return {
            'timestamp': datetime.now().isoformat(),
            'connections': self.connection_cache,
            'health': self.health_status,
            'config': {
                'max_attempts': self.max_attempts,
                'backoff_base': self.backoff_base,
                'max_delay': self.max_delay,
                'health_check_interval': self.health_check_interval
            }
        }

# Hook integration
def on_mcp_connect(service_name: str):
    """Hook called when attempting MCP connection"""
    manager = MCPConnectionManager()
    endpoint = manager.get_service_endpoint(service_name)
    return manager.connect_with_retry(service_name, endpoint)

def on_mcp_health_check(service_name: str):
    """Hook called for MCP health checks"""
    manager = MCPConnectionManager()
    return manager.health_check(service_name)

def on_shutdown():
    """Hook called on graceful shutdown"""
    manager = MCPConnectionManager()
    for service in list(manager.connection_cache.keys()):
        manager.graceful_disconnect(service)

if __name__ == "__main__":
    # Demo the connection manager
    manager = MCPConnectionManager()
    
    # Test connections with retry
    services = ['claude-flow', 'enhanced-memory', 'voice-mode', 'chatterbox', 'whisper']
    
    print("Testing MCP Connection Manager with Exponential Backoff\n")
    for service in services:
        endpoint = manager.get_service_endpoint(service)
        print(f"\nConnecting to {service} at {endpoint}")
        manager.connect_with_retry(service, endpoint)
    
    print("\n" + "="*50)
    print("Status Report:")
    print(json.dumps(manager.get_status_report(), indent=2))