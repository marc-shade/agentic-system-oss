import os
import json
import asyncio
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

class MonitoringManager:
    """
    Manages system and application monitoring for the Software Planning MCP.
    Handles resource usage tracking, performance metrics, and health checks.
    """
    
    def __init__(self):
        self.metrics_dir = Path(os.path.expanduser("~/.mcp/metrics"))
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.system_metrics_file = self.metrics_dir / "system_metrics.json"
        self.app_metrics_file = self.metrics_dir / "app_metrics.json"
        self.alerts_file = self.metrics_dir / "alerts.json"
        
        # Initialize metrics files
        self._initialize_metrics_files()
        
        # Load metrics data
        self.system_metrics = self._load_system_metrics()
        self.app_metrics = self._load_app_metrics()
        self.alerts = self._load_alerts()
        
        # Default alert thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0
        }
    
    def _initialize_metrics_files(self):
        """Initialize metrics files with default values."""
        if not self.system_metrics_file.exists():
            with open(self.system_metrics_file, "w") as f:
                json.dump({"metrics": []}, f, indent=2)
        
        if not self.app_metrics_file.exists():
            with open(self.app_metrics_file, "w") as f:
                json.dump({"metrics": []}, f, indent=2)
        
        if not self.alerts_file.exists():
            with open(self.alerts_file, "w") as f:
                json.dump({"alerts": []}, f, indent=2)
    
    def _load_system_metrics(self) -> Dict[str, Any]:
        """Load system metrics data."""
        try:
            with open(self.system_metrics_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load system metrics: {e}")
            return {"metrics": []}
    
    def _load_app_metrics(self) -> Dict[str, Any]:
        """Load application metrics data."""
        try:
            with open(self.app_metrics_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load application metrics: {e}")
            return {"metrics": []}
    
    def _load_alerts(self) -> Dict[str, Any]:
        """Load alerts data."""
        try:
            with open(self.alerts_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load alerts: {e}")
            return {"alerts": []}
    
    def _save_system_metrics(self):
        """Save system metrics data."""
        try:
            with open(self.system_metrics_file, "w") as f:
                json.dump(self.system_metrics, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save system metrics: {e}")
    
    def _save_app_metrics(self):
        """Save application metrics data."""
        try:
            with open(self.app_metrics_file, "w") as f:
                json.dump(self.app_metrics, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save application metrics: {e}")
    
    def _save_alerts(self):
        """Save alerts data."""
        try:
            with open(self.alerts_file, "w") as f:
                json.dump(self.alerts, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save alerts: {e}")
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect system-wide metrics.
        
        Returns:
            Dictionary containing system metrics
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "used": psutil.disk_usage("/").used,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv
            },
            "system": {
                "platform": platform.system(),
                "release": platform.release(),
                "version": platform.version()
            }
        }
        
        # Add to metrics history
        self.system_metrics.setdefault("metrics", []).append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.system_metrics["metrics"]) > 1000:
            self.system_metrics["metrics"] = self.system_metrics["metrics"][-1000:]
        
        self._save_system_metrics()
        
        # Check for alerts
        await self._check_alerts(metrics)
        
        return metrics
    
    async def collect_app_metrics(
        self, 
        app_name: str,
        pid: int,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect application-specific metrics.
        
        Args:
            app_name: Name of the application
            pid: Process ID of the application
            custom_metrics: Optional custom metrics to include
            
        Returns:
            Dictionary containing application metrics
        """
        try:
            process = psutil.Process(pid)
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "app_name": app_name,
                "pid": pid,
                "cpu_percent": process.cpu_percent(interval=1),
                "memory_info": process.memory_info()._asdict(),
                "num_threads": process.num_threads(),
                "status": process.status(),
                "custom_metrics": custom_metrics or {}
            }
            
            # Add to metrics history
            self.app_metrics.setdefault("metrics", []).append(metrics)
            
            # Keep only last 1000 metrics per application
            app_metrics = [m for m in self.app_metrics["metrics"] if m["app_name"] == app_name]
            if len(app_metrics) > 1000:
                # Remove oldest metrics for this app
                self.app_metrics["metrics"] = [
                    m for m in self.app_metrics["metrics"]
                    if m["app_name"] != app_name
                ] + app_metrics[-1000:]
            
            self._save_app_metrics()
            
            return metrics
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to collect metrics for process {pid}: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "app_name": app_name,
                "pid": pid,
                "error": str(e)
            }
    
    async def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        # Check CPU usage
        if metrics["cpu"]["percent"] > self.thresholds["cpu_percent"]:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "cpu_usage",
                "severity": "high",
                "message": f"CPU usage is {metrics['cpu']['percent']}%, above threshold of {self.thresholds['cpu_percent']}%"
            })
        
        # Check memory usage
        if metrics["memory"]["percent"] > self.thresholds["memory_percent"]:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "memory_usage",
                "severity": "high",
                "message": f"Memory usage is {metrics['memory']['percent']}%, above threshold of {self.thresholds['memory_percent']}%"
            })
        
        # Check disk usage
        if metrics["disk"]["percent"] > self.thresholds["disk_percent"]:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "disk_usage",
                "severity": "high",
                "message": f"Disk usage is {metrics['disk']['percent']}%, above threshold of {self.thresholds['disk_percent']}%"
            })
        
        if alerts:
            # Add alerts to history
            self.alerts.setdefault("alerts", []).extend(alerts)
            
            # Keep only last 1000 alerts
            if len(self.alerts["alerts"]) > 1000:
                self.alerts["alerts"] = self.alerts["alerts"][-1000:]
            
            self._save_alerts()
    
    async def get_system_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get system metrics within a time range.
        
        Args:
            start_time: Optional start time in ISO format
            end_time: Optional end time in ISO format
            
        Returns:
            List of metrics within the time range
        """
        metrics = self.system_metrics.get("metrics", [])
        
        if start_time:
            metrics = [m for m in metrics if m["timestamp"] >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m["timestamp"] <= end_time]
        
        return metrics
    
    async def get_app_metrics(
        self,
        app_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get application metrics within a time range.
        
        Args:
            app_name: Name of the application
            start_time: Optional start time in ISO format
            end_time: Optional end time in ISO format
            
        Returns:
            List of metrics within the time range
        """
        metrics = [
            m for m in self.app_metrics.get("metrics", [])
            if m["app_name"] == app_name
        ]
        
        if start_time:
            metrics = [m for m in metrics if m["timestamp"] >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m["timestamp"] <= end_time]
        
        return metrics
    
    async def get_alerts(
        self,
        severity: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts within a time range.
        
        Args:
            severity: Optional severity filter
            start_time: Optional start time in ISO format
            end_time: Optional end time in ISO format
            
        Returns:
            List of alerts within the time range
        """
        alerts = self.alerts.get("alerts", [])
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        if start_time:
            alerts = [a for a in alerts if a["timestamp"] >= start_time]
        
        if end_time:
            alerts = [a for a in alerts if a["timestamp"] <= end_time]
        
        return alerts
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for monitoring management."""
        return [
            {
                "name": "collect_system_metrics",
                "description": "Collect system-wide metrics",
                "parameters": [],
                "handler": self.tool_collect_system_metrics,
            },
            {
                "name": "collect_app_metrics",
                "description": "Collect application-specific metrics",
                "parameters": [
                    {
                        "name": "app_name",
                        "description": "Name of the application",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "pid",
                        "description": "Process ID of the application",
                        "type": "integer",
                        "required": True,
                    },
                    {
                        "name": "custom_metrics",
                        "description": "Optional custom metrics to include",
                        "type": "object",
                        "required": False,
                    }
                ],
                "handler": self.tool_collect_app_metrics,
            },
            {
                "name": "get_system_metrics",
                "description": "Get system metrics within a time range",
                "parameters": [
                    {
                        "name": "start_time",
                        "description": "Optional start time in ISO format",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "end_time",
                        "description": "Optional end time in ISO format",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_get_system_metrics,
            },
            {
                "name": "get_app_metrics",
                "description": "Get application metrics within a time range",
                "parameters": [
                    {
                        "name": "app_name",
                        "description": "Name of the application",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "start_time",
                        "description": "Optional start time in ISO format",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "end_time",
                        "description": "Optional end time in ISO format",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_get_app_metrics,
            },
            {
                "name": "get_alerts",
                "description": "Get alerts within a time range",
                "parameters": [
                    {
                        "name": "severity",
                        "description": "Optional severity filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "start_time",
                        "description": "Optional start time in ISO format",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "end_time",
                        "description": "Optional end time in ISO format",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_get_alerts,
            },
        ]
    
    async def tool_collect_system_metrics(self) -> Dict[str, Any]:
        """Tool handler for collecting system metrics."""
        try:
            metrics = await self.collect_system_metrics()
            return {
                "metrics": metrics,
                "message": "Collected system metrics successfully"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_collect_app_metrics(
        self,
        app_name: str,
        pid: int,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Tool handler for collecting application metrics."""
        try:
            metrics = await self.collect_app_metrics(app_name, pid, custom_metrics)
            return {
                "metrics": metrics,
                "message": f"Collected metrics for application '{app_name}'"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_system_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for getting system metrics."""
        try:
            metrics = await self.get_system_metrics(start_time, end_time)
            return {"metrics": metrics}
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_app_metrics(
        self,
        app_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for getting application metrics."""
        try:
            metrics = await self.get_app_metrics(app_name, start_time, end_time)
            return {"metrics": metrics}
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_alerts(
        self,
        severity: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for getting alerts."""
        try:
            alerts = await self.get_alerts(severity, start_time, end_time)
            return {"alerts": alerts}
        except Exception as e:
            return {"error": str(e)}
