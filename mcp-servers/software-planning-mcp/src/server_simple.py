#!/usr/bin/env python3
"""Simplified Software Planning MCP Server for project planning and task breakdown."""
import asyncio
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("software-planning")

# In-memory storage for projects and tasks
projects = {}
tasks = {}

@mcp.tool()
async def create_project(
    name: str,
    description: str,
    project_type: str = "general",
    complexity: int = 5
) -> Dict[str, Any]:
    """
    Create a new software project with cascading task breakdown.
    
    Args:
        name: Project name
        description: Project description
        project_type: Type of project (web, mobile, backend, ml, data, general)
        complexity: Complexity score 1-10
    
    Returns:
        Project details with generated ID and initial structure
    """
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.lower().replace(' ', '_')}"
    
    project = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": project_type,
        "complexity": complexity,
        "status": "planning",
        "created_at": datetime.now().isoformat(),
        "phases": [],
        "tasks": [],
        "agents": []
    }
    
    # Generate project phases based on type
    if project_type == "web":
        project["phases"] = ["requirements", "design", "frontend", "backend", "integration", "testing", "deployment"]
    elif project_type == "mobile":
        project["phases"] = ["requirements", "ui_design", "app_development", "api_integration", "testing", "store_submission"]
    elif project_type == "ml":
        project["phases"] = ["data_collection", "eda", "feature_engineering", "model_development", "evaluation", "deployment"]
    else:
        project["phases"] = ["planning", "development", "testing", "deployment"]
    
    projects[project_id] = project
    return project

@mcp.tool()
async def breakdown_project(
    project_id: str,
    detail_level: str = "medium"
) -> Dict[str, Any]:
    """
    Break down a project into cascading tasks using agent orchestration patterns.
    
    Args:
        project_id: ID of the project to break down
        detail_level: Level of detail (high, medium, low)
    
    Returns:
        Hierarchical task breakdown with agent assignments
    """
    if project_id not in projects:
        return {"error": "Project not found"}
    
    project = projects[project_id]
    breakdown = {
        "project_id": project_id,
        "project_name": project["name"],
        "cascade_levels": []
    }
    
    # Level 0: Orchestrator tasks
    level0_tasks = []
    for phase in project["phases"]:
        task = {
            "id": f"{project_id}_L0_{phase}",
            "name": f"Orchestrate {phase} phase",
            "level": 0,
            "phase": phase,
            "type": "orchestration",
            "estimated_hours": 2,
            "agents": ["Orchestrator"],
            "subtasks": []
        }
        level0_tasks.append(task)
    
    breakdown["cascade_levels"].append({
        "level": 0,
        "description": "Orchestrator level - Strategic decisions and team management",
        "tasks": level0_tasks
    })
    
    # Level 1: Lead Agent tasks
    level1_tasks = []
    for phase_task in level0_tasks:
        phase = phase_task["phase"]
        if phase in ["requirements", "planning"]:
            subtasks = [
                {"name": "Gather requirements", "agent": "Business Analyst"},
                {"name": "Define success metrics", "agent": "Product Strategist"},
                {"name": "Create roadmap", "agent": "Project Manager"}
            ]
        elif phase in ["design", "ui_design"]:
            subtasks = [
                {"name": "Create wireframes", "agent": "UX Designer"},
                {"name": "Design system architecture", "agent": "System Architect"},
                {"name": "Define API contracts", "agent": "API Architect"}
            ]
        elif phase in ["development", "frontend", "backend", "app_development"]:
            subtasks = [
                {"name": "Implement core features", "agent": "Senior Developer"},
                {"name": "Setup infrastructure", "agent": "DevOps Engineer"},
                {"name": "Integrate services", "agent": "Integration Specialist"}
            ]
        elif phase == "testing":
            subtasks = [
                {"name": "Create test strategy", "agent": "QA Lead"},
                {"name": "Perform security audit", "agent": "Security Analyst"},
                {"name": "Conduct performance testing", "agent": "Performance Engineer"}
            ]
        else:
            subtasks = [
                {"name": f"Execute {phase}", "agent": f"{phase.title()} Specialist"}
            ]
        
        for subtask in subtasks:
            task = {
                "id": f"{project_id}_L1_{phase}_{subtask['name'].replace(' ', '_')}",
                "name": subtask["name"],
                "level": 1,
                "phase": phase,
                "parent_task": phase_task["id"],
                "agent": subtask["agent"],
                "estimated_hours": 8
            }
            level1_tasks.append(task)
            phase_task["subtasks"].append(task["id"])
    
    breakdown["cascade_levels"].append({
        "level": 1,
        "description": "Lead Agents - Department heads managing specialized teams",
        "tasks": level1_tasks
    })
    
    # Store the breakdown
    project["breakdown"] = breakdown
    projects[project_id] = project
    
    return breakdown

