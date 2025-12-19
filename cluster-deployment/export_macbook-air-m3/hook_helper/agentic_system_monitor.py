#!/usr/bin/env python3
"""
Agentic System Monitor - Continuous health monitoring and auto-recovery
"""

import time
import json
import sqlite3
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/marc/.claude/agentic-system-monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgenticSystemMonitor:
    def __init__(self):
        self.persistence_dir = Path("/Users/marc/.claude/agentic-evolution")
        self.pid_file = self.persistence_dir / "mcp_bridge.pid"
        self.health_check_interval = 30  # seconds
        self.restart_cooldown = 300  # 5 minutes between restarts
        self.last_restart = datetime.min
        
    def check_process_health(self, pid: int) -> bool:
        """Check if a process is running"""
        try:
            result = subprocess.run(['ps', '-p', str(pid)], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def get_mcp_bridge_pid(self) -> int:
        """Get the PID of the MCP bridge process"""
        try:
            if self.pid_file.exists():
                return int(self.pid_file.read_text().strip())
            return 0
        except:
            return 0
    
    def check_database_health(self) -> dict:
        """Check health of all databases"""
        health = {}
        
        databases = {
            'events': 'events.db',
            'blackboard': 'blackboard.db', 
            'credit': 'credit.db',
            'learning': 'learning.db'
        }
        
        for name, db_file in databases.items():
            db_path = self.persistence_dir / db_file
            try:
                if db_path.exists():
                    conn = sqlite3.connect(db_path, timeout=5)
                    conn.execute("SELECT 1")
                    conn.close()
                    health[name] = True
                else:
                    health[name] = False
            except Exception as e:
                logger.error(f"Database {name} health check failed: {e}")
                health[name] = False
        
        return health
    
    def get_system_metrics(self) -> dict:
        """Collect comprehensive system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'mcp_bridge': {
                'pid': self.get_mcp_bridge_pid(),
                'running': False,
                'uptime': 0
            },
            'databases': self.check_database_health(),
            'event_stats': {},
            'knowledge_stats': {},
            'learning_stats': {}
        }
        
        # Check MCP bridge process
        pid = metrics['mcp_bridge']['pid']
        if pid > 0:
            metrics['mcp_bridge']['running'] = self.check_process_health(pid)
        
        # Get event bus statistics
        try:
            events_db = self.persistence_dir / "events.db"
            if events_db.exists():
                conn = sqlite3.connect(events_db)
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                metrics['event_stats']['total_events'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM events WHERE processed = 0")
                metrics['event_stats']['pending_events'] = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT type, COUNT(*) 
                    FROM events 
                    WHERE timestamp > datetime('now', '-1 hour')
                    GROUP BY type 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 5
                """)
                metrics['event_stats']['recent_event_types'] = dict(cursor.fetchall())
                
                conn.close()
        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
        
        # Get knowledge graph statistics
        try:
            blackboard_db = self.persistence_dir / "blackboard.db"
            if blackboard_db.exists():
                conn = sqlite3.connect(blackboard_db)
                cursor = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE active = 1")
                metrics['knowledge_stats']['active_nodes'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM knowledge_edges")
                metrics['knowledge_stats']['total_edges'] = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT type, COUNT(*) 
                    FROM knowledge_nodes 
                    WHERE active = 1 
                    GROUP BY type
                """)
                metrics['knowledge_stats']['nodes_by_type'] = dict(cursor.fetchall())
                
                conn.close()
        except Exception as e:
            logger.error(f"Failed to get knowledge statistics: {e}")
        
        return metrics
    
    def restart_mcp_bridge(self) -> bool:
        """Restart the MCP bridge if needed"""
        now = datetime.now()
        if now - self.last_restart < timedelta(seconds=self.restart_cooldown):
            logger.warning("Restart cooldown active, skipping restart")
            return False
        
        try:
            logger.info("Restarting MCP bridge...")
            
            # Kill existing process if running
            pid = self.get_mcp_bridge_pid()
            if pid > 0 and self.check_process_health(pid):
                subprocess.run(['kill', str(pid)])
                time.sleep(2)
            
            # Start new process
            bridge_process = subprocess.Popen([
                "/Users/marc/Documents/Cline/MCP/.unified_environments/base_mcp/venv/bin/python",
                "/Users/marc/agentic-evolution/mcp_bridge.py"
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/Users/marc/agentic-evolution"
            )
            
            # Save new PID
            self.pid_file.write_text(str(bridge_process.pid))
            self.last_restart = now
            
            logger.info(f"MCP bridge restarted with PID: {bridge_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart MCP bridge: {e}")
            return False
    
    def send_voice_alert(self, message: str):
        """Send voice alert about system issues"""
        try:
            response = requests.post('http://127.0.0.1:8880/v1/audio/speech', 
                json={
                    'model': 'tts-1',
                    'input': f"Agentic system alert: {message}",
                    'voice': 'nova'
                },
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            logger.info("Voice alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send voice alert: {e}")
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        logger.info("Starting agentic system health check...")
        
        metrics = self.get_system_metrics()
        
        # Check for critical issues
        critical_issues = []
        
        # Check MCP bridge
        if not metrics['mcp_bridge']['running']:
            critical_issues.append("MCP bridge not running")
        
        # Check databases
        failed_dbs = [name for name, healthy in metrics['databases'].items() if not healthy]
        if failed_dbs:
            critical_issues.append(f"Database issues: {', '.join(failed_dbs)}")
        
        # Log current status
        logger.info(f"System metrics: {json.dumps(metrics, indent=2)}")
        
        # Handle critical issues
        if critical_issues:
            issue_summary = "; ".join(critical_issues)
            logger.error(f"Critical issues detected: {issue_summary}")
            
            # Try to restart MCP bridge if needed
            if "MCP bridge not running" in critical_issues:
                if self.restart_mcp_bridge():
                    logger.info("MCP bridge restart successful")
                    self.send_voice_alert("MCP bridge restarted successfully")
                else:
                    logger.error("MCP bridge restart failed")
                    self.send_voice_alert("MCP bridge restart failed - manual intervention required")
        else:
            logger.info("✅ All agentic system components healthy")
        
        # Save metrics to file for external monitoring
        metrics_file = self.persistence_dir / "system_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Agentic System Monitor started")
        
        # Ensure persistence directory exists
        self.persistence_dir.mkdir(exist_ok=True)
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(self.health_check_interval)
                
        except KeyboardInterrupt:
            logger.info("Monitor shutdown requested")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            self.send_voice_alert("Agentic system monitor encountered an error")
        finally:
            logger.info("🛑 Agentic System Monitor stopped")

if __name__ == "__main__":
    monitor = AgenticSystemMonitor()
    monitor.run()