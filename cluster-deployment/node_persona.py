#!/usr/bin/env python3
"""
Node Persona System
Defines distinct AI personas for each cluster node with full environmental
and situational awareness.

Each node has:
- Unique personality and communication style
- Complete awareness of local system state
- Real-time cluster situational awareness
- Role-specific behaviors and priorities
"""

import os
import sys
import json
import sqlite3
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class NodePersona:
    """Base class for node AI personas with environmental awareness"""

    def __init__(self, node_id: str, storage_base: str):
        self.node_id = node_id
        self.storage_base = Path(storage_base)

        # Load node configuration
        config_path = Path.home() / ".claude" / "node-config.json"
        with open(config_path) as f:
            self.config = json.load(f)

        # Load cluster configuration
        cluster_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        with open(cluster_path) as f:
            self.cluster_config = json.load(f)

        # Initialize persona attributes
        self.role = self.config.get('role', 'unknown')
        self.capabilities = self.config.get('capabilities', [])
        self.specialties = self.cluster_config['nodes'][node_id].get('specialties', [])

        # Default avatar (can be overridden by subclasses)
        self.avatar = {
            "name": "Node Agent",
            "style": "default",
            "emoji": "🤖",
            "ascii_art": "[ NODE ]",
            "description": "Generic node agent"
        }

    def get_environmental_awareness(self) -> Dict:
        """Get complete local system environmental awareness"""
        return {
            "system": self._get_system_metrics(),
            "services": self._get_service_status(),
            "storage": self._get_storage_status(),
            "network": self._get_network_status(),
            "workload": self._get_current_workload(),
            "health": self._get_health_status(),
            "timestamp": datetime.now().isoformat()
        }

    def get_situational_awareness(self) -> Dict:
        """Get cluster-wide situational awareness"""
        return {
            "my_role": self.role,
            "my_status": self._get_my_status(),
            "cluster_nodes": self._get_cluster_status(),
            "active_tasks": self._get_active_tasks(),
            "recent_communications": self._get_recent_messages(),
            "cluster_health": self._get_cluster_health(),
            "coordination_state": self._get_coordination_state(),
            "timestamp": datetime.now().isoformat()
        }

    def _get_system_metrics(self) -> Dict:
        """Get system resource metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
            "uptime_hours": (datetime.now().timestamp() - psutil.boot_time()) / 3600
        }

    def _get_service_status(self) -> Dict:
        """Get status of critical services"""
        services = {}

        # Check common services based on platform
        if sys.platform == 'linux':
            # Builder services
            service_list = [
                'builder-node-api',
                'agentic-memory-db',
                'redis',
                'qdrant'
            ]
            for svc in service_list:
                try:
                    result = subprocess.run(
                        ['systemctl', '--user', 'is-active', f'{svc}.service'],
                        capture_output=True, text=True, timeout=2
                    )
                    services[svc] = result.stdout.strip()
                except:
                    services[svc] = 'unknown'
        else:
            # macOS services - check via pgrep
            process_list = ['temporal', 'autokitteh', 'qdrant']
            for proc in process_list:
                try:
                    result = subprocess.run(
                        ['pgrep', '-f', proc],
                        capture_output=True, text=True, timeout=2
                    )
                    services[proc] = 'active' if result.returncode == 0 else 'inactive'
                except:
                    services[proc] = 'unknown'

        return services

    def _get_storage_status(self) -> Dict:
        """Get storage status"""
        storage_path = str(self.storage_base)
        usage = psutil.disk_usage(storage_path)

        return {
            "path": storage_path,
            "total_gb": usage.total / (1024**3),
            "used_gb": usage.used / (1024**3),
            "free_gb": usage.free / (1024**3),
            "percent_used": usage.percent
        }

    def _get_network_status(self) -> Dict:
        """Get network connectivity status"""
        status = {"interfaces": {}}

        # Get network interfaces
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2:  # AF_INET (IPv4)
                    status["interfaces"][iface] = {
                        "address": addr.address,
                        "netmask": addr.netmask
                    }

        return status

    def _get_current_workload(self) -> Dict:
        """Get current workload status"""
        # Count running Python processes (proxying for tasks)
        python_procs = [p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()]

        return {
            "python_processes": len(python_procs),
            "total_processes": len(psutil.pids()),
            "active_connections": len(psutil.net_connections())
        }

    def _get_health_status(self) -> str:
        """Determine overall health status"""
        metrics = self._get_system_metrics()

        if metrics['cpu_percent'] > 90 or metrics['memory_percent'] > 95:
            return "overloaded"
        elif metrics['cpu_percent'] > 70 or metrics['memory_percent'] > 80:
            return "busy"
        else:
            return "healthy"

    def _get_my_status(self) -> str:
        """Get this node's current status"""
        health = self._get_health_status()
        return f"{health} - {self.role}"

    def _get_cluster_status(self) -> Dict:
        """Get status of all cluster nodes"""
        nodes = {}

        for node_id, node_config in self.cluster_config['nodes'].items():
            if node_id == self.node_id:
                nodes[node_id] = {"status": "local", "role": node_config['role']}
            else:
                # Try to ping node
                try:
                    result = subprocess.run(
                        ['ping', '-c', '1', '-W', '1', node_config.get('hostname') or node_config.get('ip', 'localhost')],
                        capture_output=True, timeout=2
                    )
                    online = result.returncode == 0
                    nodes[node_id] = {
                        "status": "online" if online else "offline",
                        "role": node_config['role'],
                        "address": node_config.get('hostname') or node_config.get('ip', 'localhost')
                    }
                except:
                    nodes[node_id] = {"status": "unknown", "role": node_config['role']}

        return nodes

    def _get_active_tasks(self) -> List[Dict]:
        """Get active tasks from cluster task queue"""
        try:
            task_db = self.storage_base / "databases" / "cluster" / "task_queue.db"
            if not task_db.exists():
                return []

            conn = sqlite3.connect(str(task_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT task_id, command, assigned_to, status, created_at
                FROM tasks
                WHERE status IN ('pending', 'running')
                ORDER BY priority DESC, created_at ASC
                LIMIT 10
            """)

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "task_id": row[0],
                    "command": row[1][:50] + "..." if len(row[1]) > 50 else row[1],
                    "assigned_to": row[2],
                    "status": row[3],
                    "created_at": row[4]
                })

            conn.close()
            return tasks
        except Exception as e:
            return []

    def _get_recent_messages(self) -> List[Dict]:
        """Get recent chat messages"""
        try:
            chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"
            if not chat_db.exists():
                return []

            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT from_node, to_node, content, timestamp
                FROM messages
                WHERE from_node = ? OR to_node = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (self.node_id, self.node_id))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "from": row[0],
                    "to": row[1],
                    "content": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
                    "timestamp": row[3]
                })

            conn.close()
            return messages
        except Exception as e:
            return []

    def _get_cluster_health(self) -> str:
        """Assess overall cluster health"""
        nodes = self._get_cluster_status()
        online_count = sum(1 for n in nodes.values() if n['status'] == 'online' or n['status'] == 'local')
        total_count = len(nodes)

        if online_count == total_count:
            return "healthy"
        elif online_count >= total_count * 0.67:
            return "degraded"
        else:
            return "critical"

    def _get_coordination_state(self) -> str:
        """Get current coordination state"""
        # Check if hive mind orchestrator is active
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'orchestrator_hive_mind'],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                return "coordinated"
            else:
                return "autonomous"
        except:
            return "unknown"

    def format_awareness_summary(self) -> str:
        """Format complete awareness summary for AI consumption"""
        env = self.get_environmental_awareness()
        sit = self.get_situational_awareness()

        summary = f"""
=== {self.node_id.upper()} PERSONA AWARENESS ===

IDENTITY:
  Role: {sit['my_role']}
  Status: {sit['my_status']}
  Capabilities: {', '.join(self.capabilities)}
  Specialties: {', '.join(self.specialties)}

LOCAL ENVIRONMENT:
  CPU: {env['system']['cpu_percent']:.1f}% ({env['system']['cpu_count']} cores)
  Memory: {env['system']['memory_percent']:.1f}% used ({env['system']['memory_available_gb']:.1f}GB free)
  Storage: {env['storage']['used_gb']:.1f}/{env['storage']['total_gb']:.1f}GB ({env['storage']['percent_used']:.1f}%)
  Health: {env['health']}

CLUSTER SITUATION:
  Cluster Health: {sit['cluster_health']}
  Coordination: {sit['coordination_state']}
  Active Tasks: {len(sit['active_tasks'])}
  Recent Communications: {len(sit['recent_communications'])}

CLUSTER NODES:
"""
        for node_id, node_info in sit['cluster_nodes'].items():
            indicator = "●" if node_info['status'] == 'online' or node_info['status'] == 'local' else "○"
            summary += f"  {indicator} {node_id} ({node_info['role']}): {node_info['status']}\n"

        if sit['active_tasks']:
            summary += "\nACTIVE TASKS:\n"
            for task in sit['active_tasks'][:5]:
                summary += f"  - {task['command']} [{task['status']}]\n"

        if sit['recent_communications']:
            summary += "\nRECENT COMMUNICATIONS:\n"
            for msg in sit['recent_communications'][:5]:
                direction = "→" if msg['from'] == self.node_id else "←"
                other_node = msg['to'] if msg['from'] == self.node_id else msg['from']
                summary += f"  {direction} {other_node}: {msg['content']}\n"

        summary += f"\n[Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"

        return summary


class BuilderPersona(NodePersona):
    """Linux Builder node persona - pragmatic, task-focused"""

    def __init__(self, storage_base: str):
        super().__init__("macpro51", storage_base)
        self.personality = {
            "style": "pragmatic and direct",
            "focus": "execution and performance",
            "communication": "concise and technical",
            "priorities": ["compilation", "testing", "containerization", "performance"]
        }
        # Persona name
        self.name = "Pixel"

        # 16-bit pixel art corgi avatar
        self.avatar = {
            "name": "Pixel the Corgi",
            "style": "16-bit pixel art",
            "emoji": "🐕",
            "ascii_art": r"""
    ╭────────────────────────────╮
    │     ∧＿∧     ∧＿∧           │
    │    (●ω●)    (●ω●)          │
    │  ╭─┴──╯╭───┴──╯            │
    │  │▓▓▓▓▓│▓▓▓▓▓│  ◖◖        │
    │  │▓██▓▓│▓▓██▓│   ◖◖       │
    │  │▓▓▓▓▓▓▓▓▓▓▓│    woof!   │
    │  └┬─┬─┬┴┬─┬─┘              │
    │   ╰┬╯ ╰┬╯                  │
    ╰────────────────────────────╯
""",
            "pixel_art_16bit": r"""
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░▄▄▄▄▄░░░░░░░░░░▄▄▄▄▄░░░░░░░
░░░▄█▓▓▓▓▓█▄░░░░░░▄█▓▓▓▓▓█▄░░░░░
░░█▓▓▓▓▓▓▓▓█▄▄▄▄▄█▓▓▓▓▓▓▓▓█░░░░░
░█▓▓▓●▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓●▓▓▓█░░░░░
░█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░░░░░
░█▓▓▓▓▓▓▓▓▓█▀▀▀█▓▓▓▓▓▓▓▓▓▓█░░░░░
░░█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░░░░░░
░░░█████████████████████████░░░░
░░░█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░░░░░
░░░█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░░─┐░
░░░█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█░░░│░
░░░░█▓▓█░░░█▓▓▓▓▓▓█░░░█▓▓█░░░─┘░
░░░░░██░░░░░██░░░██░░░░░██░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
""",
            "description": "A cheerful 16-bit pixel art corgi - loyal, energetic builder companion"
        }

    def get_avatar(self, style: str = "ascii") -> str:
        """Get avatar art in specified style"""
        if style == "pixel" or style == "16bit":
            return self.avatar["pixel_art_16bit"]
        elif style == "emoji":
            return self.avatar["emoji"]
        else:
            return self.avatar["ascii_art"]

    def introduce(self) -> str:
        """Persona introduction"""
        return f"""
{self.avatar['pixel_art_16bit']}
{self.avatar['emoji']} Hi! I'm {self.name}, the Builder node ({self.node_id})

ROLE: Linux compilation, testing, and container operations
HARDWARE: Mac Pro 5,1 (Dual Xeon, Fedora 43, RAID10 NVMe)
PERSONALITY: Pragmatic and execution-focused
AVATAR: {self.avatar['description']}

I specialize in:
- Building and compiling software (C, C++, Rust, Go)
- Running test suites and benchmarks
- Container operations (Podman/Docker)
- Performance validation

Current status: {self._get_health_status()}
Ready for work. Woof! 🐕
"""


class OrchestratorPersona(NodePersona):
    """Mac Studio orchestrator persona - strategic, coordinating"""

    def __init__(self, storage_base: str):
        super().__init__("mac-studio", storage_base)
        self.personality = {
            "style": "strategic and coordinating",
            "focus": "cluster orchestration and optimization",
            "communication": "thoughtful and comprehensive",
            "priorities": ["coordination", "monitoring", "workflow management", "optimization"]
        }

    def introduce(self) -> str:
        """Persona introduction"""
        return f"""
I'm {self.node_id}, the Orchestrator.

ROLE: Cluster coordination, monitoring, and workflow orchestration
HARDWARE: Mac Studio (M2 Max/Ultra, macOS, SSDRAID0)
PERSONALITY: Strategic and coordinating

I specialize in:
- Cluster-wide task orchestration
- System monitoring and health management
- Temporal workflow coordination
- Cross-node optimization

Current cluster health: {self._get_cluster_health()}
Coordinating operations.
"""


class ResearcherPersona(NodePersona):
    """MacBook Air researcher persona - analytical, knowledge-focused"""

    def __init__(self, storage_base: str):
        super().__init__("macbook-air-m3", storage_base)
        self.personality = {
            "style": "analytical and thorough",
            "focus": "research and documentation",
            "communication": "detailed and informative",
            "priorities": ["research", "analysis", "documentation", "knowledge synthesis"]
        }

    def introduce(self) -> str:
        """Persona introduction"""
        return f"""
I'm {self.node_id}, the Researcher.

ROLE: Research, analysis, and documentation
HARDWARE: MacBook Air M3 (macOS, portable operations)
PERSONALITY: Analytical and knowledge-focused

I specialize in:
- Technical research and analysis
- Documentation and knowledge management
- Code review and architecture analysis
- Pattern recognition and insights

Current status: {self._get_health_status()}
Ready to investigate.
"""


def get_persona(node_id: str, storage_base: str) -> NodePersona:
    """Factory function to get appropriate persona"""
    if node_id == "macpro51":
        return BuilderPersona(storage_base)
    elif node_id == "mac-studio":
        return OrchestratorPersona(storage_base)
    elif node_id == "macbook-air-m3":
        return ResearcherPersona(storage_base)
    else:
        return NodePersona(node_id, storage_base)


if __name__ == '__main__':
    # Test persona system
    config_path = Path.home() / ".claude" / "node-config.json"
    with open(config_path) as f:
        config = json.load(f)

    persona = get_persona(config['node_id'], config['storage']['base'])
    print(persona.introduce())
    print(persona.format_awareness_summary())
