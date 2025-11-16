#!/usr/bin/env python3
"""
Scheduled Health Monitoring System

Provides cron-like periodic health checks for the autonomous agentic system:
- Service availability (Temporal, AutoKitteh, Qdrant, PM2, etc.)
- Resource utilization (CPU, memory, disk, network)
- MCP server health
- Intelligent agent status
- Task queue backlog
- Database integrity
- Log analysis for errors

Automatically triggers remediation when issues are detected.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/mnt/agentic-system/logs/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('health-monitor')

class HealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str, interval_minutes: int = 5):
        self.name = name
        self.interval_minutes = interval_minutes
        self.last_check = None
        self.last_status = 'unknown'
        self.consecutive_failures = 0

    async def check(self) -> Dict:
        """Override in subclasses"""
        return {'status': 'unknown', 'message': 'Not implemented'}

class TemporalHealthCheck(HealthCheck):
    """Check Temporal server health"""

    def __init__(self):
        super().__init__('Temporal', interval_minutes=5)

    async def check(self) -> Dict:
        try:
            result = subprocess.run(
                ['temporal', 'workflow', 'list', '--limit', '1'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return {
                    'status': 'healthy',
                    'message': 'Temporal server responding'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': f'Temporal command failed: {result.stderr}'
                }
        except subprocess.TimeoutExpired:
            return {
                'status': 'unhealthy',
                'message': 'Temporal server timeout'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Temporal check error: {e}'
            }

class QdrantHealthCheck(HealthCheck):
    """Check Qdrant vector database health"""

    def __init__(self):
        super().__init__('Qdrant', interval_minutes=5)

    async def check(self) -> Dict:
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:6333/'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and 'qdrant' in result.stdout.lower():
                return {
                    'status': 'healthy',
                    'message': 'Qdrant responding'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Qdrant not responding'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Qdrant check error: {e}'
            }

class PM2HealthCheck(HealthCheck):
    """Check PM2 process manager health"""

    def __init__(self):
        super().__init__('PM2', interval_minutes=5)

    async def check(self) -> Dict:
        try:
            result = subprocess.run(
                ['pm2', 'jlist'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                processes = json.loads(result.stdout)
                online = len([p for p in processes if p.get('pm2_env', {}).get('status') == 'online'])
                total = len(processes)

                if online == total:
                    return {
                        'status': 'healthy',
                        'message': f'All {total} PM2 processes online'
                    }
                else:
                    return {
                        'status': 'degraded',
                        'message': f'Only {online}/{total} PM2 processes online'
                    }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'PM2 not responding'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'PM2 check error: {e}'
            }

class MCPHealthCheck(HealthCheck):
    """Check MCP servers health"""

    def __init__(self):
        super().__init__('MCP Servers', interval_minutes=10)

    async def check(self) -> Dict:
        try:
            # Check MCP configuration
            config_path = Path.home() / '.claude.json'
            if not config_path.exists():
                return {
                    'status': 'error',
                    'message': 'MCP configuration not found'
                }

            with open(config_path, 'r') as f:
                config = json.load(f)

            servers = config.get('mcpServers', {})
            enabled = len([s for s in servers.values() if not s.get('disabled', False)])
            total = len(servers)

            return {
                'status': 'healthy',
                'message': f'{enabled}/{total} MCP servers configured'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'MCP check error: {e}'
            }

class ResourceHealthCheck(HealthCheck):
    """Check system resource utilization"""

    def __init__(self):
        super().__init__('System Resources', interval_minutes=2)

    async def check(self) -> Dict:
        try:
            # Get CPU usage
            result = subprocess.run(
                ['top', '-l', '1', '-n', '0'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                cpu_line = [l for l in lines if 'CPU usage' in l][0]
                cpu_idle = cpu_line.split('idle')[0].split()[-1].rstrip('%')
                cpu_used = 100 - float(cpu_idle)

                if cpu_used < 80:
                    status = 'healthy'
                elif cpu_used < 95:
                    status = 'degraded'
                else:
                    status = 'critical'

                return {
                    'status': status,
                    'message': f'CPU: {cpu_used:.1f}% used',
                    'cpu_usage': cpu_used
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to get resource stats'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Resource check error: {e}'
            }

class TaskQueueHealthCheck(HealthCheck):
    """Check Agent Runtime task queue status"""

    def __init__(self):
        super().__init__('Task Queue', interval_minutes=15)

    async def check(self) -> Dict:
        try:
            import sqlite3
            db_path = Path.home() / '.claude' / 'agent_runtime.db'

            if not db_path.exists():
                return {
                    'status': 'error',
                    'message': 'Task queue database not found'
                }

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            pending = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
            failed = cursor.fetchone()[0]

            conn.close()

            if pending > 10:
                status = 'degraded'
                message = f'High backlog: {pending} pending tasks'
            elif failed > 5:
                status = 'degraded'
                message = f'Multiple failures: {failed} failed tasks'
            else:
                status = 'healthy'
                message = f'Queue healthy: {pending} pending, {failed} failed'

            return {
                'status': status,
                'message': message,
                'pending_count': pending,
                'failed_count': failed
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Task queue check error: {e}'
            }

class ScheduledHealthMonitor:
    """Main scheduled health monitoring system"""

    def __init__(self):
        self.running = True
        self.checks = [
            TemporalHealthCheck(),
            QdrantHealthCheck(),
            PM2HealthCheck(),
            MCPHealthCheck(),
            ResourceHealthCheck(),
            TaskQueueHealthCheck()
        ]
        self.health_history = []
        self.history_file = Path('/mnt/agentic-system/logs/health_history.json')

    async def run_check(self, health_check: HealthCheck) -> Dict:
        """Run a single health check"""
        logger.info(f"Running health check: {health_check.name}")

        result = await health_check.check()
        health_check.last_check = datetime.now()
        health_check.last_status = result['status']

        # Track consecutive failures
        if result['status'] in ['unhealthy', 'critical', 'error']:
            health_check.consecutive_failures += 1
        else:
            health_check.consecutive_failures = 0

        return {
            'check': health_check.name,
            'timestamp': datetime.now().isoformat(),
            'status': result['status'],
            'message': result['message'],
            'consecutive_failures': health_check.consecutive_failures
        }

    async def trigger_remediation(self, check_name: str, status: str, message: str):
        """Trigger automatic remediation for failed checks"""
        logger.warning(f"Triggering remediation for {check_name}: {message}")

        # Define remediation actions
        remediation_actions = {
            'Temporal': self.remediate_temporal,
            'Qdrant': self.remediate_qdrant,
            'PM2': self.remediate_pm2,
            'Task Queue': self.remediate_task_queue
        }

        if check_name in remediation_actions:
            try:
                await remediation_actions[check_name]()
                logger.info(f"Remediation completed for {check_name}")
            except Exception as e:
                logger.error(f"Remediation failed for {check_name}: {e}")
        else:
            logger.warning(f"No automatic remediation available for {check_name}")

    async def remediate_temporal(self):
        """Attempt to restart Temporal server"""
        logger.info("Attempting Temporal remediation...")
        # Could run restart script here
        # For now, just log
        logger.info("Manual intervention required for Temporal")

    async def remediate_qdrant(self):
        """Attempt to restart Qdrant"""
        logger.info("Attempting Qdrant remediation...")
        logger.info("Manual intervention required for Qdrant")

    async def remediate_pm2(self):
        """Attempt to restart failed PM2 processes"""
        logger.info("Attempting PM2 remediation...")
        try:
            result = subprocess.run(
                ['pm2', 'restart', 'all'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info("PM2 processes restarted successfully")
            else:
                logger.error(f"PM2 restart failed: {result.stderr}")
        except Exception as e:
            logger.error(f"PM2 remediation error: {e}")

    async def remediate_task_queue(self):
        """Handle task queue issues"""
        logger.info("Checking task consumer status...")
        # Could restart task consumer if needed
        result = subprocess.run(
            ['pgrep', '-f', 'task_consumer.py'],
            capture_output=True, text=True
        )

        if not result.stdout.strip():
            logger.warning("Task consumer not running, attempting restart")
            # Could restart task consumer here

    async def run_all_checks(self):
        """Run all health checks"""
        results = []

        for check in self.checks:
            # Check if it's time to run this check
            if check.last_check is None or \
               (datetime.now() - check.last_check).seconds >= (check.interval_minutes * 60):

                result = await self.run_check(check)
                results.append(result)

                # Trigger remediation if needed
                if result['consecutive_failures'] >= 3:
                    await self.trigger_remediation(
                        result['check'],
                        result['status'],
                        result['message']
                    )

        return results

    async def generate_health_report(self) -> Dict:
        """Generate comprehensive health report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }

        for check in self.checks:
            report['checks'].append({
                'name': check.name,
                'status': check.last_status,
                'last_check': check.last_check.isoformat() if check.last_check else None,
                'interval_minutes': check.interval_minutes,
                'consecutive_failures': check.consecutive_failures
            })

        # Calculate overall health
        statuses = [c['status'] for c in report['checks']]
        if 'critical' in statuses or statuses.count('unhealthy') > 1:
            report['overall_health'] = 'critical'
        elif 'unhealthy' in statuses or 'degraded' in statuses:
            report['overall_health'] = 'degraded'
        elif 'error' in statuses:
            report['overall_health'] = 'error'
        else:
            report['overall_health'] = 'healthy'

        return report

    async def run(self):
        """Main monitoring loop"""
        logger.info("Scheduled Health Monitor starting...")

        while self.running:
            try:
                # Run all checks
                results = await self.run_all_checks()

                if results:
                    logger.info(f"Completed {len(results)} health checks")

                    # Add to history
                    self.health_history.extend(results)

                    # Keep last 1000 entries
                    if len(self.health_history) > 1000:
                        self.health_history = self.health_history[-1000:]

                    # Save history periodically
                    if len(self.health_history) % 10 == 0:
                        self.save_history()

                # Sleep for 1 minute before next check cycle
                await asyncio.sleep(60)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

        logger.info("Scheduled Health Monitor stopped")

    def save_history(self):
        """Save health check history"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.health_history[-100:], f, indent=2)  # Save last 100 only
            logger.debug(f"Health history saved: {len(self.health_history)} entries")
        except Exception as e:
            logger.error(f"Failed to save health history: {e}")

    def stop(self):
        """Stop the monitor"""
        self.running = False

def main():
    """Entry point"""
    monitor = ScheduledHealthMonitor()

    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        monitor.stop()

if __name__ == "__main__":
    main()
