#!/usr/bin/env python3
import asyncio
import os
import sys
from typing import Dict, List, Any, Optional

from fastmcp import FastMCP
from loguru import logger

from core.system_awareness import SystemAwarenessManager
from core.mcp_discovery import MCPDiscoveryService
from core.knowledge_base import KnowledgeBaseManager
from core.project_lifecycle import ProjectLifecycleManager
from core.development_assistant import DevelopmentAssistantManager
from core.resource_manager import ResourceManager
from core.model_orchestration import ModelOrchestrationService
from core.collaboration import CollaborationManager
from tools import (
    environment_tools,
    project_tools, 
    architecture_tools,
    development_tools,
    testing_tools,
    deployment_tools,
    documentation_tools,
    code_tools
)

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add("logs/software_planning_mcp.log", rotation="10 MB", retention="1 week", level="DEBUG")

class SoftwarePlanningMCP:
    """Enhanced Software Planning MCP for AI-driven software development."""
    
    def __init__(self):
        self.mcp = FastMCP("software-planning-mcp")
        self.system_awareness = SystemAwarenessManager()
        self.mcp_discovery = MCPDiscoveryService()
        self.knowledge_base = KnowledgeBaseManager()
        self.project_lifecycle = ProjectLifecycleManager()
        self.development_assistant = DevelopmentAssistantManager()
        self.resource_manager = ResourceManager()
        self.model_orchestration = ModelOrchestrationService()
        self.collaboration = CollaborationManager()
        
        # Register all tools with MCP
        self._register_tools()
        
        logger.info("Software Planning MCP initialized")
    
    def _register_tools(self):
        """Register all tools with the MCP server."""
        all_tools = []
        
        # Environment detection and system awareness tools
        all_tools.extend(environment_tools.get_tools(self.system_awareness))
        
        # MCP discovery and integration tools
        all_tools.extend(self.mcp_discovery.get_tools())
        
        # Knowledge base tools
        all_tools.extend(self.knowledge_base.get_tools())
        
        # Project lifecycle tools
        all_tools.extend(self.project_lifecycle.get_tools())
        
        # Development assistant tools
        all_tools.extend(self.development_assistant.get_tools())
        
        # Resource management tools
        all_tools.extend(self.resource_manager.get_tools())
        
        # Model orchestration tools
        all_tools.extend(self.model_orchestration.get_tools())
        
        # Collaboration tools
        all_tools.extend(self.collaboration.get_tools())
        
        # Specialized tool categories
        all_tools.extend(project_tools.get_tools())
        all_tools.extend(architecture_tools.get_tools())
        all_tools.extend(development_tools.get_tools())
        all_tools.extend(testing_tools.get_tools())
        all_tools.extend(deployment_tools.get_tools())
        all_tools.extend(documentation_tools.get_tools())
        all_tools.extend(code_tools.get_tools())
        
        # Register all tools with MCP
        self.mcp.tools = all_tools
        logger.info(f"Registered {len(all_tools)} tools with the MCP server")
    
    async def start(self):
        """Start the Software Planning MCP server."""
        logger.info("Starting Software Planning MCP server")
        
        # Initialize system awareness
        await self.system_awareness.initialize()
        
        # Discover other MCPs
        await self.mcp_discovery.discover()
        
        # Initialize knowledge base
        await self.knowledge_base.initialize()
        
        # Run the MCP server
        await self.mcp.run_stdio_async()


async def main():
    """Main entry point for the Software Planning MCP server."""
    spmcp = SoftwarePlanningMCP()
    await spmcp.start()


if __name__ == "__main__":
    asyncio.run(main())
