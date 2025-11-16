#!/usr/bin/env python3
"""
Agent Memory Integration - Production-ready shared memory access

Provides robust synchronous memory integration for all intelligent agents.
Handles async memory client operations internally using asyncio.

Author: Enhanced Memory System
Date: 2025-11-09
Status: Production-ready
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add MCP client path
MCP_PATH = Path(__file__).parent.parent.parent / "mcp-servers" / "enhanced-memory-mcp"
sys.path.insert(0, str(MCP_PATH))

try:
    from memory_client import MemoryClient
    MEMORY_AVAILABLE = True
    logger.info("✅ Memory client available")
except ImportError as e:
    MEMORY_AVAILABLE = False
    logger.warning(f"⚠️  Memory client not available: {e}")


class AgentMemory:
    """
    Production-ready synchronous memory integration for intelligent agents
    
    Handles async memory operations internally, provides simple sync API.
    """

    def __init__(self, agent_name: str):
        """Initialize agent memory"""
        self.agent_name = agent_name
        self.enabled = MEMORY_AVAILABLE
        self.client = MemoryClient() if self.enabled else None
        logger.info(f"Initialized AgentMemory for: {agent_name} (enabled: {self.enabled})")

    def remember(
        self,
        observation: Dict[str, Any],
        entity_type: str = "agent_observation",
        importance: float = 0.5
    ) -> Optional[str]:
        """Store observation in memory (sync wrapper for async operation)"""
        if not self.enabled:
            return None

        try:
            # Create entity name
            timestamp = datetime.now().isoformat()
            obs_type = observation.get("type", "general")
            entity_name = f"{self.agent_name}-{obs_type}-{timestamp}"

            # Prepare observations
            observations = [f"{k}: {v}" for k, v in observation.items()]
            observations.extend([
                f"agent: {self.agent_name}",
                f"timestamp: {timestamp}",
                f"importance: {importance}"
            ])

            # Call async function synchronously
            result = asyncio.run(self.client.create_entities([{
                "name": entity_name,
                "entityType": entity_type,
                "observations": observations
            }]))

            if result and result.get('success') and len(result.get('results', [])) > 0:
                entity_id = str(result['results'][0].get("id"))
                logger.info(f"✅ Stored: {entity_name}")
                return entity_id
            return None

        except Exception as e:
            logger.error(f"❌ Remember failed: {e}")
            return None

    def recall(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memory (sync wrapper for async operation)"""
        if not self.enabled:
            return []

        try:
            # Call async function synchronously
            results = asyncio.run(self.client.search_nodes(
                query=query,
                limit=limit
            ))
            logger.info(f"✅ Found {len(results)} results")
            return results if results else []

        except Exception as e:
            logger.error(f"❌ Recall failed: {e}")
            return []

    def get_history(
        self,
        limit: int = 50,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get agent's memory history"""
        if not self.enabled:
            return []

        try:
            query = f"agent:{self.agent_name}"
            if event_type:
                query += f" type:{event_type}"

            results = asyncio.run(self.client.search_nodes(
                query=query,
                limit=limit
            ))
            return results if results else []

        except Exception as e:
            logger.error(f"❌ History retrieval failed: {e}")
            return []

    def is_enabled(self) -> bool:
        """Check if memory is enabled"""
        return self.enabled


# Convenience function
def get_agent_memory(agent_name: str) -> AgentMemory:
    """Get AgentMemory instance for an agent"""
    return AgentMemory(agent_name)


# Self-test
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Agent Memory Integration Test (Production)")
    print("=" * 60)

    memory = AgentMemory("test_agent_production")

    if memory.is_enabled():
        print("\n✅ Memory service connected\n")

        # Test 1: Store
        print("1. Testing remember()...")
        entity_id = memory.remember({
            "type": "test_event",
            "status": "success",
            "message": "Production memory test"
        })
        print(f"   Stored: {entity_id}\n")

        # Test 2: Recall
        print("2. Testing recall()...")
        results = memory.recall("test", limit=5)
        print(f"   Found: {len(results)} results\n")

        # Test 3: History
        print("3. Testing get_history()...")
        history = memory.get_history(limit=10)
        print(f"   Found: {len(history)} entries\n")

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60 + "\n")
    else:
        print("\n❌ Memory service not available\n")
