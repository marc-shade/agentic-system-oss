import os
import json
import asyncio
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from loguru import logger

class WorkflowState(Enum):
    """Workflow states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskState(Enum):
    """Task states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowManager:
    """
    Manages workflow orchestration and process automation for the Software Planning MCP.
    Handles workflow definitions, task execution, state management, and error handling.
    """
    
    def __init__(self):
        self.workflows_dir = Path(os.path.expanduser("~/.mcp/workflows"))
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.definitions_file = self.workflows_dir / "definitions.json"
        self.instances_file = self.workflows_dir / "instances.json"
        
        # Initialize workflow files
        self._initialize_workflow_files()
        
        # Load workflow data
        self.workflow_definitions = self._load_definitions()
        self.workflow_instances = self._load_instances()
        
        # Task handlers registry
        self.task_handlers: Dict[str, Callable] = {}
        
        # Active workflow tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    def _initialize_workflow_files(self):
        """Initialize workflow files with default values."""
        if not self.definitions_file.exists():
            with open(self.definitions_file, "w") as f:
                json.dump({"workflows": []}, f, indent=2)
        
        if not self.instances_file.exists():
            with open(self.instances_file, "w") as f:
                json.dump({"instances": []}, f, indent=2)
    
    def _load_definitions(self) -> Dict[str, Any]:
        """Load workflow definitions."""
        try:
            with open(self.definitions_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load workflow definitions: {e}")
            return {"workflows": []}
    
    def _load_instances(self) -> Dict[str, Any]:
        """Load workflow instances."""
        try:
            with open(self.instances_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load workflow instances: {e}")
            return {"instances": []}
    
    def _save_definitions(self):
        """Save workflow definitions."""
        try:
            with open(self.definitions_file, "w") as f:
                json.dump(self.workflow_definitions, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save workflow definitions: {e}")
    
    def _save_instances(self):
        """Save workflow instances."""
        try:
            with open(self.instances_file, "w") as f:
                json.dump(self.workflow_instances, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save workflow instances: {e}")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        Register a task handler function.
        
        Args:
            task_type: Type of task
            handler: Handler function for the task
        """
        self.task_handlers[task_type] = handler
    
    async def create_workflow(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new workflow definition.
        
        Args:
            name: Workflow name
            tasks: List of task definitions
            description: Optional workflow description
            tags: Optional workflow tags
            
        Returns:
            Workflow definition
        """
        # Check if workflow already exists
        if any(w["name"] == name for w in self.workflow_definitions["workflows"]):
            raise ValueError(f"Workflow '{name}' already exists")
        
        # Validate tasks
        for task in tasks:
            if "type" not in task:
                raise ValueError("Task definition must include 'type'")
            if task["type"] not in self.task_handlers:
                raise ValueError(f"No handler registered for task type '{task['type']}'")
        
        # Create workflow definition
        workflow = {
            "id": str(len(self.workflow_definitions["workflows"]) + 1),
            "name": name,
            "description": description or f"Workflow: {name}",
            "tasks": tasks,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.workflow_definitions["workflows"].append(workflow)
        self._save_definitions()
        
        logger.info(f"Created workflow: {name}")
        return workflow
    
    async def start_workflow(
        self,
        workflow_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a workflow instance.
        
        Args:
            workflow_name: Name of the workflow to start
            parameters: Optional workflow parameters
            
        Returns:
            Workflow instance
        """
        # Find workflow definition
        workflow = None
        for w in self.workflow_definitions["workflows"]:
            if w["name"] == workflow_name:
                workflow = w
                break
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create workflow instance
        instance = {
            "id": str(len(self.workflow_instances["instances"]) + 1),
            "workflow_id": workflow["id"],
            "state": WorkflowState.PENDING.value,
            "tasks": [
                {
                    "id": str(i + 1),
                    "type": task["type"],
                    "config": task.get("config", {}),
                    "state": TaskState.PENDING.value,
                    "result": None,
                    "error": None,
                    "started_at": None,
                    "completed_at": None
                }
                for i, task in enumerate(workflow["tasks"])
            ],
            "parameters": parameters or {},
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None
        }
        
        self.workflow_instances["instances"].append(instance)
        self._save_instances()
        
        # Start workflow execution
        task = asyncio.create_task(self._execute_workflow(instance))
        self.active_tasks[instance["id"]] = task
        
        logger.info(f"Started workflow instance: {workflow_name} ({instance['id']})")
        return instance
    
    async def _execute_workflow(self, instance: Dict[str, Any]):
        """Execute a workflow instance."""
        try:
            instance["state"] = WorkflowState.RUNNING.value
            instance["started_at"] = datetime.now().isoformat()
            self._save_instances()
            
            # Execute tasks sequentially
            for task in instance["tasks"]:
                try:
                    task["state"] = TaskState.RUNNING.value
                    task["started_at"] = datetime.now().isoformat()
                    self._save_instances()
                    
                    # Get task handler
                    handler = self.task_handlers[task["type"]]
                    
                    # Execute task
                    result = await handler(task["config"], instance["parameters"])
                    
                    task["state"] = TaskState.COMPLETED.value
                    task["result"] = result
                    task["completed_at"] = datetime.now().isoformat()
                    
                except Exception as e:
                    task["state"] = TaskState.FAILED.value
                    task["error"] = str(e)
                    task["completed_at"] = datetime.now().isoformat()
                    raise
                
                finally:
                    self._save_instances()
            
            instance["state"] = WorkflowState.COMPLETED.value
            instance["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            instance["state"] = WorkflowState.FAILED.value
            instance["error"] = str(e)
            instance["completed_at"] = datetime.now().isoformat()
            logger.error(f"Workflow failed: {str(e)}")
            
        finally:
            self._save_instances()
            self.active_tasks.pop(instance["id"], None)
    
    async def cancel_workflow(self, instance_id: str) -> Dict[str, Any]:
        """
        Cancel a running workflow instance.
        
        Args:
            instance_id: ID of the workflow instance
            
        Returns:
            Updated workflow instance
        """
        # Find workflow instance
        instance = None
        for inst in self.workflow_instances["instances"]:
            if inst["id"] == instance_id:
                instance = inst
                break
        
        if not instance:
            raise ValueError(f"Workflow instance '{instance_id}' not found")
        
        # Cancel if running
        if instance["state"] == WorkflowState.RUNNING.value:
            if instance["id"] in self.active_tasks:
                self.active_tasks[instance["id"]].cancel()
                try:
                    await self.active_tasks[instance["id"]]
                except asyncio.CancelledError:
                    pass
                self.active_tasks.pop(instance["id"])
            
            instance["state"] = WorkflowState.CANCELLED.value
            instance["completed_at"] = datetime.now().isoformat()
            
            # Mark running tasks as skipped
            for task in instance["tasks"]:
                if task["state"] == TaskState.RUNNING.value:
                    task["state"] = TaskState.SKIPPED.value
                    task["completed_at"] = datetime.now().isoformat()
            
            self._save_instances()
            logger.info(f"Cancelled workflow instance: {instance_id}")
        
        return instance
    
    async def get_workflow_status(
        self,
        instance_id: str
    ) -> Dict[str, Any]:
        """
        Get status of a workflow instance.
        
        Args:
            instance_id: ID of the workflow instance
            
        Returns:
            Workflow instance status
        """
        # Find workflow instance
        instance = None
        for inst in self.workflow_instances["instances"]:
            if inst["id"] == instance_id:
                instance = inst
                break
        
        if not instance:
            raise ValueError(f"Workflow instance '{instance_id}' not found")
        
        return {
            "id": instance["id"],
            "workflow_id": instance["workflow_id"],
            "state": instance["state"],
            "tasks": [
                {
                    "id": task["id"],
                    "type": task["type"],
                    "state": task["state"],
                    "started_at": task["started_at"],
                    "completed_at": task["completed_at"],
                    "error": task["error"]
                }
                for task in instance["tasks"]
            ],
            "started_at": instance["started_at"],
            "completed_at": instance["completed_at"],
            "error": instance["error"]
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for workflow management."""
        return [
            {
                "name": "create_workflow",
                "description": "Create a new workflow definition",
                "parameters": [
                    {
                        "name": "name",
                        "description": "Workflow name",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "tasks",
                        "description": "List of task definitions",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "config": {"type": "object"}
                            }
                        },
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "Optional workflow description",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "tags",
                        "description": "Optional workflow tags",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": False,
                    }
                ],
                "handler": self.tool_create_workflow,
            },
            {
                "name": "start_workflow",
                "description": "Start a workflow instance",
                "parameters": [
                    {
                        "name": "workflow_name",
                        "description": "Name of the workflow to start",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "parameters",
                        "description": "Optional workflow parameters",
                        "type": "object",
                        "required": False,
                    }
                ],
                "handler": self.tool_start_workflow,
            },
            {
                "name": "cancel_workflow",
                "description": "Cancel a running workflow instance",
                "parameters": [
                    {
                        "name": "instance_id",
                        "description": "ID of the workflow instance",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_cancel_workflow,
            },
            {
                "name": "get_workflow_status",
                "description": "Get status of a workflow instance",
                "parameters": [
                    {
                        "name": "instance_id",
                        "description": "ID of the workflow instance",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_get_workflow_status,
            },
        ]
    
    async def tool_create_workflow(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating a workflow."""
        try:
            workflow = await self.create_workflow(name, tasks, description, tags)
            return {
                "workflow": workflow,
                "message": f"Created workflow '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_start_workflow(
        self,
        workflow_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Tool handler for starting a workflow."""
        try:
            instance = await self.start_workflow(workflow_name, parameters)
            return {
                "instance": instance,
                "message": f"Started workflow '{workflow_name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_cancel_workflow(
        self,
        instance_id: str
    ) -> Dict[str, Any]:
        """Tool handler for cancelling a workflow."""
        try:
            instance = await self.cancel_workflow(instance_id)
            return {
                "instance": instance,
                "message": f"Cancelled workflow instance {instance_id}"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_get_workflow_status(
        self,
        instance_id: str
    ) -> Dict[str, Any]:
        """Tool handler for getting workflow status."""
        try:
            status = await self.get_workflow_status(instance_id)
            return {"status": status}
        except ValueError as e:
            return {"error": str(e)}
    
    async def cleanup(self):
        """Clean up resources."""
        # Cancel all active workflow tasks
        for task in self.active_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.active_tasks.clear()
