#!/usr/bin/env python3
"""
Task Manager MCP Prompts - AI-powered workflow templates
Enables template-driven task management with interactive completion
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

# 🎯 WORKFLOW TEMPLATES WITH AI INTEGRATION
TASK_PROMPTS = {
    "sprint_planning": {
        "description": "AI-guided sprint planning with capacity optimization",
        "category": "planning",
        "estimated_duration": "60-90 minutes",
        "prerequisites": ["team_availability", "backlog_refinement"],
        "template": """Sprint Planning Session for {sprint_duration}

🎯 Sprint Overview:
• Duration: {sprint_duration}
• Team Size: {team_size} members
• Sprint Goal: {sprint_goal}
• Capacity: {total_capacity} hours

👥 Team Capacity Breakdown:
{team_capacity_breakdown}

📊 Priority Framework: {priority_criteria}
🎯 Optimization Goal: {optimization_goal}

🚀 AI-Suggested Sprint Backlog:
{ai_suggested_tasks}

📈 Capacity Analysis:
• Available Story Points: {available_points}
• Recommended Allocation: {capacity_recommendation}
• Buffer Percentage: {buffer_percentage}%
• Risk Factors: {identified_risks}

🎯 Sprint Goals & Objectives:
{sprint_objectives}

📊 Success Metrics:
• Completion Rate Target: {completion_target}%
• Quality Gates: {quality_criteria}
• Definition of Done: {definition_of_done}

⚠️ Risk Mitigation:
{risk_mitigation_plan}

🔄 Retrospective Focus Areas:
{retrospective_areas}""",
        "arguments": [
            "sprint_duration", "team_capacity", "priority_criteria", 
            "optimization_goal", "sprint_goal", "buffer_percentage"
        ],
        "smart_completions": {
            "sprint_duration": ["1_week", "2_weeks", "3_weeks", "1_month"],
            "priority_criteria": ["deadline", "impact", "effort", "dependencies", "business_value"],
            "optimization_goal": ["speed", "quality", "resource_efficiency", "innovation", "risk_mitigation"],
            "buffer_percentage": ["10", "15", "20", "25", "30"]
        }
    },
    
    "task_prioritization": {
        "description": "Intelligent task prioritization with multi-criteria analysis",
        "category": "optimization",
        "estimated_duration": "30-45 minutes",
        "prerequisites": ["task_backlog", "business_context"],
        "template": """Task Prioritization Analysis - {analysis_date}

🎯 Prioritization Framework: {priority_framework}
📊 Analysis Scope: {scope_description}

🧠 AI-Powered Priority Matrix:
{priority_matrix}

📈 Scoring Methodology:
• Business Impact: {business_impact_weight}%
• Urgency/Deadline: {urgency_weight}%
• Effort/Complexity: {effort_weight}%
• Dependencies: {dependency_weight}%
• Strategic Alignment: {strategic_weight}%

🚀 Top Priority Tasks (Recommended Order):
{prioritized_task_list}

⚡ Quick Wins (High Impact, Low Effort):
{quick_wins}

🎯 Strategic Initiatives (High Impact, High Effort):
{strategic_initiatives}

⚠️ Dependency Analysis:
{dependency_analysis}

🔄 Resource Allocation Recommendations:
{resource_recommendations}

📊 Impact vs Effort Visualization:
{impact_effort_matrix}

🎯 Next Actions:
{recommended_next_actions}""",
        "arguments": [
            "priority_framework", "scope_description", "business_impact_weight",
            "urgency_weight", "effort_weight", "dependency_weight", "strategic_weight"
        ],
        "smart_completions": {
            "priority_framework": ["MoSCoW", "RICE", "Kano", "Value_vs_Effort", "Weighted_Scoring"],
            "scope_description": ["current_sprint", "quarterly_roadmap", "annual_planning", "feature_release"],
            "business_impact_weight": ["20", "25", "30", "35", "40"],
            "urgency_weight": ["15", "20", "25", "30"],
            "effort_weight": ["20", "25", "30"],
            "dependency_weight": ["10", "15", "20"],
            "strategic_weight": ["15", "20", "25"]
        }
    },
    
    "bottleneck_analysis": {
        "description": "Comprehensive workflow bottleneck identification and resolution",
        "category": "optimization",
        "estimated_duration": "45-60 minutes",
        "prerequisites": ["workflow_data", "team_performance_metrics"],
        "template": """Workflow Bottleneck Analysis - {analysis_date}

