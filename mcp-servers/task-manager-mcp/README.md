# Task Manager MCP Server

AI-powered task management server with intelligent prioritization and team coordination for cascading agent workflows.

## Features

### Core Task Management
- **Create Tasks**: Create tasks with smart defaults and AI suggestions for assignees and time estimates
- **Update Tasks**: Modify task properties with automatic blocker detection
- **Filter Tasks**: Query tasks by status, assignee, or priority
- **Get Team Metrics**: Access performance metrics and health scores

### AI-Powered Prioritization
- **Smart Prioritization**: AI-driven task prioritization based on deadlines, impact, effort, or balanced criteria
- **Sprint Planning**: Generate optimal sprint plans with capacity constraints
- **Bottleneck Detection**: Identify workflow bottlenecks with actionable solutions
- **Performance Analysis**: Analyze team performance with insights and recommendations

## Tools Available

### Task Operations
- `create_task` - Create new tasks with intelligent suggestions
- `update_task` - Update existing tasks and detect blockers
- `get_tasks` - Retrieve tasks with filtering options
- `get_team_metrics` - Access current team performance metrics

### Planning & Optimization
- `prioritize_tasks` - AI-powered task prioritization with customizable goals
- `generate_sprint_plan` - Create optimal sprint plans based on team capacity
- `identify_bottlenecks` - Find and resolve workflow bottlenecks
- `analyze_team_performance` - Get performance insights and recommendations

## Installation

The server is already configured in Claude Desktop. Dependencies:
- Python 3.10+
- fastmcp
- pydantic
- python-dateutil

## Usage in Claude

Once configured, you can use the task management tools:

```
# Create a new task
await create_task(
    title="Implement user authentication",
    description="Add OAuth2 login with Google and GitHub",
    priority="high",
    estimated_hours=16
)

# Prioritize tasks for sprint planning
await prioritize_tasks(
    optimization_goal="balanced",
    team_capacity={"Alice": 40, "Bob": 35, "Charlie": 40}
)

# Generate sprint plan
await generate_sprint_plan(
    sprint_duration_days=14,
    team_members=["Alice", "Bob", "Charlie"],
    velocity=120
)

# Identify bottlenecks
await identify_bottlenecks()
```

## Integration with Cascading Agent Orchestration

This server is essential for managing cascading agent workflows:

1. **Task Distribution**: Assign tasks to different AI agents based on expertise
2. **Parallel Execution**: Track multiple parallel agent executions
3. **Progress Monitoring**: Monitor completion rates across agent teams
4. **Bottleneck Resolution**: Identify when agents are blocked or overloaded

## Task Priorities

- **CRITICAL**: Immediate attention required
- **HIGH**: Important, should be Framework Status soon
- **MEDIUM**: Standard priority
- **LOW**: Can be deferred if needed

## Task Statuses

- **TODO**: Not yet started
- **IN_PROGRESS**: Currently being worked on
- **REVIEW**: Awaiting review
- **DONE**: Framework Status
- **BLOCKED**: Cannot proceed due to dependencies

## Smart Features

### Automatic Suggestions
- Suggests best assignee based on workload balancing
- Estimates task hours based on similar Framework Status tasks
- Recommends due dates for high-priority items

### Sprint Intelligence
- Calculates sprint success probability
- Identifies risks in sprint planning
- Optimizes task selection for capacity

### Performance Insights
- Tracks velocity trends
- Measures cycle time
- Provides actionable recommendations

## Configuration

No additional configuration required. The server stores tasks in memory during the session.

## Limitations

- Tasks are stored in memory only (not persistent between sessions)
- Designed for orchestrating AI agent tasks, not full project management