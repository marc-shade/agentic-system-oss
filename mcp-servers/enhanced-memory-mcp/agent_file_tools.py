#!/usr/bin/env python3
"""
Agent File Tools for FastMCP

Registers MCP tools for agent state export/import using .af format.
"""

import logging
from typing import Dict, Any
from pathlib import Path
from agent_file import AgentFileExporter, AgentFileImporter

logger = logging.getLogger(__name__)

# Default export directory
EXPORT_DIR = Path.home() / ".claude" / "enhanced_memories" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def register_agent_file_tools(app, db_path):
    """Register all agent file tools with FastMCP app"""

    exporter = AgentFileExporter(db_path)
    importer = AgentFileImporter(db_path)

    @app.tool()
    async def export_agent_to_file(
        agent_id: str,
        filename: str = None,
        include_entities: bool = True,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Export agent state to .af file for backup or transfer.

        Creates a portable agent file containing:
        - All memory blocks (identity, human, task, learnings)
        - Entities (episodic, semantic, procedural, working)
        - Metadata (timestamps, cluster info)

        Args:
            agent_id: Agent to export
            filename: Output filename (default: {agent_id}_{timestamp}.af)
            include_entities: Include long-term entities (default True)
            compress: Gzip compress (default True)

        Returns:
            Export result with file path and statistics

        Example:
            export_agent_to_file(agent_id="my_agent", compress=True)
        """
        from datetime import datetime

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{agent_id}_{timestamp}.af"

        output_path = EXPORT_DIR / filename

        return exporter.save_agent_file(
            agent_id=agent_id,
            output_path=output_path,
            compress=compress
        )

    @app.tool()
    async def import_agent_from_file(
        file_path: str,
        new_agent_id: str = None,
        import_entities: bool = True
    ) -> Dict[str, Any]:
        """
        Import agent state from .af file.

        Restores complete agent state including memory blocks and entities.

        Args:
            file_path: Path to .af file
            new_agent_id: Optional new agent ID (defaults to original)
            import_entities: Import long-term entities (default True)

        Returns:
            Import result with statistics

        Example:
            import_agent_from_file(file_path="/path/to/agent.af", new_agent_id="restored_agent")
        """
        return importer.import_agent(
            file_path=Path(file_path),
            new_agent_id=new_agent_id,
            import_entities=import_entities
        )

    @app.tool()
    async def list_agent_files() -> Dict[str, Any]:
        """
        List all available agent files in export directory.

        Returns:
            List of .af files with metadata

        Example:
            list_agent_files()
        """
        files = []

        for af_file in EXPORT_DIR.glob("*.af"):
            stat = af_file.stat()
            files.append({
                "filename": af_file.name,
                "path": str(af_file),
                "size_kb": stat.st_size / 1024,
                "modified": stat.st_mtime
            })

        return {
            "success": True,
            "export_directory": str(EXPORT_DIR),
            "count": len(files),
            "files": sorted(files, key=lambda x: x["modified"], reverse=True)
        }

    logger.info("✅ Agent File tools registered (3 tools)")
    logger.info(f"   Export directory: {EXPORT_DIR}")
