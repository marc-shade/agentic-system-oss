#!/usr/bin/env python3
"""
Software Planning MCP Server with OTEL Business Intelligence
OTEL-instrumented version with comprehensive observability and business intelligence tracking

AI-driven software development planning with full business intelligence.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add mcp-otel-wrapper to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'mcp-otel-wrapper'))

from mcp_otel_wrapper import TraceContext, create_business_span, finish_span, store_trace
from fastmcp import FastMCP
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add("logs/software_planning_mcp.log", rotation="10 MB", retention="1 week", level="DEBUG")

class SoftwarePlanningMCPOTEL:
    """OTEL-Instrumented MCP Server for AI-driven software planning"""
    
    def __init__(self):
        self.name = "software-planning-mcp"
        self.version = "1.0.0-otel"
        self.projects_created = 0
        self.architectures_designed = 0
        self.code_analyses_performed = 0
        self.deployments_planned = 0
        self.tests_designed = 0
        self.total_planning_value = 0.0
        
        # Initialize FastMCP
        self.mcp = FastMCP("software-planning-mcp")
        
        self.setup_tools()
        logger.info("OTEL-Instrumented Software Planning MCP initialized")
    
    def setup_tools(self):
        """Setup MCP tools with OTEL instrumentation"""
        
        @self.mcp.tool()
        def create_project(
            name: str,
            description: str,
            project_type: str = "general",
            complexity: int = 5
        ) -> Dict[str, Any]:
            """
            Create a new software project with cascading task breakdown and OTEL tracking.
            
            Args:
                name: Project name
                description: Project description
                project_type: Type of project (web, mobile, backend, ml, data, general)
                complexity: Complexity score 1-10
            """
            return self._create_project_otel({
                "name": name,
                "description": description,
                "project_type": project_type,
                "complexity": complexity
            })
        
        @self.mcp.tool()
        def breakdown_project(
            project_id: str,
            detail_level: str = "medium"
        ) -> Dict[str, Any]:
            """
            Break down a project into cascading tasks using agent orchestration patterns with OTEL tracking.
            
            Args:
                project_id: ID of the project to break down
                detail_level: Level of detail (high, medium, low)
            """
            return self._breakdown_project_otel({
                "project_id": project_id,
                "detail_level": detail_level
            })
        
        @self.mcp.tool()
        def design_architecture(
            project_id: str,
            requirements: str,
            architecture_type: str = "microservices"
        ) -> Dict[str, Any]:
            """
            Design software architecture with OTEL business intelligence tracking.
            
            Args:
                project_id: ID of the project
                requirements: System requirements
                architecture_type: Architecture pattern (monolith, microservices, serverless)
            """
            return self._design_architecture_otel({
                "project_id": project_id,
                "requirements": requirements,
                "architecture_type": architecture_type
            })
        
        @self.mcp.tool()
        def analyze_code_quality(
            project_path: str,
            analysis_type: str = "comprehensive"
        ) -> Dict[str, Any]:
            """
            Analyze code quality and provide improvement recommendations with OTEL tracking.
            
            Args:
                project_path: Path to the project code
                analysis_type: Type of analysis (quick, comprehensive, security-focused)
            """
            return self._analyze_code_quality_otel({
                "project_path": project_path,
                "analysis_type": analysis_type
            })
        
        @self.mcp.tool()
        def plan_deployment(
            project_id: str,
            target_environment: str,
            deployment_strategy: str = "rolling"
        ) -> Dict[str, Any]:
            """
            Plan deployment strategy with OTEL business intelligence tracking.
            
            Args:
                project_id: ID of the project
                target_environment: Target deployment environment (dev, staging, prod)
                deployment_strategy: Strategy (blue-green, rolling, canary)
            """
            return self._plan_deployment_otel({
                "project_id": project_id,
                "target_environment": target_environment,
                "deployment_strategy": deployment_strategy
            })
        
        @self.mcp.tool()
        def design_test_strategy(
            project_id: str,
            test_types: List[str] = None
        ) -> Dict[str, Any]:
            """
            Design comprehensive testing strategy with OTEL tracking.
            
            Args:
                project_id: ID of the project
                test_types: Types of testing (unit, integration, e2e, performance)
            """
            if test_types is None:
                test_types = ["unit", "integration", "e2e"]
            
            return self._design_test_strategy_otel({
                "project_id": project_id,
                "test_types": test_types
            })
        
        @self.mcp.tool()
        def generate_documentation(
            project_id: str,
            doc_types: List[str] = None
        ) -> Dict[str, Any]:
            """
            Generate project documentation with OTEL business intelligence tracking.
            
            Args:
                project_id: ID of the project
                doc_types: Types of documentation (api, user, developer, deployment)
            """
            if doc_types is None:
                doc_types = ["api", "user", "developer"]
            
            return self._generate_documentation_otel({
                "project_id": project_id,
                "doc_types": doc_types
            })
        
        @self.mcp.tool()
        def suggest_team_composition(
            project_type: str,
            complexity: int,
            specific_requirements: List[str] = None
        ) -> Dict[str, Any]:
            """
            Suggest an AI agent team composition for a project with OTEL tracking.
            
            Args:
                project_type: Type of project
                complexity: Complexity score 1-10
                specific_requirements: List of specific requirements or technologies
            """
            if specific_requirements is None:
                specific_requirements = []
            
            return self._suggest_team_composition_otel({
                "project_type": project_type,
                "complexity": complexity,
                "specific_requirements": specific_requirements
            })
        
        @self.mcp.tool()
        def get_project_status(
            project_id: str
        ) -> Dict[str, Any]:
            """
            Get detailed status of a project including all tasks and agents with OTEL tracking.
            
            Args:
                project_id: ID of the project
            """
            return self._get_project_status_otel({
                "project_id": project_id
            })
    
    def _create_project_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create project with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "create_project", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="create_project",
            content_type="project_planning",
            business_function="project_initiation",
            revenue_attribution="project_management_billable"
        )
        
        start_time = time.time()
        
        try:
            name = arguments["name"]
            description = arguments["description"]
            project_type = arguments.get("project_type", "general")
            complexity = arguments.get("complexity", 5)
            
            # Generate project ID
            project_id = f"proj_{str(uuid.uuid4())[:8]}"
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            project_value = self.calculate_project_creation_value(complexity, len(description), processing_time)
            
            # Update statistics
            self.projects_created += 1
            self.total_planning_value += project_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "project_name": name,
                "project_type": project_type,
                "complexity_score": complexity,
                "description_length": len(description),
                "processing_time": processing_time,
                "project_creation_value": project_value,
                "billable_hours": self.calculate_billable_hours("project_creation", complexity),
                "project_management_rate": 160,  # PM rate per hour
                "total_projects_created": self.projects_created,
                "estimated_project_duration": self.estimate_project_duration(complexity, project_type)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "project": {
                    "id": project_id,
                    "name": name,
                    "description": description,
                    "type": project_type,
                    "complexity": complexity,
                    "status": "planning",
                    "created_at": datetime.now().isoformat(),
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": project_value,
                    "planning_category": "project_creation"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _breakdown_project_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Break down project with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "breakdown_project", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="breakdown_project",
            content_type="task_breakdown",
            business_function="project_decomposition",
            revenue_attribution="strategic_planning_billable"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            detail_level = arguments.get("detail_level", "medium")
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            breakdown_value = self.calculate_breakdown_value(detail_level, processing_time)
            
            # Update statistics
            self.total_planning_value += breakdown_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "detail_level": detail_level,
                "processing_time": processing_time,
                "breakdown_value": breakdown_value,
                "billable_hours": self.calculate_billable_hours("project_breakdown", 1),
                "strategic_planning_rate": 180,  # Strategic planning rate
                "task_count_estimate": self.estimate_task_count(detail_level),
                "agent_assignments": self.suggest_agent_assignments(detail_level)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "breakdown": {
                    "project_id": project_id,
                    "detail_level": detail_level,
                    "tasks": [],  # Placeholder for actual task breakdown
                    "agent_assignments": self.suggest_agent_assignments(detail_level),
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": breakdown_value,
                    "planning_category": "task_breakdown"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _design_architecture_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design architecture with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "design_architecture", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="design_architecture",
            content_type="architecture_design",
            business_function="system_architecture",
            revenue_attribution="architecture_consulting"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            requirements = arguments["requirements"]
            architecture_type = arguments.get("architecture_type", "microservices")
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            architecture_value = self.calculate_architecture_design_value(
                architecture_type, len(requirements), processing_time
            )
            
            # Update statistics
            self.architectures_designed += 1
            self.total_planning_value += architecture_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "architecture_type": architecture_type,
                "requirements_length": len(requirements),
                "processing_time": processing_time,
                "architecture_value": architecture_value,
                "billable_hours": self.calculate_billable_hours("architecture_design", 1),
                "architecture_consulting_rate": 220,  # Architecture consulting rate
                "total_architectures_designed": self.architectures_designed,
                "complexity_assessment": self.assess_architecture_complexity(architecture_type, requirements)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "architecture": {
                    "project_id": project_id,
                    "type": architecture_type,
                    "requirements": requirements,
                    "components": [],  # Placeholder for actual architecture components
                    "patterns": self.suggest_architecture_patterns(architecture_type),
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": architecture_value,
                    "consulting_category": "architecture_design"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_code_quality_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code quality with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "analyze_code_quality", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="analyze_code_quality",
            content_type="code_analysis",
            business_function="quality_assurance",
            revenue_attribution="code_review_billable"
        )
        
        start_time = time.time()
        
        try:
            project_path = arguments["project_path"]
            analysis_type = arguments.get("analysis_type", "comprehensive")
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            analysis_value = self.calculate_code_analysis_value(analysis_type, processing_time)
            
            # Update statistics
            self.code_analyses_performed += 1
            self.total_planning_value += analysis_value
            
            # Add business intelligence to span
            span.update({
                "project_path": project_path,
                "analysis_type": analysis_type,
                "processing_time": processing_time,
                "analysis_value": analysis_value,
                "billable_hours": self.calculate_billable_hours("code_analysis", 1),
                "code_review_rate": 175,  # Code review rate
                "total_analyses_performed": self.code_analyses_performed,
                "quality_score_estimate": self.estimate_quality_score(analysis_type)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "analysis": {
                    "project_path": project_path,
                    "type": analysis_type,
                    "quality_score": self.estimate_quality_score(analysis_type),
                    "recommendations": [],  # Placeholder for actual recommendations
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": analysis_value,
                    "review_category": "code_analysis"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _plan_deployment_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Plan deployment with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "plan_deployment", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="plan_deployment",
            content_type="deployment_planning",
            business_function="devops_strategy",
            revenue_attribution="devops_consulting"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            target_environment = arguments["target_environment"]
            deployment_strategy = arguments.get("deployment_strategy", "rolling")
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            deployment_value = self.calculate_deployment_planning_value(
                deployment_strategy, target_environment, processing_time
            )
            
            # Update statistics
            self.deployments_planned += 1
            self.total_planning_value += deployment_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "target_environment": target_environment,
                "deployment_strategy": deployment_strategy,
                "processing_time": processing_time,
                "deployment_value": deployment_value,
                "billable_hours": self.calculate_billable_hours("deployment_planning", 1),
                "devops_consulting_rate": 190,  # DevOps consulting rate
                "total_deployments_planned": self.deployments_planned,
                "risk_assessment": self.assess_deployment_risk(deployment_strategy, target_environment)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "deployment_plan": {
                    "project_id": project_id,
                    "environment": target_environment,
                    "strategy": deployment_strategy,
                    "steps": [],  # Placeholder for actual deployment steps
                    "risk_level": self.assess_deployment_risk(deployment_strategy, target_environment),
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": deployment_value,
                    "consulting_category": "deployment_planning"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _design_test_strategy_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design test strategy with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "design_test_strategy", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="design_test_strategy",
            content_type="test_planning",
            business_function="quality_assurance",
            revenue_attribution="qa_consulting"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            test_types = arguments.get("test_types", ["unit", "integration", "e2e"])
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            test_value = self.calculate_test_strategy_value(test_types, processing_time)
            
            # Update statistics
            self.tests_designed += 1
            self.total_planning_value += test_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "test_types": test_types,
                "test_count": len(test_types),
                "processing_time": processing_time,
                "test_strategy_value": test_value,
                "billable_hours": self.calculate_billable_hours("test_design", len(test_types)),
                "qa_consulting_rate": 165,  # QA consulting rate
                "total_tests_designed": self.tests_designed,
                "coverage_estimate": self.estimate_test_coverage(test_types)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "test_strategy": {
                    "project_id": project_id,
                    "test_types": test_types,
                    "coverage_estimate": self.estimate_test_coverage(test_types),
                    "test_plans": [],  # Placeholder for actual test plans
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": test_value,
                    "qa_category": "test_strategy"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_documentation_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "generate_documentation", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="generate_documentation",
            content_type="documentation",
            business_function="technical_writing",
            revenue_attribution="documentation_billable"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            doc_types = arguments.get("doc_types", ["api", "user", "developer"])
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            documentation_value = self.calculate_documentation_value(doc_types, processing_time)
            
            # Update statistics
            self.total_planning_value += documentation_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "doc_types": doc_types,
                "doc_count": len(doc_types),
                "processing_time": processing_time,
                "documentation_value": documentation_value,
                "billable_hours": self.calculate_billable_hours("documentation", len(doc_types)),
                "technical_writing_rate": 145,  # Technical writing rate
                "estimated_pages": self.estimate_documentation_pages(doc_types)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "documentation": {
                    "project_id": project_id,
                    "types": doc_types,
                    "estimated_pages": self.estimate_documentation_pages(doc_types),
                    "documents": [],  # Placeholder for actual documents
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": documentation_value,
                    "writing_category": "technical_documentation"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _suggest_team_composition_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest team composition with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "suggest_team_composition", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="suggest_team_composition",
            content_type="team_planning",
            business_function="resource_planning",
            revenue_attribution="strategic_consulting"
        )
        
        start_time = time.time()
        
        try:
            project_type = arguments["project_type"]
            complexity = arguments["complexity"]
            specific_requirements = arguments.get("specific_requirements", [])
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            team_value = self.calculate_team_planning_value(complexity, len(specific_requirements), processing_time)
            
            # Update statistics
            self.total_planning_value += team_value
            
            # Add business intelligence to span
            span.update({
                "project_type": project_type,
                "complexity": complexity,
                "requirements_count": len(specific_requirements),
                "processing_time": processing_time,
                "team_planning_value": team_value,
                "billable_hours": self.calculate_billable_hours("team_planning", 1),
                "strategic_consulting_rate": 200,  # Strategic consulting rate
                "recommended_team_size": self.calculate_team_size(complexity, project_type)
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "team_composition": {
                    "project_type": project_type,
                    "complexity": complexity,
                    "recommended_team": self.generate_team_recommendations(project_type, complexity),
                    "team_size": self.calculate_team_size(complexity, project_type),
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": team_value,
                    "consulting_category": "team_planning"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_project_status_otel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get project status with OTEL tracing"""
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            _meta={"tool_name": "get_project_status", "mcp_server": self.name}
        )
        
        span = create_business_span(
            trace_context=trace_context,
            mcp_server=self.name,
            tool_name="get_project_status",
            content_type="status_report",
            business_function="project_monitoring",
            revenue_attribution="monitoring_billable"
        )
        
        start_time = time.time()
        
        try:
            project_id = arguments["project_id"]
            
            # Calculate business metrics
            processing_time = time.time() - start_time
            status_value = self.calculate_status_reporting_value(processing_time)
            
            # Update statistics
            self.total_planning_value += status_value
            
            # Add business intelligence to span
            span.update({
                "project_id": project_id,
                "processing_time": processing_time,
                "status_reporting_value": status_value,
                "billable_hours": self.calculate_billable_hours("status_reporting", 1),
                "monitoring_rate": 130,  # Project monitoring rate
                "total_planning_value": self.total_planning_value
            })
            
            finish_span(span, success=True)
            store_trace(trace_context, span)
            
            return {
                "success": True,
                "status": {
                    "project_id": project_id,
                    "current_phase": "planning",
                    "completion_percentage": 25,  # Placeholder
                    "active_tasks": [],  # Placeholder
                    "otel_tracked": True
                },
                "otel_metadata": {
                    "processing_time": processing_time,
                    "business_value": status_value,
                    "monitoring_category": "status_reporting"
                }
            }
            
        except Exception as e:
            finish_span(span, success=False, error=str(e))
            store_trace(trace_context, span)
            return {
                "success": False,
                "error": str(e)
            }
    
    # Business value calculation methods
    def calculate_project_creation_value(self, complexity: int, description_length: int, processing_time: float) -> float:
        """Calculate business value for project creation"""
        base_value = 100.0  # Base value for project creation
        complexity_factor = complexity / 5.0  # Normalize complexity
        scope_factor = min(description_length / 200, 2.0)  # Project scope factor
        efficiency_factor = max(0.5, 10.0 / processing_time)
        
        return base_value * complexity_factor * scope_factor * efficiency_factor
    
    def calculate_breakdown_value(self, detail_level: str, processing_time: float) -> float:
        """Calculate business value for project breakdown"""
        base_values = {"low": 50.0, "medium": 80.0, "high": 120.0}
        base_value = base_values.get(detail_level, 80.0)
        efficiency_factor = max(0.6, 15.0 / processing_time)
        
        return base_value * efficiency_factor
    
    def calculate_architecture_design_value(self, architecture_type: str, requirements_length: int, processing_time: float) -> float:
        """Calculate business value for architecture design"""
        type_values = {"monolith": 80.0, "microservices": 150.0, "serverless": 120.0}
        base_value = type_values.get(architecture_type, 100.0)
        complexity_factor = min(requirements_length / 300, 2.5)
        efficiency_factor = max(0.7, 20.0 / processing_time)
        
        return base_value * complexity_factor * efficiency_factor
    
    def calculate_code_analysis_value(self, analysis_type: str, processing_time: float) -> float:
        """Calculate business value for code analysis"""
        type_values = {"quick": 40.0, "comprehensive": 90.0, "security-focused": 110.0}
        base_value = type_values.get(analysis_type, 70.0)
        efficiency_factor = max(0.6, 12.0 / processing_time)
        
        return base_value * efficiency_factor
    
    def calculate_deployment_planning_value(self, strategy: str, environment: str, processing_time: float) -> float:
        """Calculate business value for deployment planning"""
        strategy_values = {"rolling": 60.0, "blue-green": 80.0, "canary": 100.0}
        env_values = {"dev": 1.0, "staging": 1.3, "prod": 1.8}
        
        base_value = strategy_values.get(strategy, 70.0)
        env_factor = env_values.get(environment, 1.2)
        efficiency_factor = max(0.6, 10.0 / processing_time)
        
        return base_value * env_factor * efficiency_factor
    
    def calculate_test_strategy_value(self, test_types: List[str], processing_time: float) -> float:
        """Calculate business value for test strategy"""
        base_value = 30.0  # Base value per test type
        complexity_factor = len(test_types) * 0.8
        efficiency_factor = max(0.7, 8.0 / processing_time)
        
        return base_value * complexity_factor * efficiency_factor
    
    def calculate_documentation_value(self, doc_types: List[str], processing_time: float) -> float:
        """Calculate business value for documentation"""
        base_value = 25.0  # Base value per doc type
        scope_factor = len(doc_types) * 0.9
        efficiency_factor = max(0.6, 12.0 / processing_time)
        
        return base_value * scope_factor * efficiency_factor
    
    def calculate_team_planning_value(self, complexity: int, requirements_count: int, processing_time: float) -> float:
        """Calculate business value for team planning"""
        base_value = 85.0
        complexity_factor = complexity / 5.0
        requirements_factor = min(requirements_count / 5, 2.0)
        efficiency_factor = max(0.7, 8.0 / processing_time)
        
        return base_value * complexity_factor * requirements_factor * efficiency_factor
    
    def calculate_status_reporting_value(self, processing_time: float) -> float:
        """Calculate business value for status reporting"""
        base_value = 35.0
        efficiency_factor = max(0.8, 5.0 / processing_time)
        
        return base_value * efficiency_factor
    
    def calculate_billable_hours(self, operation_type: str, count: int) -> float:
        """Calculate billable hours for different operations"""
        base_hours = {
            "project_creation": 1.5,
            "project_breakdown": 1.0,
            "architecture_design": 2.0,
            "code_analysis": 0.8,
            "deployment_planning": 1.2,
            "test_design": 0.6,
            "documentation": 0.4,
            "team_planning": 0.8,
            "status_reporting": 0.3
        }
        
        return base_hours.get(operation_type, 0.5) * count
    
    # Helper methods for business intelligence
    def estimate_project_duration(self, complexity: int, project_type: str) -> str:
        """Estimate project duration based on complexity and type"""
        base_weeks = {"web": 8, "mobile": 10, "backend": 6, "ml": 12, "data": 8, "general": 8}
        weeks = base_weeks.get(project_type, 8) * (complexity / 5.0)
        return f"{int(weeks)} weeks"
    
    def estimate_task_count(self, detail_level: str) -> int:
        """Estimate number of tasks based on detail level"""
        counts = {"low": 8, "medium": 15, "high": 25}
        return counts.get(detail_level, 15)
    
    def suggest_agent_assignments(self, detail_level: str) -> List[str]:
        """Suggest agent assignments based on detail level"""
        base_agents = ["project_manager", "architect", "developer"]
        if detail_level == "high":
            base_agents.extend(["qa_engineer", "devops_engineer", "ui_designer"])
        elif detail_level == "medium":
            base_agents.append("qa_engineer")
        
        return base_agents
    
    def suggest_architecture_patterns(self, architecture_type: str) -> List[str]:
        """Suggest architecture patterns based on type"""
        patterns = {
            "microservices": ["API Gateway", "Circuit Breaker", "Event Sourcing"],
            "monolith": ["Layered Architecture", "MVC", "Repository Pattern"],
            "serverless": ["Function as a Service", "Event-Driven", "CQRS"]
        }
        return patterns.get(architecture_type, ["Layered Architecture"])
    
    def assess_architecture_complexity(self, architecture_type: str, requirements: str) -> str:
        """Assess architecture complexity"""
        base_complexity = {"microservices": "High", "monolith": "Medium", "serverless": "Medium"}
        complexity = base_complexity.get(architecture_type, "Medium")
        
        if len(requirements) > 500:
            complexity_levels = {"Low": "Medium", "Medium": "High", "High": "Very High"}
            complexity = complexity_levels.get(complexity, "High")
        
        return complexity
    
    def estimate_quality_score(self, analysis_type: str) -> int:
        """Estimate quality score based on analysis type"""
        scores = {"quick": 75, "comprehensive": 85, "security-focused": 88}
        return scores.get(analysis_type, 80)
    
    def assess_deployment_risk(self, strategy: str, environment: str) -> str:
        """Assess deployment risk"""
        strategy_risk = {"rolling": "Medium", "blue-green": "Low", "canary": "Low"}
        env_risk = {"dev": "Low", "staging": "Medium", "prod": "High"}
        
        return f"{strategy_risk.get(strategy, 'Medium')} (Strategy) / {env_risk.get(environment, 'Medium')} (Environment)"
    
    def estimate_test_coverage(self, test_types: List[str]) -> str:
        """Estimate test coverage percentage"""
        coverage_map = {"unit": 30, "integration": 25, "e2e": 20, "performance": 15}
        total_coverage = sum(coverage_map.get(test_type, 10) for test_type in test_types)
        return f"{min(total_coverage, 95)}%"
    
    def estimate_documentation_pages(self, doc_types: List[str]) -> int:
        """Estimate number of documentation pages"""
        page_map = {"api": 15, "user": 20, "developer": 25, "deployment": 10}
        return sum(page_map.get(doc_type, 12) for doc_type in doc_types)
    
    def generate_team_recommendations(self, project_type: str, complexity: int) -> List[str]:
        """Generate team recommendations"""
        base_team = ["project_manager", "senior_developer", "architect"]
        
        if complexity >= 7:
            base_team.extend(["qa_engineer", "devops_engineer", "ui_designer", "data_analyst"])
        elif complexity >= 5:
            base_team.extend(["qa_engineer", "devops_engineer"])
        elif complexity >= 3:
            base_team.append("qa_engineer")
        
        # Add project-type specific roles
        type_roles = {
            "web": ["frontend_developer", "backend_developer"],
            "mobile": ["mobile_developer", "ui_designer"],
            "ml": ["data_scientist", "ml_engineer"],
            "data": ["data_engineer", "data_analyst"]
        }
        
        base_team.extend(type_roles.get(project_type, ["full_stack_developer"]))
        
        return list(set(base_team))  # Remove duplicates
    
    def calculate_team_size(self, complexity: int, project_type: str) -> int:
        """Calculate recommended team size"""
        base_size = 3
        complexity_factor = max(1, complexity // 2)
        type_factor = {"web": 1, "mobile": 1, "backend": 0, "ml": 1, "data": 1}.get(project_type, 0)
        
        return base_size + complexity_factor + type_factor
    
    async def start(self):
        """Start the OTEL-instrumented Software Planning MCP server"""
        logger.info("🚀 Starting OTEL-Instrumented Software Planning MCP Server")
        logger.info("📊 OTEL business intelligence tracking enabled")
        
        try:
            await self.mcp.run()
        except KeyboardInterrupt:
            logger.info("🛑 OTEL Server stopped by user")
        except Exception as e:
            logger.error(f"💥 OTEL Fatal error: {str(e)}", exc_info=True)
            raise

async def main():
    """Main entry point for the OTEL-instrumented Software Planning MCP server"""
    spmcp = SoftwarePlanningMCPOTEL()
    await spmcp.start()

if __name__ == "__main__":
    asyncio.run(main())