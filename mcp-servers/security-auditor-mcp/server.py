#!/usr/bin/env python3
"""
Security Auditor MCP Server
===========================

Exposes the SecurityAuditor capabilities as an MCP server.
Allows other agents (Claude Code, Gemini CLI, Codex) to perform security audits.

MCP Tools:
- scan_codebase: Scan a directory or file for vulnerabilities.
- validate_change: Check if a proposed code change is safe.
- generate_patch: Generate a fix for a vulnerability.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "intelligent-agents"))

from security_auditor import SecurityAuditor, Vulnerability, Severity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("security-auditor-mcp")

# Create MCP server
server = Server("security-auditor-mcp")

# Initialize SecurityAuditor
# Note: In a real deployment, we might want to pass config
auditor = SecurityAuditor()

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available security tools."""
    return [
        types.Tool(
            name="scan_codebase",
            description="Scan a directory or file for security vulnerabilities using LLM analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file or directory to scan"
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="validate_change",
            description="Validate a proposed code change for security risks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code_before": {
                        "type": "string",
                        "description": "Original code content"
                    },
                    "code_after": {
                        "type": "string",
                        "description": "Proposed new code content"
                    }
                },
                "required": ["code_before", "code_after"]
            }
        ),
        types.Tool(
            name="generate_patch",
            description="Generate a code patch to fix a specific vulnerability.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the vulnerability"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the vulnerable file"
                    },
                    "suggested_fix": {
                        "type": "string",
                        "description": "Optional suggestion for the fix"
                    }
                },
                "required": ["description", "file_path"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if not arguments:
        arguments = {}

    if name == "scan_codebase":
        path = arguments.get("path", "")
        vulnerabilities = await auditor.scan_codebase(path)
        
        # Convert vulnerabilities to JSON-serializable format
        results = []
        for v in vulnerabilities:
            results.append({
                "file": v.file_path,
                "line": v.line_number,
                "severity": v.severity.value,
                "description": v.description,
                "fix": v.suggested_fix
            })
            
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "vulnerabilities": results,
                "count": len(results)
            }, indent=2)
        )]

    elif name == "validate_change":
        code_before = arguments.get("code_before", "")
        code_after = arguments.get("code_after", "")
        
        is_safe, issues = await auditor.validate_change(code_before, code_after)
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "is_safe": is_safe,
                "issues": issues
            }, indent=2)
        )]

    elif name == "generate_patch":
        description = arguments.get("description", "")
        file_path = arguments.get("file_path", "")
        suggested_fix = arguments.get("suggested_fix", "")
        
        # Create a dummy vulnerability object to pass to the auditor
        # In a real scenario, we might want a cleaner API
        vuln = Vulnerability(
            file_path=file_path,
            line_number=0,
            severity=Severity.HIGH,
            description=description,
            suggested_fix=suggested_fix
        )
        
        patch = await auditor.generate_patch(vuln)
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "patch": patch
            }, indent=2)
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Security Auditor MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="security-auditor-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
