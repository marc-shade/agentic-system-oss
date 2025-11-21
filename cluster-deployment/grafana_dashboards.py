#!/usr/bin/env python3
"""
Grafana Dashboard Definitions for GitMQ Cluster
===============================================

Provides pre-configured Grafana dashboards for:
- Cluster overview and system health
- Task execution monitoring
- Approval workflow tracking
- Risk assessment visualization
- Code transfer performance
- Error tracking and debugging

These dashboards integrate with:
- Prometheus metrics (metrics.py)
- OpenTelemetry traces (telemetry.py)
- Structured logs (structured_logging.py)

Usage:
    # Generate all dashboards
    python3 grafana_dashboards.py --output ./dashboards/

    # Import to Grafana
    curl -X POST http://localhost:9500/api/dashboards/db \
        -H "Content-Type: application/json" \
        -d @cluster_overview.json

Dashboard Hierarchy:
    1. Cluster Overview (main entry point)
    2. Task Execution (drill-down from overview)
    3. Approval & Risk (drill-down from overview)
    4. Code Transfer (drill-down from overview)
    5. System Health (drill-down from overview)
"""

import json
from typing import Dict, List, Any
from pathlib import Path


class GrafanaDashboardGenerator:
    """
    Generates Grafana dashboard JSON definitions.

    Creates comprehensive monitoring dashboards with:
    - Time series graphs
    - Stat panels (single values)
    - Gauge panels (ranges)
    - Heatmaps (distributions)
    - Tables (detailed data)
    - Alert thresholds
    """

    def __init__(self, datasource: str = "Prometheus"):
        """
        Initialize dashboard generator.

        Args:
            datasource: Prometheus datasource name
        """
        self.datasource = datasource
        self.dashboard_version = 1

    def create_cluster_overview_dashboard(self) -> Dict[str, Any]:
        """
        Create main cluster overview dashboard.

        Shows high-level metrics:
        - Task submission and completion rates
        - Pending approvals
        - Active nodes
        - Error rates
        - System health
        """
        return {
            "dashboard": {
                "title": "GitMQ Cluster Overview",
                "tags": ["gitmq", "cluster", "overview"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": self.dashboard_version,
                "refresh": "10s",

                "panels": [
                    # Row 1: Key Metrics (Stats)
                    self._create_stat_panel(
                        title="Tasks Submitted (24h)",
                        query="increase(gitmq_tasks_submitted_total[24h])",
                        unit="short",
                        gridPos={"h": 4, "w": 4, "x": 0, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Tasks Completed (24h)",
                        query="increase(gitmq_tasks_completed_total[24h])",
                        unit="short",
                        gridPos={"h": 4, "w": 4, "x": 4, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Success Rate",
                        query="rate(gitmq_tasks_completed_total[1h]) / rate(gitmq_tasks_submitted_total[1h]) * 100",
                        unit="percent",
                        gridPos={"h": 4, "w": 4, "x": 8, "y": 0}
                    ),
                    self._create_gauge_panel(
                        title="Pending Approvals",
                        query="gitmq_approvals_pending",
                        min=0,
                        max=20,
                        thresholds=[
                            {"value": 0, "color": "green"},
                            {"value": 5, "color": "yellow"},
                            {"value": 10, "color": "red"}
                        ],
                        gridPos={"h": 4, "w": 4, "x": 12, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Active Nodes",
                        query="count(count by (node_id) (gitmq_tasks_submitted_total))",
                        unit="short",
                        gridPos={"h": 4, "w": 4, "x": 16, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Error Rate (1h)",
                        query="rate(gitmq_errors_total[1h]) * 3600",
                        unit="errors/h",
                        gridPos={"h": 4, "w": 4, "x": 20, "y": 0}
                    ),

                    # Row 2: Task Submission Rate (Graph)
                    self._create_graph_panel(
                        title="Task Submission Rate",
                        queries=[
                            {"expr": "rate(gitmq_tasks_submitted_total[5m])", "legendFormat": "{{node_id}} - {{task_type}}"}
                        ],
                        yAxisLabel="tasks/sec",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 4}
                    ),

                    # Row 2: Task Completion Rate (Graph)
                    self._create_graph_panel(
                        title="Task Completion Rate",
                        queries=[
                            {"expr": "rate(gitmq_tasks_completed_total[5m])", "legendFormat": "{{node_id}} - {{task_type}}"},
                            {"expr": "rate(gitmq_tasks_failed_total[5m])", "legendFormat": "{{node_id}} - {{task_type}} (failed)"}
                        ],
                        yAxisLabel="tasks/sec",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 4}
                    ),

                    # Row 3: Task Execution Duration (Heatmap)
                    self._create_heatmap_panel(
                        title="Task Execution Duration Distribution",
                        query="rate(gitmq_task_execution_duration_seconds_bucket[5m])",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 12}
                    ),

                    # Row 3: Risk Score Distribution (Heatmap)
                    self._create_heatmap_panel(
                        title="Risk Score Distribution",
                        query="rate(gitmq_risk_score_bucket[5m])",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 12}
                    ),

                    # Row 4: Error Breakdown (Table)
                    self._create_table_panel(
                        title="Recent Errors",
                        query="topk(10, gitmq_errors_total)",
                        gridPos={"h": 6, "w": 24, "x": 0, "y": 20}
                    )
                ]
            }
        }

    def create_task_execution_dashboard(self) -> Dict[str, Any]:
        """
        Create detailed task execution dashboard.

        Shows:
        - Task queues (pending, running, completed)
        - Execution duration percentiles
        - Task type breakdown
        - Execution status
        - Performance trends
        """
        return {
            "dashboard": {
                "title": "GitMQ Task Execution",
                "tags": ["gitmq", "tasks", "execution"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": self.dashboard_version,
                "refresh": "5s",

                "panels": [
                    # Row 1: Queue Stats
                    self._create_stat_panel(
                        title="Pending Tasks",
                        query="gitmq_tasks_pending",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 0, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Running Tasks",
                        query="gitmq_tasks_running",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 6, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Completed (1h)",
                        query="increase(gitmq_tasks_completed_total[1h])",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 12, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Failed (1h)",
                        query="increase(gitmq_tasks_failed_total[1h])",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 18, "y": 0}
                    ),

                    # Row 2: Duration Percentiles
                    self._create_graph_panel(
                        title="Task Execution Duration (Percentiles)",
                        queries=[
                            {"expr": "histogram_quantile(0.50, rate(gitmq_task_execution_duration_seconds_bucket[5m]))", "legendFormat": "p50"},
                            {"expr": "histogram_quantile(0.90, rate(gitmq_task_execution_duration_seconds_bucket[5m]))", "legendFormat": "p90"},
                            {"expr": "histogram_quantile(0.95, rate(gitmq_task_execution_duration_seconds_bucket[5m]))", "legendFormat": "p95"},
                            {"expr": "histogram_quantile(0.99, rate(gitmq_task_execution_duration_seconds_bucket[5m]))", "legendFormat": "p99"}
                        ],
                        yAxisLabel="seconds",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 4}
                    ),

                    # Row 2: Task Type Breakdown
                    self._create_graph_panel(
                        title="Task Submission by Type",
                        queries=[
                            {"expr": "rate(gitmq_tasks_submitted_total[5m])", "legendFormat": "{{task_type}}"}
                        ],
                        yAxisLabel="tasks/sec",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 4}
                    ),

                    # Row 3: Execution Status Over Time
                    self._create_graph_panel(
                        title="Task Status Timeline",
                        queries=[
                            {"expr": "gitmq_tasks_pending", "legendFormat": "Pending"},
                            {"expr": "gitmq_tasks_running", "legendFormat": "Running"},
                            {"expr": "rate(gitmq_tasks_completed_total[1m])", "legendFormat": "Completed/sec"},
                            {"expr": "rate(gitmq_tasks_failed_total[1m])", "legendFormat": "Failed/sec"}
                        ],
                        yAxisLabel="count",
                        gridPos={"h": 8, "w": 24, "x": 0, "y": 12}
                    ),

                    # Row 4: Task Details Table
                    self._create_table_panel(
                        title="Task Metrics by Type",
                        query="gitmq_tasks_submitted_total",
                        gridPos={"h": 8, "w": 24, "x": 0, "y": 20}
                    )
                ]
            }
        }

    def create_approval_risk_dashboard(self) -> Dict[str, Any]:
        """
        Create approval workflow and risk assessment dashboard.

        Shows:
        - Approval request rate
        - Approval decision times
        - Approval outcomes (approved, rejected, timeout)
        - Risk level distribution
        - Risk factor contributions
        """
        return {
            "dashboard": {
                "title": "GitMQ Approval & Risk Assessment",
                "tags": ["gitmq", "approval", "risk"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": self.dashboard_version,
                "refresh": "10s",

                "panels": [
                    # Row 1: Approval Stats
                    self._create_stat_panel(
                        title="Pending Approvals",
                        query="gitmq_approvals_pending",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 0, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Approved (24h)",
                        query='increase(gitmq_approval_decisions_total{decision="approved"}[24h])',
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 6, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Rejected (24h)",
                        query='increase(gitmq_approval_decisions_total{decision="rejected"}[24h])',
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 12, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Auto-Approved (24h)",
                        query='increase(gitmq_approval_decisions_total{decision="auto_approved"}[24h])',
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 18, "y": 0}
                    ),

                    # Row 2: Approval Decision Time
                    self._create_graph_panel(
                        title="Approval Decision Time (Percentiles)",
                        queries=[
                            {"expr": "histogram_quantile(0.50, rate(gitmq_approval_decision_time_seconds_bucket[5m]))", "legendFormat": "p50"},
                            {"expr": "histogram_quantile(0.90, rate(gitmq_approval_decision_time_seconds_bucket[5m]))", "legendFormat": "p90"},
                            {"expr": "histogram_quantile(0.95, rate(gitmq_approval_decision_time_seconds_bucket[5m]))", "legendFormat": "p95"}
                        ],
                        yAxisLabel="seconds",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 4}
                    ),

                    # Row 2: Approval Outcomes
                    self._create_graph_panel(
                        title="Approval Decisions",
                        queries=[
                            {"expr": 'rate(gitmq_approval_decisions_total{decision="approved"}[5m])', "legendFormat": "Approved"},
                            {"expr": 'rate(gitmq_approval_decisions_total{decision="rejected"}[5m])', "legendFormat": "Rejected"},
                            {"expr": 'rate(gitmq_approval_decisions_total{decision="auto_approved"}[5m])', "legendFormat": "Auto-Approved"},
                            {"expr": 'rate(gitmq_approval_decisions_total{decision="timeout"}[5m])', "legendFormat": "Timeout"}
                        ],
                        yAxisLabel="decisions/sec",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 4}
                    ),

                    # Row 3: Risk Score Distribution
                    self._create_heatmap_panel(
                        title="Risk Score Distribution",
                        query="rate(gitmq_risk_score_bucket[5m])",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 12}
                    ),

                    # Row 3: Risk Levels Breakdown
                    self._create_graph_panel(
                        title="Tasks by Risk Level",
                        queries=[
                            {"expr": 'gitmq_tasks_by_risk_level{risk_level="low"}', "legendFormat": "Low"},
                            {"expr": 'gitmq_tasks_by_risk_level{risk_level="medium"}', "legendFormat": "Medium"},
                            {"expr": 'gitmq_tasks_by_risk_level{risk_level="high"}', "legendFormat": "High"},
                            {"expr": 'gitmq_tasks_by_risk_level{risk_level="critical"}', "legendFormat": "Critical"}
                        ],
                        yAxisLabel="count",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 12}
                    ),

                    # Row 4: Approval Channels
                    self._create_table_panel(
                        title="Approvals by Channel",
                        query="gitmq_approval_decisions_total",
                        gridPos={"h": 6, "w": 24, "x": 0, "y": 20}
                    )
                ]
            }
        }

    def create_code_transfer_dashboard(self) -> Dict[str, Any]:
        """
        Create code transfer performance dashboard.

        Shows:
        - Transfer size distribution
        - Transfer duration
        - Transfer methods (inline, git_bundle, git_patch)
        - Bandwidth usage
        - Compression ratio
        """
        return {
            "dashboard": {
                "title": "GitMQ Code Transfer Performance",
                "tags": ["gitmq", "code-transfer", "performance"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": self.dashboard_version,
                "refresh": "10s",

                "panels": [
                    # Row 1: Transfer Stats
                    self._create_stat_panel(
                        title="Transfers (24h)",
                        query="increase(gitmq_code_transfers_total[24h])",
                        unit="short",
                        gridPos={"h": 4, "w": 6, "x": 0, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Avg Transfer Size",
                        query="avg(gitmq_code_transfer_size_bytes)",
                        unit="bytes",
                        gridPos={"h": 4, "w": 6, "x": 6, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Avg Duration",
                        query="avg(gitmq_code_transfer_duration_seconds)",
                        unit="s",
                        gridPos={"h": 4, "w": 6, "x": 12, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Avg Compression Ratio",
                        query="avg(gitmq_code_compression_ratio)",
                        unit="percent",
                        gridPos={"h": 4, "w": 6, "x": 18, "y": 0}
                    ),

                    # Row 2: Transfer Size Distribution
                    self._create_heatmap_panel(
                        title="Transfer Size Distribution",
                        query="rate(gitmq_code_transfer_size_bytes_bucket[5m])",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 4}
                    ),

                    # Row 2: Transfer Duration Distribution
                    self._create_heatmap_panel(
                        title="Transfer Duration Distribution",
                        query="rate(gitmq_code_transfer_duration_seconds_bucket[5m])",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 4}
                    ),

                    # Row 3: Transfer Methods
                    self._create_graph_panel(
                        title="Transfers by Method",
                        queries=[
                            {"expr": 'rate(gitmq_code_transfers_total{method="inline"}[5m])', "legendFormat": "Inline"},
                            {"expr": 'rate(gitmq_code_transfers_total{method="git_bundle"}[5m])', "legendFormat": "Git Bundle"},
                            {"expr": 'rate(gitmq_code_transfers_total{method="git_patch"}[5m])', "legendFormat": "Git Patch"}
                        ],
                        yAxisLabel="transfers/sec",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 12}
                    ),

                    # Row 3: Bandwidth Usage
                    self._create_graph_panel(
                        title="Bandwidth Usage",
                        queries=[
                            {"expr": "rate(gitmq_code_transfer_size_bytes[5m])", "legendFormat": "{{method}}"}
                        ],
                        yAxisLabel="bytes/sec",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 12}
                    ),

                    # Row 4: Transfer Details
                    self._create_table_panel(
                        title="Transfer Statistics",
                        query="gitmq_code_transfers_total",
                        gridPos={"h": 6, "w": 24, "x": 0, "y": 20}
                    )
                ]
            }
        }

    def create_system_health_dashboard(self) -> Dict[str, Any]:
        """
        Create system health and resource monitoring dashboard.

        Shows:
        - Memory usage
        - CPU usage
        - Disk usage
        - Network I/O
        - Error rates
        - Uptime
        """
        return {
            "dashboard": {
                "title": "GitMQ System Health",
                "tags": ["gitmq", "system", "health"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": self.dashboard_version,
                "refresh": "5s",

                "panels": [
                    # Row 1: System Stats
                    self._create_gauge_panel(
                        title="Memory Usage",
                        query="gitmq_system_memory_usage_percent",
                        min=0,
                        max=100,
                        thresholds=[
                            {"value": 0, "color": "green"},
                            {"value": 70, "color": "yellow"},
                            {"value": 90, "color": "red"}
                        ],
                        gridPos={"h": 6, "w": 6, "x": 0, "y": 0}
                    ),
                    self._create_gauge_panel(
                        title="CPU Usage",
                        query="gitmq_system_cpu_usage_percent",
                        min=0,
                        max=100,
                        thresholds=[
                            {"value": 0, "color": "green"},
                            {"value": 70, "color": "yellow"},
                            {"value": 90, "color": "red"}
                        ],
                        gridPos={"h": 6, "w": 6, "x": 6, "y": 0}
                    ),
                    self._create_gauge_panel(
                        title="Disk Usage",
                        query="gitmq_system_disk_usage_percent",
                        min=0,
                        max=100,
                        thresholds=[
                            {"value": 0, "color": "green"},
                            {"value": 80, "color": "yellow"},
                            {"value": 95, "color": "red"}
                        ],
                        gridPos={"h": 6, "w": 6, "x": 12, "y": 0}
                    ),
                    self._create_stat_panel(
                        title="Uptime",
                        query="gitmq_system_uptime_seconds",
                        unit="s",
                        gridPos={"h": 6, "w": 6, "x": 18, "y": 0}
                    ),

                    # Row 2: Error Rates
                    self._create_graph_panel(
                        title="Error Rate by Type",
                        queries=[
                            {"expr": "rate(gitmq_errors_total[5m])", "legendFormat": "{{error_type}}"}
                        ],
                        yAxisLabel="errors/sec",
                        gridPos={"h": 8, "w": 12, "x": 0, "y": 6}
                    ),

                    # Row 2: Resource Usage Trend
                    self._create_graph_panel(
                        title="Resource Usage Trend",
                        queries=[
                            {"expr": "gitmq_system_memory_usage_percent", "legendFormat": "Memory %"},
                            {"expr": "gitmq_system_cpu_usage_percent", "legendFormat": "CPU %"},
                            {"expr": "gitmq_system_disk_usage_percent", "legendFormat": "Disk %"}
                        ],
                        yAxisLabel="percent",
                        gridPos={"h": 8, "w": 12, "x": 12, "y": 6}
                    ),

                    # Row 3: Network I/O
                    self._create_graph_panel(
                        title="Network I/O",
                        queries=[
                            {"expr": "rate(gitmq_system_network_bytes_sent[5m])", "legendFormat": "Sent"},
                            {"expr": "rate(gitmq_system_network_bytes_received[5m])", "legendFormat": "Received"}
                        ],
                        yAxisLabel="bytes/sec",
                        gridPos={"h": 8, "w": 24, "x": 0, "y": 14}
                    ),

                    # Row 4: Error Details
                    self._create_table_panel(
                        title="Error Breakdown",
                        query="gitmq_errors_total",
                        gridPos={"h": 6, "w": 24, "x": 0, "y": 22}
                    )
                ]
            }
        }

    # ========================================================================
    # Panel Creation Helpers
    # ========================================================================

    def _create_stat_panel(
        self,
        title: str,
        query: str,
        unit: str = "short",
        gridPos: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Create stat panel (single value)."""
        return {
            "type": "stat",
            "title": title,
            "gridPos": gridPos or {"h": 4, "w": 6, "x": 0, "y": 0},
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": self.datasource
            }],
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"]
                },
                "orientation": "auto",
                "textMode": "auto",
                "colorMode": "value",
                "graphMode": "area"
            },
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "green"}
                        ]
                    }
                }
            }
        }

    def _create_gauge_panel(
        self,
        title: str,
        query: str,
        min: float,
        max: float,
        thresholds: List[Dict],
        gridPos: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Create gauge panel (range visualization)."""
        return {
            "type": "gauge",
            "title": title,
            "gridPos": gridPos or {"h": 6, "w": 6, "x": 0, "y": 0},
            "targets": [{
                "expr": query,
                "refId": "A",
                "datasource": self.datasource
            }],
            "options": {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"]
                },
                "showThresholdLabels": True,
                "showThresholdMarkers": True
            },
            "fieldConfig": {
                "defaults": {
                    "min": min,
                    "max": max,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": thresholds
                    }
                }
            }
        }

    def _create_graph_panel(
        self,
        title: str,
        queries: List[Dict[str, str]],
        yAxisLabel: str = "",
        gridPos: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Create time series graph panel."""
        targets = []
        for i, q in enumerate(queries):
            targets.append({
                "expr": q["expr"],
                "legendFormat": q["legendFormat"],
                "refId": chr(65 + i),  # A, B, C, ...
                "datasource": self.datasource
            })

        return {
            "type": "graph",
            "title": title,
            "gridPos": gridPos or {"h": 8, "w": 12, "x": 0, "y": 0},
            "targets": targets,
            "yaxes": [
                {
                    "label": yAxisLabel,
                    "show": True
                },
                {
                    "show": True
                }
            ],
            "xaxis": {
                "show": True,
                "mode": "time"
            },
            "legend": {
                "show": True,
                "alignAsTable": True,
                "avg": True,
                "max": True,
                "min": True,
                "current": True,
                "values": True
            },
            "lines": True,
            "fill": 1,
            "linewidth": 1,
            "nullPointMode": "null",
            "tooltip": {
                "shared": True,
                "sort": 0,
                "value_type": "individual"
            }
        }

    def _create_heatmap_panel(
        self,
        title: str,
        query: str,
        gridPos: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Create heatmap panel (distribution visualization)."""
        return {
            "type": "heatmap",
            "title": title,
            "gridPos": gridPos or {"h": 8, "w": 12, "x": 0, "y": 0},
            "targets": [{
                "expr": query,
                "format": "heatmap",
                "refId": "A",
                "datasource": self.datasource
            }],
            "dataFormat": "tsbuckets",
            "yAxis": {
                "format": "short",
                "logBase": 1
            },
            "cards": {
                "cardPadding": 2
            },
            "color": {
                "mode": "spectrum",
                "cardColor": "#b4ff00",
                "colorScale": "sqrt",
                "exponent": 0.5,
                "colorScheme": "interpolateOranges"
            }
        }

    def _create_table_panel(
        self,
        title: str,
        query: str,
        gridPos: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Create table panel (detailed data)."""
        return {
            "type": "table",
            "title": title,
            "gridPos": gridPos or {"h": 6, "w": 24, "x": 0, "y": 0},
            "targets": [{
                "expr": query,
                "format": "table",
                "instant": True,
                "refId": "A",
                "datasource": self.datasource
            }],
            "options": {
                "showHeader": True,
                "sortBy": []
            },
            "transformations": [
                {
                    "id": "organize",
                    "options": {
                        "excludeByName": {},
                        "indexByName": {},
                        "renameByName": {}
                    }
                }
            ]
        }

    # ========================================================================
    # Export Functions
    # ========================================================================

    def export_all_dashboards(self, output_dir: str = "./dashboards"):
        """
        Export all dashboards to JSON files.

        Args:
            output_dir: Output directory for dashboard files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        dashboards = {
            "cluster_overview.json": self.create_cluster_overview_dashboard(),
            "task_execution.json": self.create_task_execution_dashboard(),
            "approval_risk.json": self.create_approval_risk_dashboard(),
            "code_transfer.json": self.create_code_transfer_dashboard(),
            "system_health.json": self.create_system_health_dashboard()
        }

        for filename, dashboard in dashboards.items():
            filepath = output_path / filename
            with open(filepath, 'w') as f:
                json.dump(dashboard, f, indent=2)
            print(f"✓ Exported {filename}")

        print(f"\n✓ All dashboards exported to {output_dir}/")
        return dashboards


# ============================================================================
# Example Usage
# ============================================================================

def example_dashboard_generation():
    """Example: Generate and export Grafana dashboards."""
    print("\n" + "=" * 70)
    print("Grafana Dashboard Generation Example")
    print("=" * 70)

    # Create generator
    generator = GrafanaDashboardGenerator(datasource="Prometheus")

    print("\n1. Generating dashboards...")

    # Export all dashboards
    generator.export_all_dashboards(output_dir="./dashboards")

    print("\n2. Import to Grafana:")
    print("   curl -X POST http://localhost:9500/api/dashboards/db \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d @dashboards/cluster_overview.json")

    print("\n3. Dashboard URLs:")
    print("   - Cluster Overview: http://localhost:9500/d/cluster-overview")
    print("   - Task Execution: http://localhost:9500/d/task-execution")
    print("   - Approval & Risk: http://localhost:9500/d/approval-risk")
    print("   - Code Transfer: http://localhost:9500/d/code-transfer")
    print("   - System Health: http://localhost:9500/d/system-health")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Grafana dashboards")
    parser.add_argument("--output", default="./dashboards", help="Output directory")
    parser.add_argument("--datasource", default="Prometheus", help="Prometheus datasource name")
    args = parser.parse_args()

    generator = GrafanaDashboardGenerator(datasource=args.datasource)
    generator.export_all_dashboards(output_dir=args.output)

    print("\nGrafana dashboards module loaded successfully ✓")
