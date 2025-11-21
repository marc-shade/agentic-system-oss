#!/usr/bin/env python3
from typing import List, Dict, Any
from loguru import logger

def get_tools(system_awareness_manager) -> List[Dict[str, Any]]:
    """Get environment detection and system awareness tools."""
    return [
        {
            "name": "detect_environment",
            "description": "Detect the current development environment",
            "parameters": {},
            "function": system_awareness_manager.detect_environment
        },
        {
            "name": "list_system_resources",
            "description": "List available system resources",
            "parameters": {
                "resource_type": {
                    "type": "string",
                    "description": "Type of resource to list (cpu, memory, disk, etc.)"
                }
            },
            "function": system_awareness_manager.list_system_resources
        }
    ]
