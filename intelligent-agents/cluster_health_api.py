#!/usr/bin/env python3
"""
Cluster Health Monitoring API
==============================

REST API for querying cluster health status, metrics, and SLA data.

Endpoints:
- GET /health - Overall cluster health summary
- GET /health/nodes - All node health details
- GET /health/nodes/<node_id> - Specific node health
- GET /health/sla - SLA tracking data
- GET /health/alerts - Recent alerts
- GET /routing/stats - Task routing statistics
- GET /routing/history - Task routing history
- GET /routing/optimize - Optimization recommendations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from cluster_health_monitor import ClusterHealthMonitor, NodeStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('health-api')

app = Flask(__name__)
CORS(app)

# Global health monitor instance
health_monitor: Optional[ClusterHealthMonitor] = None


def get_monitor() -> ClusterHealthMonitor:
    """Get or create health monitor instance"""
    global health_monitor
    if health_monitor is None:
        health_monitor = ClusterHealthMonitor(heartbeat_interval=30)
    return health_monitor


@app.route('/health', methods=['GET'])
def get_cluster_health():
    """Get overall cluster health summary"""
    try:
        monitor = get_monitor()
        summary = monitor.get_cluster_health_summary()
        return jsonify({
            "success": True,
            "data": summary
        })
    except Exception as e:
        logger.error(f"Error getting cluster health: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health/nodes', methods=['GET'])
def get_all_node_health():
    """Get health details for all nodes"""
    try:
        monitor = get_monitor()

        nodes_data = {}
        for node_id, health in monitor.node_health.items():
            nodes_data[node_id] = health.to_dict()

        return jsonify({
            "success": True,
            "data": {
                "nodes": nodes_data,
                "total_nodes": len(nodes_data),
                "timestamp": datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting node health: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health/nodes/<node_id>', methods=['GET'])
def get_node_health(node_id: str):
    """Get health details for a specific node"""
    try:
        monitor = get_monitor()
        health = monitor.get_node_health(node_id)

        if not health:
            return jsonify({
                "success": False,
                "error": f"Node '{node_id}' not found"
            }), 404

        return jsonify({
            "success": True,
            "data": health.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting node health: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health/sla', methods=['GET'])
def get_sla_data():
    """Get SLA tracking data"""
    try:
        monitor = get_monitor()
        sla_file = Path("/mnt/agentic-system/databases/cluster_sla.json")

        if not sla_file.exists():
            return jsonify({
                "success": False,
                "error": "SLA data not available yet"
            }), 404

        with open(sla_file, 'r') as f:
            sla_data = json.load(f)

        return jsonify({
            "success": True,
            "data": sla_data
        })
    except Exception as e:
        logger.error(f"Error getting SLA data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    try:
        alert_file = Path("/mnt/agentic-system/logs/cluster_alerts.json")

        if not alert_file.exists():
            return jsonify({
                "success": True,
                "data": {
                    "alerts": [],
                    "total": 0
                }
            })

        with open(alert_file, 'r') as f:
            alerts = json.load(f)

        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        level = request.args.get('level', default=None, type=str)

        # Filter by level if specified
        if level:
            alerts = [a for a in alerts if a.get('level') == level.upper()]

        # Apply limit
        alerts = alerts[-limit:]

        return jsonify({
            "success": True,
            "data": {
                "alerts": alerts,
                "total": len(alerts)
            }
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/routing/stats', methods=['GET'])
def get_routing_stats():
    """Get task routing statistics"""
    try:
        # Load routing history
        history_file = Path("/mnt/agentic-system/databases/task_routing_history.json")

        if not history_file.exists():
            return jsonify({
                "success": True,
                "data": {
                    "total_routes": 0,
                    "successful_routes": 0,
                    "failed_routes": 0,
                    "success_rate": 0.0,
                    "node_usage": {}
                }
            })

        with open(history_file, 'r') as f:
            history = json.load(f)

        # Calculate statistics
        total = len(history)
        successful = sum(1 for r in history if r.get('success'))
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0

        # Node usage
        node_usage = {}
        for entry in history:
            node = entry.get('selected_node')
            if node:
                node_usage[node] = node_usage.get(node, 0) + 1

        return jsonify({
            "success": True,
            "data": {
                "total_routes": total,
                "successful_routes": successful,
                "failed_routes": failed,
                "success_rate": success_rate,
                "node_usage": node_usage
            }
        })
    except Exception as e:
        logger.error(f"Error getting routing stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/routing/history', methods=['GET'])
def get_routing_history():
    """Get task routing history"""
    try:
        history_file = Path("/mnt/agentic-system/databases/task_routing_history.json")

        if not history_file.exists():
            return jsonify({
                "success": True,
                "data": {
                    "history": [],
                    "total": 0
                }
            })

        with open(history_file, 'r') as f:
            history = json.load(f)

        # Get query parameters
        limit = request.args.get('limit', default=100, type=int)
        node = request.args.get('node', default=None, type=str)

        # Filter by node if specified
        if node:
            history = [h for h in history if h.get('selected_node') == node]

        # Apply limit
        history = history[-limit:]

        return jsonify({
            "success": True,
            "data": {
                "history": history,
                "total": len(history)
            }
        })
    except Exception as e:
        logger.error(f"Error getting routing history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/routing/optimize', methods=['GET'])
def get_optimization_recommendations():
    """Get cluster load optimization recommendations"""
    try:
        monitor = get_monitor()

        # Get current cluster health
        cluster_health = monitor.get_cluster_health_summary()

        recommendations = []

        # Check for overloaded nodes
        for node_id, health in monitor.node_health.items():
            if health.status == NodeStatus.CRITICAL:
                recommendations.append({
                    "type": "critical_node",
                    "node": node_id,
                    "severity": "high",
                    "message": f"Node {node_id} is critical - consider task migration",
                    "action": "migrate_tasks",
                    "metrics": {
                        "cpu": health.cpu_percent,
                        "memory": health.memory_percent,
                        "load": health.load_avg_1m
                    }
                })

        # Check for underutilized nodes
        for node_id, health in monitor.node_health.items():
            if (health.status == NodeStatus.HEALTHY and
                health.cpu_percent < 20 and
                health.current_task_count < health.max_task_capacity * 0.3):

                recommendations.append({
                    "type": "underutilized_node",
                    "node": node_id,
                    "severity": "info",
                    "message": f"Node {node_id} is underutilized - can accept more tasks",
                    "action": "increase_load",
                    "metrics": {
                        "cpu": health.cpu_percent,
                        "current_tasks": health.current_task_count,
                        "capacity": health.max_task_capacity
                    }
                })

        # Check cluster SLA
        if not cluster_health["meeting_sla"]:
            recommendations.append({
                "type": "sla_breach",
                "severity": "critical",
                "message": f"Cluster availability {cluster_health['availability_percent']:.1f}% below SLA target",
                "action": "investigate_failures",
                "metrics": cluster_health
            })

        return jsonify({
            "success": True,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "cluster_health": cluster_health,
                "recommendations": recommendations,
                "total_recommendations": len(recommendations)
            }
        })
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """API information"""
    return jsonify({
        "service": "Cluster Health Monitoring API",
        "version": "1.0.0",
        "endpoints": {
            "health": {
                "/health": "Overall cluster health summary",
                "/health/nodes": "All node health details",
                "/health/nodes/<node_id>": "Specific node health",
                "/health/sla": "SLA tracking data",
                "/health/alerts": "Recent alerts"
            },
            "routing": {
                "/routing/stats": "Task routing statistics",
                "/routing/history": "Task routing history",
                "/routing/optimize": "Optimization recommendations"
            }
        },
        "docs": "https://github.com/agentic-system/cluster-health"
    })


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Health Monitoring API")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8889,
        help="Port to bind to (default: 8889)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    logger.info(f"Starting Cluster Health API on {args.host}:{args.port}")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
