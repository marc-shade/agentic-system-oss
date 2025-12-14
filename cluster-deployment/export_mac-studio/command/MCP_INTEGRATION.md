# MCP Integration for Slash Commands

## Overview
These slash commands integrate with 67+ MCP servers to provide comprehensive functionality.

## Key Integrations

### AI Prompt Library
- **Server**: ai-prompt-library
- **Agents**: 157+ specialized AI agents
- **Commands**: All `/ai-*` commands
- **Usage**: `/user:ai-business consultant` loads Agency Consultant

### Document Processing
- **Servers**: docsingest-mcp, crawl4ai-mcp, obsidian-mcp
- **Tools**: PDF processing, web extraction, note management
- **Commands**: `/document-processing`, `/pdf-create`

### Business Intelligence
- **Servers**: lead-generator-mcp, pitchdeck-generator, market-research-mcp
- **Tools**: Lead generation, pitch creation, market analysis
- **Commands**: `/business-intelligence`, `/lead-gen`

### Communication
- **Servers**: slack-mcp, discord-mcp, apple-mcp
- **Tools**: Multi-platform messaging
- **Commands**: `/communication-hub`, `/apple-*`

### Database Operations
- **Servers**: sqlite-mcp, postgres-mcp, vector-db-mcp
- **Tools**: Query execution, data analysis
- **Commands**: `/database-tools`

### Creative Tools
- **Servers**: image-gen-mcp, pip-deck-mcp
- **Tools**: Image generation, workshop facilitation
- **Commands**: `/image-generation`, `/workshop-tactics`

## Command Execution Flow
1. Slash command triggered
2. Parameter parsing and validation
3. MCP tool selection and invocation
4. AI agent integration (if applicable)
5. Result formatting and return

## Setup Requirements
- All MCP servers must be running
- Claude Desktop configuration updated
- Environment variables configured
- Network connectivity for remote tools