🔍 Analysis Period: {analysis_period}
📊 Workflow Scope: {workflow_scope}

🚨 Identified Bottlenecks:
{identified_bottlenecks}

📈 Performance Impact Analysis:
• Cycle Time Impact: {cycle_time_impact}
• Throughput Reduction: {throughput_impact}
• Team Utilization: {utilization_impact}
• Quality Impact: {quality_impact}

🔬 Root Cause Analysis:
{root_cause_analysis}

🎯 Bottleneck Categories:
• Process Bottlenecks: {process_bottlenecks}
• Resource Bottlenecks: {resource_bottlenecks}
• Dependency Bottlenecks: {dependency_bottlenecks}
• Knowledge Bottlenecks: {knowledge_bottlenecks}

💡 AI-Recommended Solutions:
{recommended_solutions}

📊 Solution Priority Matrix:
{solution_priority_matrix}

🚀 Implementation Roadmap:
{implementation_roadmap}

📈 Expected Improvements:
• Velocity Increase: {velocity_improvement}
• Cycle Time Reduction: {cycle_time_reduction}
• Quality Enhancement: {quality_improvement}

🔄 Monitoring & Measurement:
{monitoring_plan}""",
        "arguments": [
            "analysis_period", "workflow_scope", "focus_areas"
        ],
        "smart_completions": {
            "analysis_period": ["last_week", "last_sprint", "last_month", "last_quarter"],
            "workflow_scope": ["development", "deployment", "testing", "planning", "review"],
            "focus_areas": ["cycle_time", "throughput", "quality", "team_satisfaction", "delivery_predictability"]
        }
    },
    
    "team_capacity_planning": {
        "description": "Resource allocation optimization with skills matrix analysis",
        "category": "planning",
        "estimated_duration": "90-120 minutes",
        "prerequisites": ["team_skills_matrix", "project_requirements", "timeline_constraints"],
        "template": """Team Capacity Planning - {planning_period}

👥 Team Composition Analysis:
{team_composition}

🎯 Planning Objectives:
• Time Period: {planning_period}
• Key Deliverables: {key_deliverables}
• Success Criteria: {success_criteria}

📊 Capacity Overview:
• Total Team Capacity: {total_capacity} hours
• Available Capacity: {available_capacity} hours
• Planned Utilization: {planned_utilization}%
• Buffer Allocation: {buffer_allocation}%

🧠 Skills Matrix & Allocation:
{skills_matrix_analysis}

🚀 Project Allocation Recommendations:
{project_allocations}

⚡ Cross-Training Opportunities:
{cross_training_plan}

📈 Workload Distribution:
{workload_distribution}

⚠️ Capacity Risks & Mitigation:
{capacity_risks}

🔄 Flexibility & Scaling Options:
{scaling_options}

📊 Resource Utilization Forecast:
{utilization_forecast}

🎯 Optimization Recommendations:
{optimization_recommendations}

📅 Review & Adjustment Schedule:
{review_schedule}""",
        "arguments": [
            "planning_period", "key_deliverables", "buffer_allocation",
            "optimization_focus", "scaling_needs"
        ],
        "smart_completions": {
            "planning_period": ["1_month", "1_quarter", "6_months", "1_year"],
            "buffer_allocation": ["10", "15", "20", "25"],
            "optimization_focus": ["efficiency", "quality", "innovation", "risk_reduction", "skill_development"],
            "scaling_needs": ["none", "temporary_contractors", "new_hires", "skill_development", "process_automation"]
        }
    },
    
    "performance_review": {
        "description": "Comprehensive team performance analysis with improvement recommendations",
        "category": "analysis",
        "estimated_duration": "60-75 minutes",
        "prerequisites": ["performance_metrics", "team_feedback", "project_outcomes"],
        "template": """Team Performance Review - {review_period}

📊 Performance Overview:
• Review Period: {review_period}
• Team Size: {team_size}
• Projects Completed: {projects_completed}
• Overall Health Score: {health_score}/100

📈 Key Performance Metrics:
{key_metrics}

🎯 Goal Achievement Analysis:
{goal_achievement}

🚀 Team Strengths:
{team_strengths}

