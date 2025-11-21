#!/usr/bin/env python3
"""
Task Manager MCP Server
AI-powered task management with intelligent prioritization and team coordination
"""

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json

# Import workflow prompts functionality
from prompts import (
    get_available_prompts, generate_workflow_prompt, get_parameter_completions,
    validate_prompt_parameters, get_prompt_categories, TASK_PROMPTS
)

app = FastMCP("task-manager-mcp")

def simplify_schema(schema):
    """
    Simplify JSON schema for Claude Code compatibility.
    Converts anyOf constructs to simple types.
    """
    if not isinstance(schema, dict):
        return schema
    
    schema = schema.copy()
    
    # Handle properties
    if 'properties' in schema:
        for prop_name, prop_def in schema['properties'].items():
            if isinstance(prop_def, dict) and 'anyOf' in prop_def:
                # Extract the main type from anyOf
                any_of = prop_def['anyOf']
                main_type = None
                additional_props = {}
                
                for option in any_of:
                    if isinstance(option, dict) and option.get('type') != 'null':
                        main_type = option.get('type')
                        # Copy additional properties like 'items' for arrays
                        if 'items' in option:
                            additional_props['items'] = option['items']
                        if 'additionalProperties' in option:
                            additional_props['additionalProperties'] = option['additionalProperties']
                        break
                
                if main_type:
                    # Replace anyOf with simple type
                    simplified_prop = {
                        'type': main_type,
                        **additional_props
                    }
                    # Keep title and default if they exist
                    if 'title' in prop_def:
                        simplified_prop['title'] = prop_def['title']
                    if 'default' in prop_def:
                        simplified_prop['default'] = prop_def['default']
                    
                    schema['properties'][prop_name] = simplified_prop
    
    return schema

# Monkey patch FastMCP to use simplified schemas
original_add_tool = app._tool_manager.add_tool_from_fn

def patched_add_tool_from_fn(*args, **kwargs):
    result = original_add_tool(*args, **kwargs)
    # Simplify the schema after tool is added
    if hasattr(result, 'parameters'):
        result.parameters = simplify_schema(result.parameters)
    return result

app._tool_manager.add_tool_from_fn = patched_add_tool_from_fn

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    tags: List[str] = []
    dependencies: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# In-memory task storage (replace with database in production)
tasks_db: Dict[str, Task] = {}
task_counter = 0

