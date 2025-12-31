"""
Planning and status tools for Enhanced Memory MCP Server.

Tools:
- save_implementation_plan: Save structured implementation plans
- get_memory_status: Get overall memory system status
"""

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

from ..config import DB_PATH, log_tool_usage, logger


def register_planning_tools(app, memory_client):
    """Register planning and status tools with FastMCP app."""

    @app.tool()
    async def save_implementation_plan(
        name: str,
        steps: List[Dict],
        description: Optional[str] = None
    ) -> Dict:
        """
        Save a structured implementation plan.

        Args:
            name: Plan name
            steps: List of step dictionaries
            description: Optional plan description

        Returns:
            Result of the save operation
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create entity for the plan
        entity_name = f"plan_{name}"
        plan_data = {
            'name': name,
            'description': description,
            'steps': steps,
            'type': 'implementation_plan'
        }

        # Create as entity with versioning via memory client
        result = await memory_client.create_entities([{
            'name': entity_name,
            'entityType': 'implementation_plan',
            'observations': [f"Step {i+1}: {step}" for i, step in enumerate(steps)]
        }])

        # Also save in specialized table
        cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
        entity_row = cursor.fetchone()
        entity_id = entity_row[0] if entity_row else None

        cursor.execute('''
            INSERT INTO implementation_plans (name, description, steps, entity_id)
            VALUES (?, ?, ?, ?)
        ''', (name, description, json.dumps(steps), entity_id))

        conn.commit()
        conn.close()

        return {
            'success': True,
            'name': name,
            'step_count': len(steps),
            'entity_name': entity_name,
            'versioned': True,
            'message': f"Implementation plan '{name}' saved with version control"
        }

    @app.tool()
    async def get_memory_status() -> Dict:
        """
        Get overall memory system status and statistics.

        CONCURRENT ACCESS: Uses memory-db Unix socket service for core stats.

        Returns:
            System statistics and health information
        """
        _start = time.time()
        try:
            # Get basic stats from memory-db service
            response = await memory_client.get_memory_status()

            if response.get("success"):
                # Return the stats from memory-db
                return response
            else:
                return {
                    "error": response.get("error", "Unknown error from memory-db service"),
                    "entities": {"total": 0},
                    "compression": {"ratio": "N/A"}
                }

        except Exception as e:
            log_tool_usage("get_memory_status", "core", False, (time.time() - _start) * 1000)
            logger.error(f"Error getting memory status via memory-db: {str(e)}")
            return {
                "error": f"Memory-DB service error: {str(e)}",
                "entities": {"total": 0},
                "compression": {"ratio": "N/A"}
            }
        finally:
            log_tool_usage("get_memory_status", "core", True, (time.time() - _start) * 1000)

    return {
        'save_implementation_plan': save_implementation_plan,
        'get_memory_status': get_memory_status,
    }