@mcp.tool()
async def create_task(
    project_id: str,
    name: str,
    description: str,
    assigned_agents: List[str],
    priority: str = "medium",
    estimated_hours: float = 4.0
) -> Dict[str, Any]:
    """
    Create a specific task within a project.
    
    Args:
        project_id: ID of the parent project
        name: Task name
        description: Task description
        assigned_agents: List of AI agents to assign
        priority: Task priority (low, medium, high, critical)
        estimated_hours: Estimated hours to complete
    
    Returns:
        Created task details
    """
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(tasks)}"
    
    task = {
        "id": task_id,
        "project_id": project_id,
        "name": name,
        "description": description,
        "assigned_agents": assigned_agents,
        "priority": priority,
        "estimated_hours": estimated_hours,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "parallel_approaches": []
    }
    
    tasks[task_id] = task
    
    # Add task to project
    if project_id in projects:
        projects[project_id]["tasks"].append(task_id)
    
    return task

@mcp.tool()
async def define_approaches(
    task_id: str,
    approaches: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Define parallel approaches for a task (for concurrent execution).
    
    Args:
        task_id: ID of the task
        approaches: List of approach definitions with name and description
    
    Returns:
        Updated task with parallel approaches
    """
    if task_id not in tasks:
        return {"error": "Task not found"}
    
    task = tasks[task_id]
    task["parallel_approaches"] = approaches
    task["execution_pattern"] = "parallel"
    
    return task

@mcp.tool()
async def list_projects(
    status: Optional[str] = None,
    project_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all projects with optional filtering.
    
    Args:
        status: Filter by status (planning, active, completed)
        project_type: Filter by project type
    
    Returns:
        List of projects matching criteria
    """
    result = []
    for project in projects.values():
        if status and project.get("status") != status:
            continue
        if project_type and project.get("type") != project_type:
            continue
        result.append(project)
    
    return result

@mcp.tool()
async def get_status(
    project_id: str
) -> Dict[str, Any]:
    """
    Get detailed status of a project including all tasks and agents.
    
    Args:
        project_id: ID of the project
    
    Returns:
        Comprehensive project status
    """
    if project_id not in projects:
        return {"error": "Project not found"}
    
    project = projects[project_id]
    project_tasks = [tasks[tid] for tid in project.get("tasks", []) if tid in tasks]
    
    # Calculate summary statistics
    total_tasks = len(project_tasks)
    completed_tasks = sum(1 for t in project_tasks if t.get("status") == "completed")
    total_hours = sum(t.get("estimated_hours", 0) for t in project_tasks)
    
    status = {
        "project": project,
        "tasks": project_tasks,
        "statistics": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "total_estimated_hours": total_hours,
            "unique_agents": list(set(
                agent for t in project_tasks 
                for agent in t.get("assigned_agents", [])
            ))
        }
    }
    
    return status

