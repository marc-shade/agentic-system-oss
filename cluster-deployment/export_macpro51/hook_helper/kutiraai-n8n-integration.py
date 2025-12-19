#!/usr/bin/env python3
"""
KutiraAI and n8n Integration Hook for MCP System
Provides seamless integration with the existing agentic monitoring system
"""

import os
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path

class KutiraiN8nIntegration:
    def __init__(self):
        self.base_dir = Path("/home/marc/.claude")
        self.status_file = self.base_dir / "logs" / "service-status.json"

    def get_service_status(self):
        """Get current status of KutiraAI and n8n services"""
        try:
            # Run our health check script
            result = subprocess.run(
                [str(self.base_dir / "kutiraai-n8n-health.sh"), "status"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Extract key information
            output = result.stdout
            healthy = "🎉 All services are healthy!" in output

            status = {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": healthy,
                "services": {
                    "kutiraai": {
                        "frontend_port": 3001,
                        "api_port": 3002,
                        "backend_port": 8000,
                        "healthy": "Port 3001: Active" in output and "Port 3002: Active" in output,
                        "urls": [
                            "http://localhost:3001",
                            "http://localhost:3002",
                            "http://localhost:8000"
                        ]
                    },
                    "n8n": {
                        "port": 5678,
                        "healthy": "Port 5678: Active" in output,
                        "url": "http://localhost:5678"
                    }
                }
            }

            # Save status for other tools
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)

            return status

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "overall_healthy": False
            }

    def restart_failed_services(self):
        """Restart any failed services"""
        try:
            subprocess.run([
                str(self.base_dir / "manage-services.sh"), "restart"
            ], check=True, timeout=60)
            return True
        except Exception:
            return False

    def get_integration_info(self):
        """Get information for MCP system integration"""
        status = self.get_service_status()

        integration_info = {
            "service_type": "automation_platform",
            "capabilities": [
                "workflow_automation",
                "ai_interface",
                "api_endpoints",
                "visual_workflow_designer"
            ],
            "endpoints": {
                "kutiraai_frontend": "http://localhost:3001",
                "kutiraai_api": "http://localhost:3002",
                "n8n_workflows": "http://localhost:5678"
            },
            "health_status": status,
            "management_commands": {
                "status": f"{self.base_dir}/manage-services.sh status",
                "restart": f"{self.base_dir}/manage-services.sh restart",
                "logs": f"{self.base_dir}/manage-services.sh logs"
            }
        }

        return integration_info

def main():
    """Main function for standalone execution"""
    integration = KutiraiN8nIntegration()

    # Get and display status
    status = integration.get_service_status()
    print(json.dumps(status, indent=2))

    # Show integration info
    info = integration.get_integration_info()
    print("\nIntegration Information:")
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    main()