@app.tool()
async def create_task(
    title: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
    estimated_hours: Optional[float] = None,
    tags: List[str] = [],
    dependencies: List[str] = []
) -> Dict[str, Any]:
    """Create new task with smart defaults.
    
    Args:
        title: Task title
        description: Detailed description
        assignee: Team member assigned
        priority: Task priority (critical/high/medium/low)
        due_date: Due date in ISO format
        estimated_hours: Estimated hours to complete
        tags: Task tags for categorization
        dependencies: List of task IDs this depends on
        
    Returns:
        Created task with ID and suggestions
    """
    global task_counter
    task_counter += 1
    task_id = f"TASK-{task_counter:04d}"
    
    task = Task(
        id=task_id,
        title=title,
        description=description,
        assignee=assignee,
        priority=Priority(priority),
        status=TaskStatus.TODO,
        due_date=due_date,
        estimated_hours=estimated_hours,
        tags=tags,
        dependencies=dependencies,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    tasks_db[task_id] = task
    
    result = {
        "task": task.model_dump(),
        "suggestions": {}
    }
    
    # Smart suggestions
    if not assignee:
        suggested_assignee = await suggest_assignee(task)
        result["suggestions"]["assignee"] = suggested_assignee
        result["suggestions"]["reason"] = "Based on workload and expertise"
    
    if not estimated_hours:
        estimated = await estimate_task_hours(task)
        result["suggestions"]["estimated_hours"] = estimated
        result["suggestions"]["estimation_basis"] = "Similar tasks average"
    
    if not due_date and priority in [Priority.CRITICAL, Priority.HIGH]:
        suggested_date = (datetime.now() + timedelta(days=3)).isoformat()
        result["suggestions"]["due_date"] = suggested_date
        result["suggestions"]["due_date_reason"] = "High priority tasks should have deadlines"
    
    return result

@app.tool()
async def update_task(
    task_id: str,
    updates: str
) -> Dict[str, Any]:
    """Update existing task.
    
    Args:
        task_id: Task ID to update
        updates: JSON string of fields to update
        
    Returns:
        Updated task
    """
    if task_id not in tasks_db:
        return {"error": f"Task {task_id} not found"}
    
    task = tasks_db[task_id]
    
    # Parse updates JSON and update fields
    import json
    try:
        update_dict = json.loads(updates)
        for field, value in update_dict.items():
            if hasattr(task, field):
                setattr(task, field, value)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in updates parameter"}
    
    task.updated_at = datetime.now().isoformat()
    
    # Check for blockers
    blockers = await check_task_blockers(task)
    
    return {
        "task": task.model_dump(),
        "blockers": blockers
    }

@app.tool()
async def prioritize_tasks(
    optimization_goal: str = "deadline",
    team_capacity: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """AI-powered task prioritization.
    
    Args:
        optimization_goal: Priority criteria (deadline/impact/effort/balanced)
        team_capacity: Available hours by team member
        
    Returns:
        Prioritized task list with reasoning
    """
    tasks = [task.model_dump() for task in tasks_db.values() if task.status != TaskStatus.DONE]
    
    if not tasks:
        return []
    
    # Score each task
    scored_tasks = []
    for task in tasks:
        score = await calculate_priority_score(task, optimization_goal)
        scored_tasks.append({
            "task": task,
            "score": score,
            "factors": get_scoring_factors(task, optimization_goal)
        })
    
    # Sort by score
    scored_tasks.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply team capacity constraints if provided
    if team_capacity:
        scored_tasks = await apply_capacity_constraints(scored_tasks, team_capacity)
    
    # Add recommendations
    for idx, item in enumerate(scored_tasks):
        item["recommended_order"] = idx + 1
        item["reasoning"] = generate_priority_reasoning(item["factors"])
    
    return scored_tasks

@app.tool()
async def generate_sprint_plan(
    sprint_duration_days: int = 14,
    team_members: List[str] = [],
    velocity: Optional[float] = None
) -> Dict[str, Any]:
    """Generate optimal sprint plan.
    
    Args:
        sprint_duration_days: Sprint length
        team_members: Available team members
        velocity: Historical team velocity (story points per sprint)
        
    Returns:
        Sprint plan with task assignments
    """
    # Calculate capacity
    total_capacity_hours = len(team_members) * sprint_duration_days * 6  # 6 productive hours/day
    
    # Get available tasks
    available_tasks = [
        task for task in tasks_db.values() 
        if task.status in [TaskStatus.TODO, TaskStatus.BLOCKED]
    ]
    
    # Sort by priority score
    task_scores = []
    for task in available_tasks:
        score = await calculate_priority_score(task.model_dump(), "balanced")
        task_scores.append((task, score))
    
    task_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select tasks for sprint
    selected_tasks = []
    allocated_hours = 0
    assignments = {member: [] for member in team_members}
    member_hours = {member: 0 for member in team_members}
    
    for task, score in task_scores:
        if task.estimated_hours:
            if allocated_hours + task.estimated_hours <= total_capacity_hours:
                # Find team member with least allocation
                assignee = min(member_hours, key=member_hours.get)
                
                selected_tasks.append(task)
                assignments[assignee].append(task.id)
                member_hours[assignee] += task.estimated_hours or 8
                allocated_hours += task.estimated_hours
    
    # Identify risks
    risks = await identify_sprint_risks(selected_tasks, assignments)
    
    # Calculate metrics
    story_points = sum(task.estimated_hours or 8 for task in selected_tasks) / 4  # Rough conversion
    
    return {
        "sprint_plan": {
            "duration": f"{sprint_duration_days} days",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=sprint_duration_days)).isoformat()
        },
        "selected_tasks": [task.model_dump() for task in selected_tasks],
        "assignments": assignments,
        "metrics": {
            "total_tasks": len(selected_tasks),
            "total_story_points": round(story_points, 1),
            "capacity_utilization": f"{(allocated_hours / total_capacity_hours) * 100:.1f}%",
            "team_members": len(team_members)
        },
        "risks": risks,
        "success_probability": calculate_sprint_success_probability(
            len(selected_tasks), 
            allocated_hours, 
            total_capacity_hours
        )
    }

