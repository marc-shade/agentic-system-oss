# Software Planning MCP

A Model Context Protocol (MCP) server for AI-driven software project planning and task breakdown with cascading agent orchestration capabilities.

## Installation Status

✅ **Installed applied and Configured**

The software-planning-mcp server has been installed and configured in your Claude Desktop application.

## Features

This MCP server provides 8 powerful tools for project planning and orchestration: ### 1. **create_project**
Create a new software project with cascading task breakdown
- Parameters: name, description, project_type  (testing required), complexity (1-10)
- Automatically generates project phases based on type

### 2. **breakdown_project**
Break down a project into cascading tasks using agent orchestration patterns
- Generates hierarchical task structure with Level 0 (Orchestrator) and Level 1 (Lead Agents)
- Assigns appropriate AI agents to each task level

### 3. **create_task**
Create specific tasks within a project
- Assign multiple AI agents for parallel execution
- Set priorities and time estimates

### 4. **define_parallel_approaches**
Define parallel approaches for concurrent task execution
- Supports cascading agent orchestration patterns
- Enables multiple solution paths

### 5. **list_projects**
List all projects with optional filtering
- Filter by status or project type
- Get overview of all active projects

### 6. **get_project_status**
Get detailed status of a project including all tasks and agents
- View completion statistics
- Track assigned agents and hours

### 7. **suggest_agent_team**
Get AI agent team composition recommendations
- Based on project type and complexity
- Includes orchestrator, lead agents, specialists, and support roles

### 8. **generate_execution_plan**
Generate detailed execution plans with timelines
- Supports cascading, parallel, or hybrid execution styles
- Includes phase dependencies and parallel tracks

## Usage Examples

### Creating a Web Project with Cascading Breakdown

```
1. Use create_project:
   - name: "E-commerce Platform"
   - description: "Modern e-commerce site with AI recommendations"
   - project_type: "web"
   - complexity: 8

2. Use breakdown_project:
   - project_id: [from step 1]
   - detail_level: "high"

3. Use suggest_agent_team:
   - project_type: "web"
   - complexity: 8
   - specific_requirements: ["ai", "real-time", "payment processing"]
```

### Parallel Execution Pattern

```
1. Create a task using create_task
2. Use define_parallel_approaches with:
   - Conservative approach: "Use proven React + Node.js stack"
   - Modern approach: "Next.js 14 with Edge functions"
   - Experimental approach: "Remix with Deno Deploy"
```

## Configuration

The server is configured in Claude Desktop at:
```json
"software-planning": {
  "command": "/opt/homebrew/Caskroom/miniconda/base/bin/python",
  "args": [
    "/Users/marc/Documents/Cline/MCP/software-planning-mcp/src/server_simple.py"
  ],
  "env": {
    "PYTHONPATH": "/Users/marc/Documents/Cline/MCP/software-planning-mcp/src"
  }
}
```

## Technical Details

- Built with FastMCP for easy tool creation
- Simplified implementation without external dependencies
- In-memory storage for projects and tasks
- Supports cascading agent orchestration patterns
- Designed for parallel execution workflows

## Next Steps

To use the software-planning tools:

1. **Restart Claude Desktop** to load the new configuration
2. The tools will appear with the prefix `software-planning__`
3. Start by creating a project and breaking it down into cascading tasks
4. Use the agent team suggestions to orchestrate complex workflows

## Integration with Cascading Agent Orchestrator

This MCP server is designed to work seamlessly with your Cascading Agent Orchestrator role:

- **Level 0**: Use `create_project` and `breakdown_project` for orchestration
- **Level 1**: Tasks are automatically assigned to Lead Agents
- **Level 2-3**: Further breakdown happens through the orchestration patterns
- **Parallel Execution**: Use `define_parallel_approaches` for multiple solution paths

The server provides the structured foundation for your Delete It, Delegate It, Do It framework.