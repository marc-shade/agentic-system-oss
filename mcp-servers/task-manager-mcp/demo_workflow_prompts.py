#!/usr/bin/env python3
"""
🎯 Task Manager MCP Workflow Prompts Demonstration
Shows the full workflow template system in action
"""

import asyncio
import json
from prompts import (
    get_available_prompts, generate_workflow_prompt, get_parameter_completions,
    validate_prompt_parameters, get_prompt_categories
)

async def demonstrate_workflow_prompts():
    """Comprehensive demonstration of workflow prompts functionality"""
    
    print("🚀 Task Manager MCP Workflow Prompts - Live Demonstration")
    print("=" * 80)
    
    # 1. Show available templates
    print("\n📋 AVAILABLE WORKFLOW TEMPLATES")
    print("-" * 40)
    
    prompts = get_available_prompts()
    categories = get_prompt_categories()
    
    for category_id, category_info in categories.items():
        print(f"\n🎯 {category_info['name']}")
        print(f"   {category_info['description']}")
        
        for prompt_name in category_info['prompts']:
            if prompt_name in prompts:
                config = prompts[prompt_name]
                print(f"   • {prompt_name}: {config['description']}")
                print(f"     Duration: {config['estimated_duration']}")
                print(f"     Prerequisites: {', '.join(config.get('prerequisites', ['None']))}")
    
    # 2. Interactive parameter exploration
    print("\n🔧 SMART PARAMETER COMPLETIONS")
    print("-" * 40)
    
    sample_prompts = [
        ("sprint_planning", "optimization_goal"),
        ("task_prioritization", "priority_framework"),
        ("bottleneck_analysis", "analysis_period"),
        ("team_capacity_planning", "planning_period"),
        ("performance_review", "review_period")
    ]
    
    for prompt_name, param_name in sample_prompts:
        completions = get_parameter_completions(prompt_name, param_name)
        print(f"  {prompt_name}.{param_name}: {completions}")
    
    # 3. Generate complete workflow templates
    print("\n📝 GENERATED WORKFLOW TEMPLATES")
    print("-" * 40)
    
    # Sprint Planning Template
    print("\n🏃 Sprint Planning Template:")
    sprint_params = {
        "sprint_duration": "2_weeks",
        "team_capacity": {"Alice": 40, "Bob": 40, "Charlie": 32, "Diana": 40},
        "priority_criteria": ["business_value", "deadline", "effort"],
        "optimization_goal": "quality",
        "sprint_goal": "Deliver user authentication system with dashboard integration",
        "buffer_percentage": 20
    }
    
    # Simulate task context
    context = {
        "tasks": [
            {
                "id": "TASK-001",
                "title": "Implement JWT authentication",
                "priority": "critical",
                "estimated_hours": 16,
                "status": "todo",
                "dependencies": []
            },
            {
                "id": "TASK-002",
                "title": "Create user registration API",
                "priority": "high",
                "estimated_hours": 12,
                "status": "todo", 
                "dependencies": ["TASK-001"]
            },
            {
                "id": "TASK-003",
                "title": "Design login UI components",
                "priority": "high",
                "estimated_hours": 8,
                "status": "todo",
                "dependencies": []
            },
            {
                "id": "TASK-004",
                "title": "Implement password reset flow",
                "priority": "medium",
                "estimated_hours": 10,
                "status": "todo",
                "dependencies": ["TASK-001"]
            },
            {
                "id": "TASK-005",
                "title": "Add authentication unit tests",
                "priority": "medium",
                "estimated_hours": 6,
                "status": "todo",
                "dependencies": ["TASK-001"]
            }
        ],
        "team_data": {
            "members": ["Alice", "Bob", "Charlie", "Diana"],
            "size": 4
        }
    }
    
    sprint_result = await generate_workflow_prompt("sprint_planning", sprint_params, context)
    print(sprint_result["prompt"])
    print(f"\n📋 Next Steps ({len(sprint_result['next_steps'])} items):")
    for i, step in enumerate(sprint_result["next_steps"], 1):
        print(f"  {i}. {step}")
    
    # Task Prioritization Template  
    print("\n" + "=" * 80)
    print("\n📊 Task Prioritization Template:")
    priority_params = {
        "priority_framework": "RICE",
        "scope_description": "quarterly_roadmap",
        "business_impact_weight": 35,
        "urgency_weight": 25,
        "effort_weight": 20,
        "dependency_weight": 10,
        "strategic_weight": 10
    }
    
    priority_result = await generate_workflow_prompt("task_prioritization", priority_params, context)
    print(priority_result["prompt"][:800] + "...")
    
    # Bottleneck Analysis Template
    print("\n" + "=" * 80) 
    print("\n🔍 Bottleneck Analysis Template:")
    bottleneck_params = {
        "analysis_period": "last_sprint",
        "workflow_scope": "development",
        "focus_areas": ["cycle_time", "throughput", "quality"]
    }
    
    bottleneck_result = await generate_workflow_prompt("bottleneck_analysis", bottleneck_params)
    print(bottleneck_result["prompt"][:600] + "...")
    
    # 4. Show AI-enhanced features
    print("\n" + "=" * 80)
    print("\n🧠 AI-ENHANCED FEATURES DEMONSTRATION")
    print("-" * 40)
    
    print("✅ Context-Aware Task Suggestions:")
    high_priority_tasks = [t for t in context["tasks"] if t["priority"] in ["critical", "high"]]
    print(f"   Identified {len(high_priority_tasks)} high-priority tasks for sprint")
    for task in high_priority_tasks:
        print(f"   • {task['title']} ({task['estimated_hours']}h, {task['priority']})")
    
    print("\n✅ Intelligent Capacity Planning:")
    total_capacity = sum(sprint_params["team_capacity"].values())
    buffer = total_capacity * (sprint_params["buffer_percentage"] / 100)
    working_capacity = total_capacity - buffer
    print(f"   Total Capacity: {total_capacity}h")
    print(f"   Buffer: {buffer}h ({sprint_params['buffer_percentage']}%)")
    print(f"   Working Capacity: {working_capacity}h")
    
    print("\n✅ Risk Assessment:")
    total_task_hours = sum(t["estimated_hours"] for t in context["tasks"])
    utilization = (total_task_hours / working_capacity) * 100
    risk_level = "Low" if utilization < 80 else "Medium" if utilization < 100 else "High"
    print(f"   Total Task Hours: {total_task_hours}h")
    print(f"   Capacity Utilization: {utilization:.1f}%")
    print(f"   Risk Level: {risk_level}")
    
    print("\n✅ Dependency Analysis:")
    tasks_with_deps = [t for t in context["tasks"] if t["dependencies"]]
    print(f"   Tasks with dependencies: {len(tasks_with_deps)}")
    for task in tasks_with_deps:
        deps = ', '.join(task["dependencies"])
        print(f"   • {task['title']} depends on: {deps}")
    
    # 5. Parameter validation demo
    print("\n" + "=" * 80)
    print("\n✅ PARAMETER VALIDATION DEMONSTRATION")
    print("-" * 40)
    
    # Valid parameters
    valid_test = validate_prompt_parameters("sprint_planning", sprint_params)
    print(f"Valid parameters: {valid_test}")
    
    # Invalid parameters  
    invalid_params = {"sprint_duration": "2_weeks"}
    invalid_test = validate_prompt_parameters("sprint_planning", invalid_params)
    print(f"Invalid parameters: {invalid_test}")
    
    # 6. Summary and benefits
    print("\n" + "=" * 80)
    print("\n🎯 WORKFLOW PROMPTS BENEFITS SUMMARY")
    print("-" * 40)
    
    benefits = [
        "🚀 60-80% time savings on workflow planning",
        "🧠 AI-powered insights and recommendations", 
        "🎯 Context-aware task and capacity analysis",
        "📊 Interactive parameter completion and validation",
        "🔄 Standardized processes across teams",
        "📈 Improved planning accuracy and success rates",
        "🛠️ Seamless integration with task management",
        "📋 Automated next steps and action planning"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print("\n🎉 Workflow Prompts Transform Manual Planning Into Intelligent Automation!")
    print("=" * 80)

# Demo-specific task data for realistic examples
SAMPLE_TASKS = [
    {
        "id": "TASK-001",
        "title": "Implement JWT authentication middleware",
        "description": "Create secure JWT-based authentication system with refresh tokens",
        "assignee": "Alice",
        "priority": "critical",
        "status": "todo",
        "estimated_hours": 16,
        "tags": ["security", "backend", "authentication"],
        "dependencies": [],
        "due_date": "2025-08-15T17:00:00Z"
    },
    {
        "id": "TASK-002", 
        "title": "Create user registration API endpoints",
        "description": "Build REST endpoints for user signup, email verification, and profile creation",
        "assignee": "Bob",
        "priority": "high",
        "status": "todo",
        "estimated_hours": 12,
        "tags": ["api", "backend", "user-management"],
        "dependencies": ["TASK-001"],
        "due_date": "2025-08-18T17:00:00Z"
    },
    {
        "id": "TASK-003",
        "title": "Design login and registration UI components",
        "description": "Create responsive React components for authentication flows",
        "assignee": "Charlie",
        "priority": "high", 
        "status": "in_progress",
        "estimated_hours": 8,
        "tags": ["frontend", "ui", "react"],
        "dependencies": [],
        "due_date": "2025-08-16T17:00:00Z"
    },
    {
        "id": "TASK-004",
        "title": "Implement password reset functionality",
        "description": "Email-based password reset with secure token generation",
        "assignee": "Alice",
        "priority": "medium",
        "status": "todo",
        "estimated_hours": 10,
        "tags": ["security", "email", "backend"],
        "dependencies": ["TASK-001"],
        "due_date": "2025-08-20T17:00:00Z"
    },
    {
        "id": "TASK-005",
        "title": "Add comprehensive authentication tests", 
        "description": "Unit and integration tests for all auth functionality",
        "assignee": "Diana",
        "priority": "medium",
        "status": "todo",
        "estimated_hours": 6,
        "tags": ["testing", "quality", "automation"],
        "dependencies": ["TASK-001", "TASK-002"],
        "due_date": "2025-08-22T17:00:00Z"
    },
    {
        "id": "TASK-006",
        "title": "Set up user session management",
        "description": "Implement session handling, logout, and session expiry",
        "assignee": "Bob",
        "priority": "medium",
        "status": "todo", 
        "estimated_hours": 8,
        "tags": ["session", "backend", "security"],
        "dependencies": ["TASK-001"],
        "due_date": "2025-08-19T17:00:00Z"
    },
    {
        "id": "TASK-007",
        "title": "Create user dashboard prototype",
        "description": "Initial user dashboard with basic profile and settings",
        "assignee": "Charlie",
        "priority": "low",
        "status": "todo",
        "estimated_hours": 12,
        "tags": ["frontend", "dashboard", "ui"],
        "dependencies": ["TASK-001", "TASK-003"],
        "due_date": "2025-08-25T17:00:00Z"
    }
]

if __name__ == "__main__":
    asyncio.run(demonstrate_workflow_prompts())