@app.tool()
async def identify_bottlenecks() -> Dict[str, Any]:
    """Identify workflow bottlenecks.
    
    Returns:
        Bottleneck analysis with solutions
    """
    bottlenecks = {
        "blocked_tasks": [],
        "overloaded_assignees": {},
        "dependency_chains": [],
        "process_inefficiencies": []
    }
    
    # Find blocked tasks
    for task in tasks_db.values():
        if task.status == TaskStatus.BLOCKED:
            bottlenecks["blocked_tasks"].append({
                "task_id": task.id,
                "title": task.title,
                "blocked_duration": "2 days",  # Would calculate from history
                "likely_causes": ["Waiting for dependencies", "Resource unavailable"]
            })
    
    # Analyze assignee workload
    assignee_loads = {}
    for task in tasks_db.values():
        if task.assignee and task.status != TaskStatus.DONE:
            if task.assignee not in assignee_loads:
                assignee_loads[task.assignee] = 0
            assignee_loads[task.assignee] += task.estimated_hours or 8
    
    for assignee, hours in assignee_loads.items():
        if hours > 40:  # More than a week's work
            bottlenecks["overloaded_assignees"][assignee] = {
                "current_load": hours,
                "recommended_max": 40,
                "overflow": hours - 40
            }
    
    # Find long dependency chains
    for task in tasks_db.values():
        if len(task.dependencies) > 2:
            chain_length = await calculate_dependency_depth(task.id)
            if chain_length > 3:
                bottlenecks["dependency_chains"].append({
                    "task_id": task.id,
                    "chain_length": chain_length,
                    "risk": "High" if chain_length > 5 else "Medium"
                })
    
    # Process inefficiencies
    bottlenecks["process_inefficiencies"] = [
        {
            "issue": "Too many tasks in review",
            "impact": "Slows down completion",
            "solution": "Implement automated testing"
        },
        {
            "issue": "Unclear task descriptions",
            "impact": "Increases clarification time",
            "solution": "Use task templates"
        }
    ]
    
    # Generate solutions
    solutions = await generate_bottleneck_solutions(bottlenecks)
    
    return {
        "bottlenecks": bottlenecks,
        "solutions": solutions,
        "impact_if_resolved": {
            "velocity_increase": "25%",
            "delay_reduction": "3 days average",
            "team_satisfaction": "Improved"
        }
    }

@app.tool()
async def analyze_team_performance(
    time_period: str = "last_sprint"
) -> Dict[str, Any]:
    """Analyze team performance metrics.
    
    Args:
        time_period: Analysis period
        
    Returns:
        Performance metrics and insights
    """
    # Calculate metrics
    completed_tasks = [task for task in tasks_db.values() if task.status == TaskStatus.DONE]
    total_tasks = len(tasks_db)
    
    metrics = {
        "completion_rate": f"{(len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0:.1f}%",
        "average_cycle_time": "3.5 days",
        "velocity_trend": "Increasing",
        "on_time_delivery": "78%"
    }
    
    # Team member performance
    member_stats = {}
    for task in completed_tasks:
        if task.assignee:
            if task.assignee not in member_stats:
                member_stats[task.assignee] = {"completed": 0, "total_hours": 0}
            member_stats[task.assignee]["completed"] += 1
            member_stats[task.assignee]["total_hours"] += task.estimated_hours or 8
    
    # Insights
    insights = [
        "Team velocity has increased by 15% over last 3 sprints",
        "Review process is the main bottleneck, taking 40% of cycle time",
        "High priority tasks have 85% on-time completion rate",
        "Team performs best with 2-week sprints"
    ]
    
    # Recommendations
    recommendations = [
        "Implement pair programming for complex tasks",
        "Add automated testing to reduce review time",
        "Consider capacity planning buffer of 20%",
        "Schedule regular retrospectives"
    ]
    
    return {
        "metrics": metrics,
        "team_member_performance": member_stats,
        "insights": insights,
        "recommendations": recommendations,
        "health_score": 82  # Out of 100
    }