⚠️ Areas for Improvement:
{improvement_areas}

👥 Individual Performance Highlights:
{individual_highlights}

📊 Process Effectiveness:
{process_effectiveness}

🔄 Retrospective Insights:
{retrospective_insights}

💡 AI-Generated Recommendations:
{ai_recommendations}

🎯 Action Plan for Next Period:
{action_plan}

📅 Development & Training Plan:
{development_plan}

🏆 Recognition & Rewards:
{recognition_plan}

📊 Success Metrics for Next Review:
{next_period_metrics}""",
        "arguments": [
            "review_period", "focus_areas", "improvement_priorities",
            "development_budget", "recognition_budget"
        ],
        "smart_completions": {
            "review_period": ["monthly", "quarterly", "semi_annual", "annual"],
            "focus_areas": ["productivity", "quality", "collaboration", "innovation", "satisfaction"],
            "improvement_priorities": ["technical_skills", "soft_skills", "process_optimization", "tool_adoption"],
            "development_budget": ["low", "medium", "high", "unlimited"],
            "recognition_budget": ["low", "medium", "high", "performance_based"]
        }
    }
}

# 🎯 INTERACTIVE PARAMETER SYSTEM
class PromptParameterEngine:
    """Handles interactive parameter completion and validation"""
    
    def __init__(self):
        self.parameter_suggestions = {
            "team_roles": ["frontend", "backend", "fullstack", "qa", "devops", "design", "pm", "architect"],
            "priority_levels": ["critical", "high", "medium", "low"],
            "complexity_levels": ["simple", "moderate", "complex", "very_complex"],
            "risk_levels": ["low", "medium", "high", "critical"],
            "confidence_levels": ["low", "medium", "high", "very_high"],
            "effort_estimates": ["1_hour", "half_day", "1_day", "2_days", "1_week", "2_weeks", "1_month"],
            "business_impact": ["low", "medium", "high", "critical"],
            "urgency": ["not_urgent", "somewhat_urgent", "urgent", "critical"],
            "dependencies": ["none", "few", "moderate", "many", "complex_web"]
        }
    
    def get_parameter_suggestions(self, parameter_name: str) -> List[str]:
        """Get smart suggestions for a parameter"""
        return self.parameter_suggestions.get(parameter_name, [])
    
    def validate_parameter(self, parameter_name: str, value: str) -> bool:
        """Validate parameter value"""
        suggestions = self.get_parameter_suggestions(parameter_name)
        if suggestions:
            return value in suggestions
        return True  # Allow any value if no specific suggestions
    
    def generate_dynamic_parameters(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate dynamic parameter suggestions based on context"""
        dynamic_params = {}
        
        # Team-based suggestions
        if context.get("team_members"):
            dynamic_params["assignee"] = context["team_members"]
        
        # Project-based suggestions
        if context.get("project_tags"):
            dynamic_params["tags"] = context["project_tags"]
        
        # Historical data-based suggestions
        if context.get("past_sprints"):
            sprint_durations = [sprint.get("duration") for sprint in context["past_sprints"]]
            dynamic_params["sprint_duration"] = list(set(sprint_durations))
        
        return dynamic_params