@mcp.tool()
async def suggest_team(
    project_type: str,
    complexity: int,
    specific_requirements: List[str] = []
) -> Dict[str, Any]:
    """
    Suggest an AI agent team composition for a project.
    
    Args:
        project_type: Type of project
        complexity: Complexity score 1-10
        specific_requirements: List of specific requirements or technologies
    
    Returns:
        Recommended agent team composition
    """
    base_team = {
        "orchestrator": ["Cascading Agent Orchestrator"],
        "lead_agents": [],
        "specialists": [],
        "support": []
    }
    
    # Add lead agents based on project type
    if project_type == "web":
        base_team["lead_agents"].extend([
            "Agency Consultant",
            "Fractional CTO",
            "Agency Visual Architect"
        ])
        base_team["specialists"].extend([
            "React Developer",
            "Backend API Specialist",
            "Database Architect",
            "UX Designer"
        ])
    elif project_type == "mobile":
        base_team["lead_agents"].extend([
            "Mobile App Architect",
            "Agency Visual Architect",
            "User Experience Lead"
        ])
        base_team["specialists"].extend([
            "iOS Developer",
            "Android Developer",
            "Mobile Backend Developer",
            "App Store Optimization Expert"
        ])
    elif project_type == "ml":
        base_team["lead_agents"].extend([
            "ML Model Architect",
            "Data Science Lead",
            "AI Research Coordinator"
        ])
        base_team["specialists"].extend([
            "Data Engineer",
            "ML Engineer",
            "Data Analyst",
            "Model Deployment Specialist"
        ])
    
    # Add more specialists based on complexity
    if complexity >= 7:
        base_team["specialists"].extend([
            "Performance Engineer",
            "Security Analyst",
            "DevOps Specialist"
        ])
        base_team["support"].extend([
            "Technical Writer",
            "QA Engineer",
            "Project Coordinator"
        ])
    
    # Add specialists for specific requirements
    for req in specific_requirements:
        req_lower = req.lower()
        if "blockchain" in req_lower:
            base_team["specialists"].append("Blockchain Developer")
        if "ai" in req_lower or "llm" in req_lower:
            base_team["specialists"].append("AI Integration Specialist")
        if "real-time" in req_lower:
            base_team["specialists"].append("Real-time Systems Engineer")
        
    # Remove duplicates
    for key in base_team:
        base_team[key] = list(dict.fromkeys(base_team[key]))
    
    return {
        "recommended_team": base_team,
        "team_size": sum(len(agents) for agents in base_team.values()),
        "rationale": f"Team composition based on {project_type} project with complexity {complexity}"
    }

@mcp.tool()
async def gen_exec_plan(
    project_id: str,
    execution_style: str = "cascading"
) -> Dict[str, Any]:
    """
    Generate a detailed execution plan for the project.
    
    Args:
        project_id: ID of the project
        execution_style: Style of execution (cascading, parallel, hybrid)
    
    Returns:
        Detailed execution plan with timelines and dependencies
    """
    if project_id not in projects:
        return {"error": "Project not found"}
    
    project = projects[project_id]
    breakdown = project.get("breakdown", {})
    
    plan = {
        "project_id": project_id,
        "project_name": project["name"],
        "execution_style": execution_style,
        "phases": []
    }
    
    # Generate phase-based execution plan
    for i, phase in enumerate(project.get("phases", [])):
        phase_plan = {
            "phase": phase,
            "order": i + 1,
            "dependencies": [project["phases"][i-1]] if i > 0 else [],
            "parallel_tracks": [],
            "estimated_days": 5 * (i + 1)  # Simple estimation
        }
        
        # Add parallel tracks within each phase
        if execution_style in ["cascading", "hybrid"]:
            phase_plan["parallel_tracks"] = [
                {"track": "Conservative", "description": f"Proven approach for {phase}"},
                {"track": "Modern", "description": f"Current best practices for {phase}"},
                {"track": "Experimental", "description": f"Cutting-edge approach for {phase}"}
            ]
        
        plan["phases"].append(phase_plan)
    
    # Calculate total timeline
    total_days = sum(p["estimated_days"] for p in plan["phases"])
    if execution_style == "parallel":
        total_days = max(p["estimated_days"] for p in plan["phases"])
    
    plan["total_estimated_days"] = total_days
    plan["recommended_start_date"] = datetime.now().isoformat()
    
    return plan

# Run the server
if __name__ == "__main__":
    mcp.run()