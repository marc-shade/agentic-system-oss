#!/usr/bin/env python3
"""
MCP Health Monitor - Continuous health checking for backing services
Implements Factor 4 (Backing Services) and Factor 11 (Logs)
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class MCPHealthMonitor:
    """Monitor health of MCP services continuously"""
    
    def __init__(self):
        self.load_config()
        self.services = self.discover_services()
        self.health_history = []
        self.alert_thresholds = {
            'consecutive_failures': 3,
            'degraded_threshold': 0.7,  # 70% success rate
            'critical_threshold': 0.5    # 50% success rate
        }
        
    def load_config(self):
        """Load configuration from services.env"""
        env_path = Path.home() / '.claude' / 'services.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        self.check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        self.timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '5'))
        
    def discover_services(self) -> Dict[str, Dict]:
        """Discover MCP services from configuration"""
        services = {}
        
        # Core MCP services (Tier 0)
        core_services = {
            'claude-flow': {
                'port': os.getenv('CLAUDE_FLOW_PORT', '3000'),
                'critical': True,
                'check_endpoint': '/health'
            },
            'enhanced-memory': {
                'port': os.getenv('ENHANCED_MEMORY_PORT', '3001'),
                'critical': True,
                'check_endpoint': '/health'
            },
            'voice-mode': {
                'port': os.getenv('VOICE_MODE_PORT', '3002'),
                'critical': True,
                'check_endpoint': '/health'
            }
        }
        
        # Voice services
        voice_services = {
            'chatterbox': {
                'endpoint': os.getenv('CHATTERBOX_ENDPOINT', 'http://127.0.0.1:8880'),
                'critical': False,
                'check_endpoint': '/health'
            },
            'whisper': {
                'endpoint': os.getenv('WHISPER_ENDPOINT', 'http://127.0.0.1:2022'),
                'critical': False,
                'check_endpoint': '/health'
            }
        }
        
        # Combine all services
        for name, config in core_services.items():
            services[name] = {
                'endpoint': f"http://localhost:{config['port']}",
                'critical': config['critical'],
                'check_endpoint': config['check_endpoint']
            }
        
        services.update(voice_services)
        return services
    
    def check_service_health(self, name: str, config: Dict) -> Tuple[str, Dict]:
        """Check health of a single service"""
        endpoint = config['endpoint']
        check_url = endpoint + config.get('check_endpoint', '/health')
        
        try:
            # Use curl for health check (cross-platform)
            result = subprocess.run(
                ['curl', '-s', '-f', '-m', str(self.timeout), check_url],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return 'healthy', {
                    'status': 'healthy',
                    'response_time': time.time(),
                    'message': 'Service responding normally'
                }
            else:
                return 'unhealthy', {
                    'status': 'unhealthy',
                    'error': result.stderr or 'Health check failed',
                    'response_time': time.time()
                }
                
        except subprocess.SubprocessError as e:
            return 'unknown', {
                'status': 'unknown',
                'error': str(e),
                'response_time': time.time()
            }
        except FileNotFoundError:
            # curl not available, try basic Python check
            return self._python_health_check(name, check_url)
    
    def _python_health_check(self, name: str, url: str) -> Tuple[str, Dict]:
        """Fallback Python-based health check"""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return 'healthy', {
                        'status': 'healthy',
                        'response_time': time.time(),
                        'message': 'Service responding'
                    }
        except Exception as e:
            return 'unhealthy', {
                'status': 'unhealthy',
                'error': str(e),
                'response_time': time.time()
            }
    
    async def monitor_continuously(self):
        """Run continuous health monitoring"""
        print(f"Starting MCP Health Monitor (checking every {self.check_interval}s)")
        print("="*60)
        
        while True:
            report = await self.check_all_services()
            self.display_report(report)
            self.check_alerts(report)
            
            # Store history (keep last 100 checks)
            self.health_history.append(report)
            if len(self.health_history) > 100:
                self.health_history.pop(0)
            
            await asyncio.sleep(self.check_interval)
    
    async def check_all_services(self) -> Dict:
        """Check health of all services"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'summary': {
                'total': len(self.services),
                'healthy': 0,
                'unhealthy': 0,
                'unknown': 0
            }
        }
        
        for name, config in self.services.items():
            status, details = self.check_service_health(name, config)
            report['services'][name] = details
            report['summary'][status] += 1
        
        # Calculate health score
        if report['summary']['total'] > 0:
            report['health_score'] = report['summary']['healthy'] / report['summary']['total']
        else:
            report['health_score'] = 0.0
        
        return report
    
    def display_report(self, report: Dict):
        """Display health report to stdout (Factor 11: Logs)"""
        timestamp = datetime.fromisoformat(report['timestamp']).strftime('%H:%M:%S')
        health_score = report['health_score']
        
        # Clear previous line for compact display
        print(f"\r[{timestamp}] Health: {health_score:.0%} | ", end='')
        
        # Show service status indicators
        for name, details in report['services'].items():
            status = details['status']
            indicator = '●' if status == 'healthy' else '○' if status == 'unknown' else '✗'
            color = '\033[92m' if status == 'healthy' else '\033[93m' if status == 'unknown' else '\033[91m'
            print(f"{color}{name}:{indicator}\033[0m ", end='')
        
        # Log to file if configured
        if os.getenv('LOG_TO_STDOUT', 'true').lower() == 'true':
            sys.stdout.flush()
    
    def check_alerts(self, report: Dict):
        """Check for alert conditions"""
        health_score = report['health_score']
        
        # Critical alert
        if health_score < self.alert_thresholds['critical_threshold']:
            self.send_alert('CRITICAL', f"System health critical: {health_score:.0%}")
        
        # Degraded alert
        elif health_score < self.alert_thresholds['degraded_threshold']:
            self.send_alert('WARNING', f"System health degraded: {health_score:.0%}")
        
        # Check critical services
        for name, details in report['services'].items():
            if self.services[name].get('critical') and details['status'] != 'healthy':
                self.send_alert('CRITICAL', f"Critical service {name} is {details['status']}")
    
    def send_alert(self, level: str, message: str):
        """Send alert (would integrate with notification system)"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        alert_msg = f"\n[{timestamp}] {level}: {message}"
        
        # Log alert
        print(alert_msg)
        
        # Write to alert file
        alert_file = Path.home() / '.claude' / 'mcp_alerts.log'
        with open(alert_file, 'a') as f:
            f.write(alert_msg + '\n')
    
    def get_health_summary(self) -> Dict:
        """Get summary of health history"""
        if not self.health_history:
            return {'message': 'No health data available'}
        
        # Calculate averages
        total_checks = len(self.health_history)
        avg_health = sum(r['health_score'] for r in self.health_history) / total_checks
        
        # Service-specific stats
        service_stats = {}
        for service in self.services:
            healthy_count = sum(
                1 for r in self.health_history 
                if r['services'].get(service, {}).get('status') == 'healthy'
            )
            service_stats[service] = {
                'uptime': healthy_count / total_checks,
                'total_checks': total_checks
            }
        
        return {
            'average_health': avg_health,
            'total_checks': total_checks,
            'service_stats': service_stats,
            'current_status': self.health_history[-1] if self.health_history else None
        }

def main():
    """Main entry point for health monitor"""
    monitor = MCPHealthMonitor()
    
    # Run monitoring
    try:
        asyncio.run(monitor.monitor_continuously())
    except KeyboardInterrupt:
        print("\n\nHealth monitoring stopped")
        summary = monitor.get_health_summary()
        print(f"\nHealth Summary:")
        print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()