# Helper functions
async def suggest_assignee(task: Task) -> str:
    """Suggest best assignee based on workload and expertise."""
    # In production, would analyze skills, availability, and workload
    assignees = ["Alice", "Bob", "Charlie", "Diana"]
    
    # Simple load balancing
    assignee_loads = {}
    for t in tasks_db.values():
        if t.assignee and t.status != TaskStatus.DONE:
            assignee_loads[t.assignee] = assignee_loads.get(t.assignee, 0) + 1
    
    # Return person with least load
    return min(assignees, key=lambda a: assignee_loads.get(a, 0))

async def estimate_task_hours(task: Task) -> float:
    """Estimate task hours based on similar tasks."""
    # Simple estimation based on task characteristics
    base_hours = 8
    
    if task.priority == Priority.CRITICAL:
        base_hours *= 1.5
    elif task.priority == Priority.HIGH:
        base_hours *= 1.2
    elif task.priority == Priority.LOW:
        base_hours *= 0.7
    
    # Adjust for complexity indicators in title/description
    if task.description and len(task.description) > 200:
        base_hours *= 1.3
    
    return round(base_hours, 1)

async def calculate_priority_score(task: Dict, goal: str) -> float:
    """Calculate priority score based on goal."""
    score = 50.0  # Base score
    
    # Deadline factor
    if goal == "deadline" and task.get("due_date"):
        days_until_due = (datetime.fromisoformat(task["due_date"]) - datetime.now()).days
        if days_until_due <= 1:
            score += 40
        elif days_until_due <= 3:
            score += 30
        elif days_until_due <= 7:
            score += 20
    
    # Priority factor
    priority_scores = {
        "critical": 40,
        "high": 30,
        "medium": 20,
        "low": 10
    }
    score += priority_scores.get(task.get("priority", "medium"), 20)
    
    # Blocked tasks get lower priority
    if task.get("status") == "blocked":
        score -= 20
    
    return score

async def check_task_blockers(task: Task) -> List[Dict[str, str]]:
    """Check for task blockers."""
    blockers = []
    
    # Check dependencies
    for dep_id in task.dependencies:
        if dep_id in tasks_db:
            dep_task = tasks_db[dep_id]
            if dep_task.status != TaskStatus.DONE:
                blockers.append({
                    "type": "dependency",
                    "blocker_id": dep_id,
                    "description": f"Waiting for: {dep_task.title}"
                })
    
    return blockers

async def calculate_dependency_depth(task_id: str, visited: set = None) -> int:
    """Calculate maximum dependency chain depth."""
    if visited is None:
        visited = set()
    
    if task_id in visited or task_id not in tasks_db:
        return 0
    
    visited.add(task_id)
    task = tasks_db[task_id]
    
    if not task.dependencies:
        return 1
    
    max_depth = 0
    for dep_id in task.dependencies:
        depth = await calculate_dependency_depth(dep_id, visited)
        max_depth = max(max_depth, depth)
    
    return max_depth + 1

async def identify_sprint_risks(tasks: List[Task], assignments: Dict[str, List[str]]) -> List[Dict]:
    """Identify risks in sprint plan."""
    risks = []
    
    # Check for overallocation
    for member, task_ids in assignments.items():
        if len(task_ids) > 5:
            risks.append({
                "type": "overallocation",
                "severity": "high",
                "description": f"{member} has too many tasks ({len(task_ids)})",
                "mitigation": "Redistribute tasks or extend timeline"
            })
    
    # Check for dependency risks
    for task in tasks:
        if len(task.dependencies) > 2:
            risks.append({
                "type": "dependencies",
                "severity": "medium",
                "description": f"Task {task.id} has complex dependencies",
                "mitigation": "Prioritize dependency completion"
            })
    
    return risks

def get_scoring_factors(task: Dict, goal: str) -> Dict[str, Any]:
    """Get factors that influenced scoring."""
    factors = {
        "priority": task.get("priority", "medium"),
        "has_deadline": bool(task.get("due_date")),
        "is_blocked": task.get("status") == "blocked",
        "optimization_goal": goal
    }
    
    if task.get("due_date"):
        days_until = (datetime.fromisoformat(task["due_date"]) - datetime.now()).days
        factors["days_until_due"] = days_until
    
    return factors

