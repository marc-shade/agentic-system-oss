import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from loguru import logger

from .knowledge_base import KnowledgeBaseManager

class ProjectLifecycleManager:
    """
    Manages the project lifecycle for the Software Planning MCP.
    Handles requirements engineering, architecture planning, development planning,
    testing strategies, and deployment planning.
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBaseManager] = None):
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.projects_dir = Path(os.path.expanduser("~/.mcp/projects"))
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base = knowledge_base
    
    async def load_projects(self) -> None:
        """Load all projects from disk."""
        for project_file in self.projects_dir.glob("*.json"):
            try:
                with open(project_file, "r") as f:
                    project_data = json.load(f)
                    project_id = project_data.get("id")
                    if project_id:
                        self.projects[project_id] = project_data
                        logger.debug(f"Loaded project: {project_data.get('name')} ({project_id})")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load project from {project_file}: {e}")
    
    async def save_project(self, project_id: str) -> None:
        """Save a project to disk."""
        if project_id not in self.projects:
            logger.warning(f"Cannot save project {project_id}: Project not found")
            return
        
        project_file = self.projects_dir / f"{project_id}.json"
        try:
            with open(project_file, "w") as f:
                json.dump(self.projects[project_id], f, indent=2)
            logger.debug(f"Saved project: {self.projects[project_id].get('name')} ({project_id})")
        except IOError as e:
            logger.error(f"Failed to save project {project_id}: {e}")
    
    async def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new project.
        
        Args:
            name: The name of the project
            description: A description of the project
            project_type: The type of project (e.g., "web", "mobile", "desktop", "library")
            metadata: Optional metadata for the project
            
        Returns:
            The ID of the created project
        """
        project_id = f"project-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(name) % 10000}"
        now = datetime.now().isoformat()
        
        project = {
            "id": project_id,
            "name": name,
            "description": description,
            "type": project_type,
            "created_at": now,
            "updated_at": now,
            "status": "created",
            "metadata": metadata or {},
            "requirements": [],
            "architecture": {
                "components": [],
                "dependencies": [],
                "technologies": []
            },
            "development": {
                "tasks": [],
                "milestones": [],
                "resources": []
            },
            "testing": {
                "strategy": {},
                "test_cases": [],
                "test_environments": []
            },
            "deployment": {
                "strategy": {},
                "environments": [],
                "pipelines": []
            }
        }
        
        self.projects[project_id] = project
        await self.save_project(project_id)
        
        # Add project to knowledge base if available
        if self.knowledge_base:
            await self.knowledge_base.add_document(
                title=f"Project: {name}",
                content=description,
                document_type="project",
                project_id=project_id,
                tags=["project", project_type],
                custom_id=f"doc-project-{project_id}"
            )
        
        logger.info(f"Created project: {name} ({project_id})")
        return project_id
    
    async def add_requirement(
        self,
        project_id: str,
        title: str,
        description: str,
        requirement_type: str,
        priority: str,
        status: str = "proposed",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a requirement to a project.
        
        Args:
            project_id: The ID of the project
            title: The title of the requirement
            description: A description of the requirement
            requirement_type: The type of requirement (e.g., "functional", "non-functional")
            priority: The priority of the requirement (e.g., "high", "medium", "low")
            status: The status of the requirement (e.g., "proposed", "approved", "implemented")
            metadata: Optional metadata for the requirement
            
        Returns:
            The ID of the added requirement
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        requirement_id = f"req-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        requirement = {
            "id": requirement_id,
            "title": title,
            "description": description,
            "type": requirement_type,
            "priority": priority,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }
        
        self.projects[project_id]["requirements"].append(requirement)
        self.projects[project_id]["updated_at"] = now
        await self.save_project(project_id)
        
        # Add requirement to knowledge base if available
        if self.knowledge_base:
            await self.knowledge_base.add_document(
                title=f"Requirement: {title}",
                content=description,
                document_type="requirement",
                project_id=project_id,
                tags=["requirement", requirement_type, priority],
                custom_id=f"doc-req-{requirement_id}"
            )
        
        logger.info(f"Added requirement '{title}' to project {project_id}")
        return requirement_id
    
    async def add_architecture_component(
        self,
        project_id: str,
        name: str,
        description: str,
        component_type: str,
        responsibilities: List[str],
        dependencies: List[str] = None,
        technologies: List[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an architecture component to a project.
        
        Args:
            project_id: The ID of the project
            name: The name of the component
            description: A description of the component
            component_type: The type of component (e.g., "service", "database", "ui")
            responsibilities: List of responsibilities for the component
            dependencies: Optional list of dependencies on other components
            technologies: Optional list of technologies used by the component
            metadata: Optional metadata for the component
            
        Returns:
            The ID of the added component
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        component_id = f"comp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(name) % 10000}"
        now = datetime.now().isoformat()
        
        component = {
            "id": component_id,
            "name": name,
            "description": description,
            "type": component_type,
            "responsibilities": responsibilities,
            "dependencies": dependencies or [],
            "technologies": technologies or [],
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }
        
        self.projects[project_id]["architecture"]["components"].append(component)
        self.projects[project_id]["updated_at"] = now
        await self.save_project(project_id)
        
        # Add component to knowledge base if available
        if self.knowledge_base:
            content = f"{description}\n\nResponsibilities:\n" + "\n".join([f"- {r}" for r in responsibilities])
            if dependencies:
                content += f"\n\nDependencies:\n" + "\n".join([f"- {d}" for d in dependencies])
            if technologies:
                content += f"\n\nTechnologies:\n" + "\n".join([f"- {t}" for t in technologies])
            
            await self.knowledge_base.add_document(
                title=f"Architecture Component: {name}",
                content=content,
                document_type="architecture",
                project_id=project_id,
                tags=["architecture", "component", component_type],
                custom_id=f"doc-comp-{component_id}"
            )
        
        logger.info(f"Added architecture component '{name}' to project {project_id}")
        return component_id
    
    async def add_development_task(
        self,
        project_id: str,
        title: str,
        description: str,
        task_type: str,
        priority: str,
        estimate: str,
        dependencies: List[str] = None,
        assignee: Optional[str] = None,
        status: str = "todo",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a development task to a project.
        
        Args:
            project_id: The ID of the project
            title: The title of the task
            description: A description of the task
            task_type: The type of task (e.g., "feature", "bug", "refactor")
            priority: The priority of the task (e.g., "high", "medium", "low")
            estimate: The estimated effort for the task (e.g., "2h", "1d")
            dependencies: Optional list of dependencies on other tasks
            assignee: Optional assignee for the task
            status: The status of the task (e.g., "todo", "in_progress", "done")
            metadata: Optional metadata for the task
            
        Returns:
            The ID of the added task
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        task_id = f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "type": task_type,
            "priority": priority,
            "estimate": estimate,
            "dependencies": dependencies or [],
            "assignee": assignee,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }
        
        self.projects[project_id]["development"]["tasks"].append(task)
        self.projects[project_id]["updated_at"] = now
        await self.save_project(project_id)
        
        logger.info(f"Added development task '{title}' to project {project_id}")
        return task_id
    
    async def add_test_case(
        self,
        project_id: str,
        title: str,
        description: str,
        test_type: str,
        steps: List[str],
        expected_result: str,
        requirements: List[str] = None,
        priority: str = "medium",
        status: str = "draft",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a test case to a project.
        
        Args:
            project_id: The ID of the project
            title: The title of the test case
            description: A description of the test case
            test_type: The type of test (e.g., "unit", "integration", "e2e")
            steps: List of steps to execute the test
            expected_result: The expected result of the test
            requirements: Optional list of requirements covered by the test
            priority: The priority of the test case (e.g., "high", "medium", "low")
            status: The status of the test case (e.g., "draft", "ready", "automated")
            metadata: Optional metadata for the test case
            
        Returns:
            The ID of the added test case
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        test_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        test_case = {
            "id": test_id,
            "title": title,
            "description": description,
            "type": test_type,
            "steps": steps,
            "expected_result": expected_result,
            "requirements": requirements or [],
            "priority": priority,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }
        
        self.projects[project_id]["testing"]["test_cases"].append(test_case)
        self.projects[project_id]["updated_at"] = now
        await self.save_project(project_id)
        
        logger.info(f"Added test case '{title}' to project {project_id}")
        return test_id
    
    async def add_deployment_environment(
        self,
        project_id: str,
        name: str,
        description: str,
        environment_type: str,
        configuration: Dict[str, Any],
        prerequisites: List[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a deployment environment to a project.
        
        Args:
            project_id: The ID of the project
            name: The name of the environment
            description: A description of the environment
            environment_type: The type of environment (e.g., "development", "staging", "production")
            configuration: Configuration details for the environment
            prerequisites: Optional list of prerequisites for the environment
            metadata: Optional metadata for the environment
            
        Returns:
            The ID of the added environment
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        env_id = f"env-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(name) % 10000}"
        now = datetime.now().isoformat()
        
        environment = {
            "id": env_id,
            "name": name,
            "description": description,
            "type": environment_type,
            "configuration": configuration,
            "prerequisites": prerequisites or [],
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }
        
        self.projects[project_id]["deployment"]["environments"].append(environment)
        self.projects[project_id]["updated_at"] = now
        await self.save_project(project_id)
        
        logger.info(f"Added deployment environment '{name}' to project {project_id}")
        return env_id
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for project lifecycle management."""
        return [
            {
                "name": "create_project",
                "description": "Create a new software project",
                "parameters": [
                    {
                        "name": "name",
                        "description": "The name of the project",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "A description of the project",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "project_type",
                        "description": "The type of project (e.g., 'web', 'mobile', 'desktop', 'library')",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_create_project,
            },
            {
                "name": "add_requirement",
                "description": "Add a requirement to a project",
                "parameters": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "title",
                        "description": "The title of the requirement",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "A description of the requirement",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "requirement_type",
                        "description": "The type of requirement (e.g., 'functional', 'non-functional')",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "priority",
                        "description": "The priority of the requirement (e.g., 'high', 'medium', 'low')",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_add_requirement,
            },
            {
                "name": "add_architecture_component",
                "description": "Add an architecture component to a project",
                "parameters": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "name",
                        "description": "The name of the component",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "A description of the component",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "component_type",
                        "description": "The type of component (e.g., 'service', 'database', 'ui')",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "responsibilities",
                        "description": "List of responsibilities for the component",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": True,
                    },
                    {
                        "name": "technologies",
                        "description": "List of technologies used by the component",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": False,
                    }
                ],
                "handler": self.tool_add_architecture_component,
            },
            {
                "name": "get_project",
                "description": "Get a project by ID",
                "parameters": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_get_project,
            },
            {
                "name": "list_projects",
                "description": "List all projects",
                "parameters": [],
                "handler": self.tool_list_projects,
            },
        ]
    
    async def tool_create_project(self, name: str, description: str, project_type: str) -> Dict[str, Any]:
        """Tool handler for creating a new project."""
        project_id = await self.create_project(name, description, project_type)
        return {
            "project_id": project_id,
            "message": f"Created project '{name}' with ID {project_id}"
        }
    
    async def tool_add_requirement(
        self, project_id: str, title: str, description: str, requirement_type: str, priority: str
    ) -> Dict[str, Any]:
        """Tool handler for adding a requirement to a project."""
        try:
            requirement_id = await self.add_requirement(
                project_id, title, description, requirement_type, priority
            )
            return {
                "requirement_id": requirement_id,
                "message": f"Added requirement '{title}' to project {project_id}"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_add_architecture_component(
        self, project_id: str, name: str, description: str, component_type: str, 
        responsibilities: List[str], technologies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for adding an architecture component to a project."""
        try:
            component_id = await self.add_architecture_component(
                project_id, name, description, component_type, responsibilities, technologies=technologies
            )
            return {
                "component_id": component_id,
                "message": f"Added architecture component '{name}' to project {project_id}"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_get_project(self, project_id: str) -> Dict[str, Any]:
        """Tool handler for getting a project by ID."""
        if project_id not in self.projects:
            return {"error": f"Project {project_id} not found"}
        return {"project": self.projects[project_id]}
    
    async def tool_list_projects(self) -> Dict[str, Any]:
        """Tool handler for listing all projects."""
        project_summaries = []
        for project_id, project in self.projects.items():
            project_summaries.append({
                "id": project_id,
                "name": project["name"],
                "description": project["description"],
                "type": project["type"],
                "status": project["status"],
                "created_at": project["created_at"],
                "updated_at": project["updated_at"],
            })
        return {"projects": project_summaries}