# 🧠 AI INTEGRATION ENGINE
class PromptAIEngine:
    """Handles AI-powered template completion and suggestions"""
    
    async def analyze_task_context(self, tasks: List[Dict], team_data: Dict) -> Dict[str, Any]:
        """Analyze task context for intelligent suggestions"""
        analysis = {
            "task_complexity_distribution": self._analyze_complexity(tasks),
            "team_workload_balance": self._analyze_workload(tasks, team_data),
            "priority_patterns": self._analyze_priorities(tasks),
            "dependency_network": self._analyze_dependencies(tasks),
            "velocity_trends": self._analyze_velocity(tasks),
            "bottleneck_indicators": self._identify_bottlenecks(tasks, team_data)
        }
        return analysis
    
    async def generate_sprint_suggestions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered sprint planning suggestions"""
        return {
            "recommended_capacity": self._calculate_optimal_capacity(context),
            "task_recommendations": self._suggest_sprint_tasks(context),
            "risk_assessment": self._assess_sprint_risks(context),
            "success_probability": self._calculate_success_probability(context),
            "optimization_tips": self._generate_optimization_tips(context)
        }
    
    async def generate_priority_matrix(self, tasks: List[Dict], criteria: Dict) -> Dict[str, Any]:
        """Generate intelligent priority matrix"""
        return {
            "high_impact_low_effort": self._filter_quick_wins(tasks),
            "high_impact_high_effort": self._filter_strategic_initiatives(tasks),
            "low_impact_low_effort": self._filter_filler_tasks(tasks),
            "low_impact_high_effort": self._filter_questionable_tasks(tasks),
            "priority_scores": self._calculate_priority_scores(tasks, criteria)
        }
    
    def _analyze_complexity(self, tasks: List[Dict]) -> Dict[str, int]:
        """Analyze task complexity distribution"""
        complexity_counts = {"simple": 0, "moderate": 0, "complex": 0, "very_complex": 0}
        for task in tasks:
            # Simple heuristics for complexity
            description_length = len(task.get("description", ""))
            dependencies_count = len(task.get("dependencies", []))
            
            if description_length < 50 and dependencies_count == 0:
                complexity_counts["simple"] += 1
            elif description_length < 200 and dependencies_count <= 2:
                complexity_counts["moderate"] += 1
            elif description_length < 500 and dependencies_count <= 5:
                complexity_counts["complex"] += 1
            else:
                complexity_counts["very_complex"] += 1
        
        return complexity_counts
    
    def _analyze_workload(self, tasks: List[Dict], team_data: Dict) -> Dict[str, float]:
        """Analyze team workload balance"""
        workload = {}
        team_members = team_data.get("members", [])
        
        for member in team_members:
            member_tasks = [t for t in tasks if t.get("assignee") == member]
            total_hours = sum(t.get("estimated_hours", 8) for t in member_tasks)
            workload[member] = total_hours
        
        return workload
    
    def _analyze_priorities(self, tasks: List[Dict]) -> Dict[str, int]:
        """Analyze priority distribution"""
        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for task in tasks:
            priority = task.get("priority", "medium")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return priority_counts
    
    def _analyze_dependencies(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Analyze task dependency network"""
        dependency_counts = [len(task.get("dependencies", [])) for task in tasks]
        return {
            "total_dependencies": sum(dependency_counts),
            "max_dependencies": max(dependency_counts) if dependency_counts else 0,
            "avg_dependencies": sum(dependency_counts) / len(dependency_counts) if dependency_counts else 0,
            "tasks_with_dependencies": len([d for d in dependency_counts if d > 0])
        }
    
    def _analyze_velocity(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Analyze team velocity trends"""
        completed_tasks = [t for t in tasks if t.get("status") == "done"]
        return {
            "completed_count": len(completed_tasks),
            "avg_completion_time": "3.5 days",  # Would calculate from actual data
            "velocity_trend": "stable",  # Would analyze historical data
            "completion_rate": len(completed_tasks) / len(tasks) if tasks else 0
        }
    
    def _identify_bottlenecks(self, tasks: List[Dict], team_data: Dict) -> List[str]:
        """Identify potential bottlenecks"""
        bottlenecks = []
        
        # Check for blocked tasks
        blocked_tasks = [t for t in tasks if t.get("status") == "blocked"]
        if len(blocked_tasks) > 3:
            bottlenecks.append("High number of blocked tasks")
        
        # Check for overloaded team members
        workload = self._analyze_workload(tasks, team_data)
        overloaded = [member for member, hours in workload.items() if hours > 40]
        if overloaded:
            bottlenecks.append(f"Overloaded team members: {', '.join(overloaded)}")
        
        # Check for complex dependency chains
        dependency_analysis = self._analyze_dependencies(tasks)
        if dependency_analysis["max_dependencies"] > 5:
            bottlenecks.append("Complex dependency chains detected")
        
        return bottlenecks
    
    def _calculate_optimal_capacity(self, context: Dict[str, Any]) -> str:
        """Calculate optimal sprint capacity"""
        team_size = context.get("team_size", 5)
        sprint_days = context.get("sprint_duration_days", 14)
        buffer_percentage = context.get("buffer_percentage", 20)
        
        productive_hours_per_day = 6
        total_capacity = team_size * sprint_days * productive_hours_per_day
        optimal_capacity = total_capacity * (1 - buffer_percentage / 100)
        
        return f"{optimal_capacity:.0f} hours ({total_capacity:.0f} total with {buffer_percentage}% buffer)"
    
    def _suggest_sprint_tasks(self, context: Dict[str, Any]) -> List[str]:
        """Suggest tasks for sprint based on context"""
        return [
            "Focus on high-priority items with clear acceptance criteria",
            "Include a mix of feature work and technical debt",
            "Ensure tasks align with sprint goal",
            "Consider team member skills and availability",
            "Include buffer for unexpected issues"
        ]
    
    def _assess_sprint_risks(self, context: Dict[str, Any]) -> List[str]:
        """Assess potential sprint risks"""
        risks = []
        
        if context.get("team_size", 5) < 3:
            risks.append("Small team size increases delivery risk")
        
        if context.get("new_technology", False):
            risks.append("New technology adoption may slow velocity")
        
        if context.get("dependencies_external", 0) > 2:
            risks.append("Multiple external dependencies increase uncertainty")
        
        return risks if risks else ["Low risk sprint with manageable scope"]
    
    def _calculate_success_probability(self, context: Dict[str, Any]) -> str:
        """Calculate sprint success probability"""
        base_probability = 80
        
        # Adjust based on various factors
        if context.get("team_experience", "medium") == "high":
            base_probability += 10
        elif context.get("team_experience", "medium") == "low":
            base_probability -= 15
        
        if context.get("scope_clarity", "medium") == "high":
            base_probability += 5
        elif context.get("scope_clarity", "medium") == "low":
            base_probability -= 10
        
        return f"{max(0, min(100, base_probability))}%"
    
    def _generate_optimization_tips(self, context: Dict[str, Any]) -> List[str]:
        """Generate optimization tips based on context"""
        tips = [
            "Start with highest priority items",
            "Break down large tasks into smaller deliverables",
            "Maintain daily standup focus on blockers",
            "Prepare for mid-sprint adjustments",
            "Document decisions and learnings"
        ]
        
        if context.get("remote_team", False):
            tips.append("Increase communication frequency for remote coordination")
        
        if context.get("new_team_members", 0) > 0:
            tips.append("Allocate time for onboarding and knowledge transfer")
        
        return tips
    
    def _filter_quick_wins(self, tasks: List[Dict]) -> List[Dict]:
        """Filter tasks that are quick wins (high impact, low effort)"""
        return [
            task for task in tasks
            if task.get("estimated_hours", 8) <= 4 and task.get("priority") in ["high", "critical"]
        ]
    
    def _filter_strategic_initiatives(self, tasks: List[Dict]) -> List[Dict]:
        """Filter strategic initiatives (high impact, high effort)"""
        return [
            task for task in tasks
            if task.get("estimated_hours", 8) > 16 and task.get("priority") in ["high", "critical"]
        ]
    
    def _filter_filler_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Filter filler tasks (low impact, low effort)"""
        return [
            task for task in tasks
            if task.get("estimated_hours", 8) <= 4 and task.get("priority") in ["low", "medium"]
        ]
    
    def _filter_questionable_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Filter questionable tasks (low impact, high effort)"""
        return [
            task for task in tasks
            if task.get("estimated_hours", 8) > 16 and task.get("priority") in ["low", "medium"]
        ]
    
    def _calculate_priority_scores(self, tasks: List[Dict], criteria: Dict) -> Dict[str, float]:
        """Calculate priority scores for tasks"""
        scores = {}
        
        for task in tasks:
            score = 0
            
            # Priority weight
            priority_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            score += priority_scores.get(task.get("priority", "medium"), 2) * criteria.get("priority_weight", 0.3)
            
            # Urgency weight (based on due date)
            if task.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(task["due_date"])
                    days_until_due = (due_date - datetime.now()).days
                    urgency_score = max(0, 4 - (days_until_due / 7))  # Higher score for closer deadlines
                    score += urgency_score * criteria.get("urgency_weight", 0.2)
                except:
                    pass
            
            # Effort weight (inverse - less effort = higher score)
            effort_hours = task.get("estimated_hours", 8)
            effort_score = max(0, 4 - (effort_hours / 20))  # Normalize to 0-4 scale
            score += effort_score * criteria.get("effort_weight", 0.2)
            
            # Business impact (would be provided or calculated)
            impact_score = 3  # Default medium impact
            score += impact_score * criteria.get("impact_weight", 0.3)
            
            scores[task.get("id", "unknown")] = round(score, 2)
        
        return scores

# 🎯 GLOBAL INSTANCES
parameter_engine = PromptParameterEngine()
ai_engine = PromptAIEngine()

# 🚀 MAIN FUNCTIONS FOR MCP INTEGRATION
def get_available_prompts() -> Dict[str, Dict[str, Any]]:
    """Get all available workflow prompts"""
    return {
        name: {
            "description": prompt["description"],
            "category": prompt["category"],
            "estimated_duration": prompt["estimated_duration"],
            "prerequisites": prompt.get("prerequisites", []),
            "arguments": prompt["arguments"]
        }
        for name, prompt in TASK_PROMPTS.items()
    }

async def generate_workflow_prompt(
    prompt_name: str,
    parameters: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a workflow prompt with AI-enhanced content"""
    if prompt_name not in TASK_PROMPTS:
        return {"error": f"Prompt '{prompt_name}' not found"}
    
    prompt_config = TASK_PROMPTS[prompt_name]
    
    # Add AI analysis if context provided
    if context:
        ai_analysis = await ai_engine.analyze_task_context(
            context.get("tasks", []),
            context.get("team_data", {})
        )
        parameters.update(ai_analysis)
    
    # Generate AI-specific content based on prompt type
    if prompt_name == "sprint_planning":
        ai_suggestions = await ai_engine.generate_sprint_suggestions(parameters)
        parameters.update(ai_suggestions)
    elif prompt_name == "task_prioritization":
        priority_matrix = await ai_engine.generate_priority_matrix(
            context.get("tasks", []) if context else [],
            parameters
        )
        parameters.update(priority_matrix)
    
    # Add default values for missing template parameters
    parameters = _add_default_parameters(prompt_name, parameters, context)
    
    # Fill template
    try:
        filled_template = prompt_config["template"].format_map(parameters)
    except KeyError as e:
        return {"error": f"Missing required parameter: {e}"}
    
    return {
        "prompt": filled_template,
        "metadata": {
            "prompt_name": prompt_name,
            "category": prompt_config["category"],
            "estimated_duration": prompt_config["estimated_duration"],
            "generated_at": datetime.now().isoformat()
        },
        "ai_insights": parameters.get("ai_analysis", {}),
        "next_steps": _generate_next_steps(prompt_name, parameters)
    }

def get_parameter_completions(
    prompt_name: str,
    parameter_name: str,
    context: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Get smart completions for a parameter"""
    if prompt_name not in TASK_PROMPTS:
        return []
    
    prompt_config = TASK_PROMPTS[prompt_name]
    
    # Check for prompt-specific completions
    smart_completions = prompt_config.get("smart_completions", {})
    if parameter_name in smart_completions:
        return smart_completions[parameter_name]
    
    # Check for global parameter suggestions
    global_suggestions = parameter_engine.get_parameter_suggestions(parameter_name)
    if global_suggestions:
        return global_suggestions
    
    # Generate dynamic suggestions based on context
    if context:
        dynamic_params = parameter_engine.generate_dynamic_parameters(context)
        if parameter_name in dynamic_params:
            return dynamic_params[parameter_name]
    
    return []

def validate_prompt_parameters(prompt_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate prompt parameters"""
    if prompt_name not in TASK_PROMPTS:
        return {"valid": False, "error": f"Prompt '{prompt_name}' not found"}
    
    prompt_config = TASK_PROMPTS[prompt_name]
    required_args = prompt_config["arguments"]
    
    # Check required parameters
    missing_params = [arg for arg in required_args if arg not in parameters]
    if missing_params:
        return {
            "valid": False,
            "error": f"Missing required parameters: {', '.join(missing_params)}",
            "missing_parameters": missing_params
        }
    
    # Validate parameter values
    invalid_params = []
    for param_name, value in parameters.items():
        if not parameter_engine.validate_parameter(param_name, str(value)):
            invalid_params.append(param_name)
    
    if invalid_params:
        return {
            "valid": False,
            "error": f"Invalid parameter values: {', '.join(invalid_params)}",
            "invalid_parameters": invalid_params
        }
    
    return {"valid": True}

def _add_default_parameters(prompt_name: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Add default values for missing template parameters"""
    params = parameters.copy()
    
    if prompt_name == "sprint_planning":
        # Add defaults for sprint planning template
        if "team_size" not in params:
            team_size = len(context.get("team_data", {}).get("members", [])) if context else 5
            params["team_size"] = team_size
        
        if "total_capacity" not in params:
            team_size = params.get("team_size", 5)
            sprint_days = 10 if params.get("sprint_duration") == "2_weeks" else 5
            params["total_capacity"] = team_size * sprint_days * 6  # 6 productive hours/day
        
        if "team_capacity_breakdown" not in params:
            if isinstance(params.get("team_capacity"), dict):
                breakdown = []
                for member, hours in params["team_capacity"].items():
                    breakdown.append(f"{member}: {hours}h")
                params["team_capacity_breakdown"] = "\n".join(breakdown)
            else:
                params["team_capacity_breakdown"] = "Team capacity to be determined"
        
        if "ai_suggested_tasks" not in params:
            if context and context.get("tasks"):
                high_priority_tasks = [t for t in context["tasks"] if t.get("priority") in ["high", "critical"]]
                task_list = []
                for task in high_priority_tasks[:5]:  # Top 5 tasks
                    task_list.append(f"• {task.get('title', 'Untitled')} ({task.get('estimated_hours', 8)}h)")
                params["ai_suggested_tasks"] = "\n".join(task_list) if task_list else "No high-priority tasks identified"
            else:
                params["ai_suggested_tasks"] = "Tasks to be determined based on backlog analysis"
        
        if "available_points" not in params:
            params["available_points"] = params.get("total_capacity", 240) // 8  # Rough story point conversion
        
        if "capacity_recommendation" not in params:
            utilization = 80 if params.get("buffer_percentage", 20) >= 20 else 90
            params["capacity_recommendation"] = f"Plan for {utilization}% capacity utilization"
        
        if "identified_risks" not in params:
            params["identified_risks"] = "Standard sprint risks: scope creep, technical challenges, team availability"
        
        if "sprint_objectives" not in params:
            params["sprint_objectives"] = f"• Deliver on sprint goal: {params.get('sprint_goal', 'TBD')}\n• Maintain quality standards\n• Learn and improve processes"
        
        if "completion_target" not in params:
            params["completion_target"] = 85
        
        if "quality_criteria" not in params:
            params["quality_criteria"] = "Code review required, testing completed, documentation updated"
        
        if "definition_of_done" not in params:
            params["definition_of_done"] = "Implemented, tested, reviewed, documented, deployed to staging"
        
        if "risk_mitigation_plan" not in params:
            params["risk_mitigation_plan"] = "• Daily standup to identify blockers\n• Mid-sprint review for scope adjustment\n• Buffer time for unexpected issues"
        
        if "retrospective_areas" not in params:
            params["retrospective_areas"] = "Team collaboration, process efficiency, technical practices"
    
    elif prompt_name == "task_prioritization":
        if "analysis_date" not in params:
            params["analysis_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Add defaults for other missing parameters if needed
        defaults = {
            "priority_matrix": "Priority matrix will be generated based on current tasks",
            "prioritized_task_list": "Task prioritization will be calculated",
            "quick_wins": "Quick wins will be identified from task analysis",
            "strategic_initiatives": "Strategic initiatives will be identified",
            "dependency_analysis": "Dependency analysis will be performed",
            "resource_recommendations": "Resource recommendations will be generated",
            "impact_effort_matrix": "Impact vs effort matrix will be created",
            "recommended_next_actions": "Next actions will be recommended based on analysis"
        }
        
        for key, default_value in defaults.items():
            if key not in params:
                params[key] = default_value
    
    elif prompt_name == "bottleneck_analysis":
        if "analysis_date" not in params:
            params["analysis_date"] = datetime.now().strftime("%Y-%m-%d")
        
        defaults = {
            "identified_bottlenecks": "Bottleneck analysis will be performed on current workflow",
            "cycle_time_impact": "Cycle time impact will be calculated",
            "throughput_impact": "Throughput impact will be measured",
            "utilization_impact": "Team utilization impact will be assessed",
            "quality_impact": "Quality impact will be evaluated",
            "root_cause_analysis": "Root cause analysis will be conducted",
            "process_bottlenecks": "Process bottlenecks will be identified",
            "resource_bottlenecks": "Resource bottlenecks will be analyzed",
            "dependency_bottlenecks": "Dependency bottlenecks will be mapped",
            "knowledge_bottlenecks": "Knowledge bottlenecks will be assessed",
            "recommended_solutions": "Solutions will be recommended based on analysis",
            "solution_priority_matrix": "Solution priority matrix will be created",
            "implementation_roadmap": "Implementation roadmap will be developed",
            "velocity_improvement": "Velocity improvement estimates will be provided",
            "cycle_time_reduction": "Cycle time reduction targets will be set",
            "quality_improvement": "Quality improvement goals will be established",
            "monitoring_plan": "Monitoring plan will be created"
        }
        
        for key, default_value in defaults.items():
            if key not in params:
                params[key] = default_value
    
    # Add similar defaults for other prompt types as needed
    
    return params

def _generate_next_steps(prompt_name: str, parameters: Dict[str, Any]) -> List[str]:
    """Generate next steps based on prompt type"""
    next_steps = []
    
    if prompt_name == "sprint_planning":
        next_steps = [
            "Review and refine the sprint backlog with the team",
            "Confirm task assignments and capacity allocations",
            "Set up tracking for sprint metrics and goals",
            "Schedule daily standups and mid-sprint reviews",
            "Prepare contingency plans for identified risks"
        ]
    elif prompt_name == "task_prioritization":
        next_steps = [
            "Review prioritization results with stakeholders",
            "Update task assignments based on priority order",
            "Communicate priority changes to the team",
            "Schedule regular priority review sessions",
            "Monitor progress on high-priority items"
        ]
    elif prompt_name == "bottleneck_analysis":
        next_steps = [
            "Implement quick wins to address immediate bottlenecks",
            "Develop detailed implementation plans for major solutions",
            "Assign owners for each bottleneck resolution",
            "Set up monitoring for bottleneck indicators",
            "Schedule follow-up analysis in 2-4 weeks"
        ]
    elif prompt_name == "team_capacity_planning":
        next_steps = [
            "Finalize resource allocations with team leads",
            "Communicate capacity plans to stakeholders",
            "Set up regular capacity review meetings",
            "Begin cross-training initiatives",
            "Monitor actual vs planned capacity utilization"
        ]
    elif prompt_name == "performance_review":
        next_steps = [
            "Share performance insights with team members",
            "Create individual development plans",
            "Implement recommended process improvements",
            "Schedule follow-up performance check-ins",
            "Update team goals and success metrics"
        ]
    
    return next_steps

# 🎯 PROMPT CATEGORIES AND METADATA
PROMPT_CATEGORIES = {
    "planning": {
        "name": "Planning & Strategy",
        "description": "Templates for strategic planning and project preparation",
        "prompts": ["sprint_planning", "team_capacity_planning"]
    },
    "optimization": {
        "name": "Process Optimization",
        "description": "Templates for improving workflows and identifying inefficiencies",
        "prompts": ["task_prioritization", "bottleneck_analysis"]
    },
    "analysis": {
        "name": "Performance Analysis",
        "description": "Templates for analyzing team and project performance",
        "prompts": ["performance_review"]
    }
}

def get_prompt_categories() -> Dict[str, Dict[str, Any]]:
    """Get organized prompt categories"""
    return PROMPT_CATEGORIES

# 🚀 USAGE EXAMPLES FOR TESTING
if __name__ == "__main__":
    import asyncio
    
    async def test_prompts():
        # Test sprint planning prompt
        sprint_params = {
            "sprint_duration": "2_weeks",
            "team_size": 6,
            "sprint_goal": "Implement user authentication system",
            "total_capacity": 480,
            "team_capacity_breakdown": "Frontend: 2 devs (160h), Backend: 2 devs (160h), QA: 1 tester (80h), DevOps: 1 engineer (80h)",
            "priority_criteria": ["business_value", "deadline", "dependencies"],
            "optimization_goal": "quality",
            "buffer_percentage": 20
        }
        
        result = await generate_workflow_prompt("sprint_planning", sprint_params)
        print("🚀 Sprint Planning Template:")
        print(result["prompt"])
        print("\n" + "="*80 + "\n")
        
        # Test parameter completions
        completions = get_parameter_completions("sprint_planning", "optimization_goal")
        print("🎯 Optimization Goal Completions:")
        print(completions)
        
    # Run test
    asyncio.run(test_prompts())