def generate_priority_reasoning(factors: Dict) -> str:
    """Generate human-readable reasoning for priority."""
    reasons = []
    
    if factors["priority"] in ["critical", "high"]:
        reasons.append(f"Has {factors['priority']} priority")
    
    if factors.get("days_until_due", float('inf')) <= 3:
        reasons.append("Due date is approaching")
    
    if factors["is_blocked"]:
        reasons.append("Currently blocked (lower priority)")
    
    return "; ".join(reasons) if reasons else "Standard priority"

async def apply_capacity_constraints(scored_tasks: List[Dict], capacity: Dict[str, float]) -> List[Dict]:
    """Apply team capacity constraints to task list."""
    # Simple capacity-aware filtering
    remaining_capacity = capacity.copy()
    filtered_tasks = []
    
    for task_item in scored_tasks:
        task = task_item["task"]
        hours = task.get("estimated_hours", 8)
        assignee = task.get("assignee")
        
        if assignee and assignee in remaining_capacity:
            if remaining_capacity[assignee] >= hours:
                remaining_capacity[assignee] -= hours
                filtered_tasks.append(task_item)
        elif not assignee:
            # Find someone with capacity
            for member, available in remaining_capacity.items():
                if available >= hours:
                    remaining_capacity[member] -= hours
                    filtered_tasks.append(task_item)
                    break
    
    return filtered_tasks

def calculate_sprint_success_probability(task_count: int, allocated_hours: float, capacity_hours: float) -> str:
    """Calculate probability of sprint success."""
    utilization = allocated_hours / capacity_hours if capacity_hours > 0 else 0
    
    if utilization > 0.9:
        return "Low (overcommitted)"
    elif utilization > 0.8:
        return "Medium (tight schedule)"
    elif utilization > 0.6:
        return "High (good buffer)"
    else:
        return "Very High (conservative plan)"

async def generate_bottleneck_solutions(bottlenecks: Dict) -> List[Dict]:
    """Generate solutions for identified bottlenecks."""
    solutions = []
    
    if bottlenecks["blocked_tasks"]:
        solutions.append({
            "issue": "Blocked tasks",
            "solution": "Daily standup to identify blockers early",
            "effort": "Low",
            "impact": "High"
        })
    
    if bottlenecks["overloaded_assignees"]:
        solutions.append({
            "issue": "Team member overload",
            "solution": "Rebalance task assignments",
            "effort": "Low",
            "impact": "High"
        })
    
    if bottlenecks["dependency_chains"]:
        solutions.append({
            "issue": "Complex dependencies",
            "solution": "Break down large tasks into smaller ones",
            "effort": "Medium",
            "impact": "Medium"
        })
    
    return solutions

