#!/usr/bin/env python3
"""
Cluster Node Communication API
Provides REST API for inter-node communication in the agentic cluster

Features:
- Node discovery and registration
- Memory synchronization endpoints
- Inter-node messaging
- Status reporting
"""

from flask import Flask, jsonify, request
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import logging
import subprocess

app = Flask(__name__)

# Configuration
NODE_CONFIG_PATH = Path.home() / '.claude' / 'node-config.json'
# Store on SSDRAID0 (not /Users/marc - see FILE_LOCATION_POLICY.md)
CLUSTER_DB = Path('/Volumes/SSDRAID0/agentic-system/databases/cluster/node_registry.db')
LOCAL_DB = Path('/Volumes/SSDRAID0/agentic-system/databases/cluster/nodes/macbook-air-m3/local_memory.db')
SHARED_DB_SSDRAID = Path('/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path('/Volumes/SSDRAID0/agentic-system/logs/cluster-node-api.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('cluster-node-api')

# Load node configuration
def load_node_config():
    if NODE_CONFIG_PATH.exists():
        with open(NODE_CONFIG_PATH) as f:
            return json.load(f)
    return {}

NODE_CONFIG = load_node_config()
NODE_ID = NODE_CONFIG.get('node_id', 'unknown')

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "node_id": NODE_ID,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/node/info', methods=['GET'])
def get_node_info():
    """Get this node's information"""
    return jsonify({
        "success": True,
        "data": NODE_CONFIG
    })

@app.route('/api/v1/cluster/nodes', methods=['GET'])
def list_cluster_nodes():
    """List all nodes in the cluster"""
    try:
        conn = sqlite3.connect(CLUSTER_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT node_id, node_name, role, status, last_seen, capabilities
            FROM nodes
            WHERE status = 'active'
            ORDER BY last_seen DESC
        ''')

        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                "node_id": row['node_id'],
                "node_name": row['node_name'],
                "role": row['role'],
                "status": row['status'],
                "last_seen": row['last_seen'],
                "capabilities": json.loads(row['capabilities']) if row['capabilities'] else []
            })

        conn.close()

        return jsonify({
            "success": True,
            "data": nodes,
            "count": len(nodes)
        })

    except Exception as e:
        logger.error(f"Error listing cluster nodes: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/v1/memory/local/stats', methods=['GET'])
def get_local_memory_stats():
    """Get local memory database statistics"""
    try:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM entities')
        entity_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM observations')
        observation_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations')
        relation_count = cursor.fetchone()[0]

        cursor.execute('''
            SELECT tier, COUNT(*) as count
            FROM entities
            GROUP BY tier
        ''')
        tier_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "entities": entity_count,
                "observations": observation_count,
                "relations": relation_count,
                "tier_distribution": tier_distribution
            }
        })

    except Exception as e:
        logger.error(f"Error getting local memory stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/v1/memory/cluster/sync', methods=['POST'])
def trigger_cluster_sync():
    """Trigger cluster memory synchronization"""
    try:
        sync_type = request.json.get('type', 'sync')  # push, pull, or sync

        # Run cluster sync script
        result = subprocess.run(
            ['python3', '/Volumes/SSDRAID0/agentic-system/scripts/cluster-memory-sync.py', sync_type],
            capture_output=True,
            text=True,
            timeout=60
        )

        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })

    except Exception as e:
        logger.error(f"Error triggering cluster sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/v1/message/send', methods=['POST'])
def send_message():
    """Send a message to another node (placeholder for future implementation)"""
    try:
        target_node = request.json.get('target_node')
        message = request.json.get('message')
        message_type = request.json.get('type', 'general')

        # For now, just log the message
        # Future: Implement actual inter-node HTTP communication
        logger.info(f"Message from {NODE_ID} to {target_node}: {message}")

        return jsonify({
            "success": True,
            "message": "Message queued for delivery (implementation pending)"
        })

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/v1/services/status', methods=['GET'])
def get_services_status():
    """Get status of key services on this node"""
    try:
        services = {}

        # Check Qdrant
        try:
            import requests
            resp = requests.get('http://localhost:6333/healthz', timeout=2)
            services['qdrant'] = {
                "status": "healthy" if resp.status_code == 200 else "unhealthy",
                "port": 6333
            }
        except:
            services['qdrant'] = {"status": "stopped"}

        # Check Temporal
        try:
            result = subprocess.run(['pgrep', '-f', 'temporal server'],
                                    capture_output=True, timeout=2)
            services['temporal'] = {
                "status": "running" if result.returncode == 0 else "stopped"
            }
        except:
            services['temporal'] = {"status": "unknown"}

        # Check enhanced-memory-mcp
        try:
            result = subprocess.run(['pgrep', '-f', 'enhanced-memory-mcp'],
                                    capture_output=True, timeout=2)
            services['enhanced_memory_mcp'] = {
                "status": "running" if result.returncode == 0 else "stopped"
            }
        except:
            services['enhanced_memory_mcp'] = {"status": "unknown"}

        return jsonify({
            "success": True,
            "data": services
        })

    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info(f"🚀 Starting Cluster Node API for {NODE_ID}")
    logger.info(f"📂 Cluster DB: {CLUSTER_DB}")
    logger.info(f"📂 Local DB: {LOCAL_DB}")

    # Run on port 5100 for inter-node communication
    app.run(host='0.0.0.0', port=5100, debug=False)