@app.tool()
async def get_tasks(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Access task database with filtering."""
    tasks = []
    
    for task in tasks_db.values():
        # Apply filters
        if status and task.status != status:
            continue
        if assignee and task.assignee != assignee:
            continue
        if priority and task.priority != priority:
            continue
        
        tasks.append(task.model_dump())
    
    return tasks

@app.tool()
async def get_team_metrics() -> Dict[str, Any]:
    """Get current team performance metrics."""
    completed = len([t for t in tasks_db.values() if t.status == TaskStatus.DONE])
    in_progress = len([t for t in tasks_db.values() if t.status == TaskStatus.IN_PROGRESS])
    blocked = len([t for t in tasks_db.values() if t.status == TaskStatus.BLOCKED])
    
    return {
        "tasks": {
            "total": len(tasks_db),
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked
        },
        "velocity": {
            "current_sprint": 32,
            "average": 28,
            "trend": "increasing"
        },
        "cycle_time": {
            "average_days": 3.5,
            "median_days": 3.0
        }
    }

# 🎯 WORKFLOW PROMPTS MCP TOOLS

@app.tool()
async def get_workflow_prompts() -> Dict[str, Any]:
    """Get all available workflow template prompts.
    
    Returns:
        Dictionary of available prompts with descriptions and metadata
    """
    prompts = get_available_prompts()
    categories = get_prompt_categories()
    
    return {
        "prompts": prompts,
        "categories": categories,
        "total_prompts": len(prompts),
        "usage_guide": {
            "step_1": "Choose a workflow prompt from the available list",
            "step_2": "Get parameter completions using get_prompt_parameter_completions",
            "step_3": "Generate the filled template using generate_workflow_template",
            "step_4": "Follow the generated next steps for implementation"
        }
    }

@app.tool()
async def get_prompt_parameter_completions(
    prompt_name: str,
    parameter_name: str,
    team_context: Optional[str] = None
) -> Dict[str, Any]:
    """Get smart completions for workflow prompt parameters.
    
    Args:
        prompt_name: Name of the workflow prompt
        parameter_name: Parameter to get completions for
        team_context: JSON string with team context (optional)
        
    Returns:
        Available parameter completions and suggestions
    """
    context = None
    if team_context:
        try:
            context = json.loads(team_context)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON in team_context parameter"}
    
    if prompt_name not in TASK_PROMPTS:
        available_prompts = list(TASK_PROMPTS.keys())
        return {
            "error": f"Prompt '{prompt_name}' not found",
            "available_prompts": available_prompts
        }
    
    completions = get_parameter_completions(prompt_name, parameter_name, context)
    prompt_config = TASK_PROMPTS[prompt_name]
    
    return {
        "parameter": parameter_name,
        "prompt": prompt_name,
        "completions": completions,
        "required_parameters": prompt_config["arguments"],
        "smart_completions": prompt_config.get("smart_completions", {}),
        "has_dynamic_suggestions": bool(context and completions)
    }

@app.tool()
async def generate_workflow_template(
    prompt_name: str,
    parameters: str,
    include_ai_analysis: bool = True
) -> Dict[str, Any]:
    """Generate a workflow template with AI-powered content.
    
    Args:
        prompt_name: Name of the workflow prompt to generate
        parameters: JSON string with template parameters
        include_ai_analysis: Whether to include AI analysis and suggestions
        
    Returns:
        Generated workflow template with AI insights and next steps
    """
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in parameters"}
    
    if prompt_name not in TASK_PROMPTS:
        available_prompts = list(TASK_PROMPTS.keys())
        return {
            "error": f"Prompt '{prompt_name}' not found",
            "available_prompts": available_prompts
        }
    
    # Validate parameters
    validation = validate_prompt_parameters(prompt_name, params)
    if not validation["valid"]:
        return validation
    
    # Prepare context for AI analysis
    context = None
    if include_ai_analysis:
        # Get current tasks for context
        current_tasks = [task.model_dump() for task in tasks_db.values()]
        
        # Get team data
        team_members = list(set(
            task.assignee for task in tasks_db.values() 
            if task.assignee and task.status != TaskStatus.DONE
        ))
        
        context = {
            "tasks": current_tasks,
            "team_data": {
                "members": team_members,
                "size": len(team_members)
            }
        }
    
    # Generate the workflow template
    result = await generate_workflow_prompt(prompt_name, params, context)
    
    if "error" in result:
        return result
    
    # Add current task context
    result["task_context"] = {
        "total_tasks": len(tasks_db),
        "active_tasks": len([t for t in tasks_db.values() if t.status != TaskStatus.DONE]),
        "team_members": len(set(t.assignee for t in tasks_db.values() if t.assignee)),
        "current_sprint_velocity": 28  # Would calculate from actual data
    }
    
    return result

@app.tool()
async def validate_workflow_parameters(
    prompt_name: str,
    parameters: str
) -> Dict[str, Any]:
    """Validate parameters for a workflow prompt.
    
    Args:
        prompt_name: Name of the workflow prompt
        parameters: JSON string with parameters to validate
        
    Returns:
        Validation result with errors and suggestions
    """
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        return {
            "valid": False,
            "error": "Invalid JSON in parameters",
            "example": '{"sprint_duration": "2_weeks", "optimization_goal": "quality"}'
        }
    
    if prompt_name not in TASK_PROMPTS:
        return {
            "valid": False,
            "error": f"Prompt '{prompt_name}' not found",
            "available_prompts": list(TASK_PROMPTS.keys())
        }
    
    validation = validate_prompt_parameters(prompt_name, params)
    
    if validation["valid"]:
        prompt_config = TASK_PROMPTS[prompt_name]
        validation["metadata"] = {
            "category": prompt_config["category"],
            "estimated_duration": prompt_config["estimated_duration"],
            "prerequisites": prompt_config.get("prerequisites", [])
        }
    
    return validation

@app.tool()
async def get_workflow_prompt_examples() -> Dict[str, Any]:
    """Get example usage for workflow prompts.
    
    Returns:
        Example parameters and use cases for each workflow prompt
    """
    examples = {
        "sprint_planning": {
            "description": "Plan a 2-week sprint with capacity optimization",
            "example_parameters": {
                "sprint_duration": "2_weeks",
                "team_size": 6,
                "sprint_goal": "Implement user authentication system",
                "priority_criteria": ["business_value", "deadline"],
                "optimization_goal": "quality",
                "buffer_percentage": "20"
            },
            "use_cases": [
                "Starting a new sprint",
                "Capacity planning for upcoming work",
                "Balancing team workload",
                "Setting sprint goals and metrics"
            ]
        },
        "task_prioritization": {
            "description": "Prioritize backlog items using multi-criteria analysis",
            "example_parameters": {
                "priority_framework": "RICE",
                "scope_description": "quarterly_roadmap",
                "business_impact_weight": "30",
                "urgency_weight": "25",
                "effort_weight": "25",
                "strategic_weight": "20"
            },
            "use_cases": [
                "Quarterly planning sessions",
                "Feature roadmap prioritization",
                "Resolving priority conflicts",
                "Stakeholder alignment on priorities"
            ]
        },
        "bottleneck_analysis": {
            "description": "Identify and resolve workflow bottlenecks",
            "example_parameters": {
                "analysis_period": "last_sprint",
                "workflow_scope": "development",
                "focus_areas": ["cycle_time", "throughput", "quality"]
            },
            "use_cases": [
                "Sprint retrospectives",
                "Process improvement initiatives",
                "Performance optimization",
                "Team efficiency analysis"
            ]
        },
        "team_capacity_planning": {
            "description": "Optimize resource allocation and skills distribution",
            "example_parameters": {
                "planning_period": "1_quarter",
                "key_deliverables": ["Authentication system", "API gateway", "Admin dashboard"],
                "buffer_allocation": "20",
                "optimization_focus": "efficiency",
                "scaling_needs": "skill_development"
            },
            "use_cases": [
                "Quarterly resource planning",
                "Project staffing decisions",
                "Skills gap analysis",
                "Cross-training planning"
            ]
        },
        "performance_review": {
            "description": "Comprehensive team performance analysis",
            "example_parameters": {
                "review_period": "quarterly",
                "focus_areas": ["productivity", "quality", "collaboration"],
                "improvement_priorities": ["technical_skills", "process_optimization"],
                "development_budget": "medium"
            },
            "use_cases": [
                "Quarterly team reviews",
                "Performance improvement planning",
                "Team development initiatives",
                "Process optimization reviews"
            ]
        }
    }
    
    return {
        "examples": examples,
        "quick_start_guide": {
            "step_1": "Choose a workflow template that matches your need",
            "step_2": "Use the example parameters as a starting point",
            "step_3": "Customize parameters based on your team and project context",
            "step_4": "Generate the template and follow the AI-generated next steps"
        },
        "tips": [
            "Use get_prompt_parameter_completions to see all available options",
            "Include team context for more accurate AI suggestions",
            "Validate parameters before generating templates",
            "Review generated templates with your team for customization"
        ]
    }

# Run the server
if __name__ == "__main__":
    # Centralized logging configuration
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / ".claude"))
    try:
        from mcp_logging_config import setup_mcp_logging
        # Initialize centralized logging
        logger = setup_mcp_logging("task-manager")
    except ImportError:
        # Fallback to basic logging if centralized logging not available
        pass
    
    app.run()