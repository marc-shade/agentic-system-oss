import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

class DeploymentManager:
    """
    Manages deployment operations for the Software Planning MCP.
    Handles deployment configurations, environment management, and deployment execution.
    """
    
    def __init__(self):
        self.config_dir = Path(os.path.expanduser("~/.mcp/deployment"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.environments_file = self.config_dir / "environments.json"
        self.deployments_file = self.config_dir / "deployments.json"
        
        # Initialize configuration files
        self._initialize_config_files()
        
        # Load configurations
        self.environments = self._load_environments()
        self.deployments = self._load_deployments()
    
    def _initialize_config_files(self):
        """Initialize configuration files with default values."""
        if not self.environments_file.exists():
            with open(self.environments_file, "w") as f:
                json.dump({"environments": []}, f, indent=2)
        
        if not self.deployments_file.exists():
            with open(self.deployments_file, "w") as f:
                json.dump({"deployments": []}, f, indent=2)
    
    def _load_environments(self) -> Dict[str, Any]:
        """Load environment configurations."""
        try:
            with open(self.environments_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load environments: {e}")
            return {"environments": []}
    
    def _load_deployments(self) -> Dict[str, Any]:
        """Load deployment history."""
        try:
            with open(self.deployments_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load deployments: {e}")
            return {"deployments": []}
    
    def _save_environments(self):
        """Save environment configurations."""
        try:
            with open(self.environments_file, "w") as f:
                json.dump(self.environments, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save environments: {e}")
    
    def _save_deployments(self):
        """Save deployment history."""
        try:
            with open(self.deployments_file, "w") as f:
                json.dump(self.deployments, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save deployments: {e}")
    
    async def create_environment(
        self,
        name: str,
        type: str,
        config: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new deployment environment.
        
        Args:
            name: Environment name (e.g., 'production', 'staging')
            type: Environment type (e.g., 'kubernetes', 'vm', 'serverless')
            config: Environment-specific configuration
            description: Optional environment description
        """
        if any(env["name"] == name for env in self.environments["environments"]):
            raise ValueError(f"Environment '{name}' already exists")
        
        environment = {
            "id": str(len(self.environments["environments"]) + 1),
            "name": name,
            "type": type,
            "config": config,
            "description": description or f"{name} environment",
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        self.environments["environments"].append(environment)
        self._save_environments()
        
        logger.info(f"Created environment: {name}")
        return environment
    
    async def deploy(
        self,
        environment_id: str,
        artifact_path: str,
        version: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deploy an artifact to a specified environment.
        
        Args:
            environment_id: Target environment ID
            artifact_path: Path to the deployment artifact
            version: Version being deployed
            config: Optional deployment configuration
        """
        # Find the environment
        environment = None
        for env in self.environments["environments"]:
            if env["id"] == environment_id:
                environment = env
                break
        
        if not environment:
            raise ValueError(f"Environment with ID '{environment_id}' not found")
        
        # Create deployment record
        deployment = {
            "id": str(len(self.deployments["deployments"]) + 1),
            "environment_id": environment_id,
            "artifact_path": artifact_path,
            "version": version,
            "config": config or {},
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "logs": []
        }
        
        self.deployments["deployments"].append(deployment)
        self._save_deployments()
        
        try:
            # Execute deployment based on environment type
            if environment["type"] == "kubernetes":
                result = await self._deploy_to_kubernetes(environment, deployment)
            elif environment["type"] == "vm":
                result = await self._deploy_to_vm(environment, deployment)
            elif environment["type"] == "serverless":
                result = await self._deploy_serverless(environment, deployment)
            else:
                raise ValueError(f"Unsupported environment type: {environment['type']}")
            
            # Update deployment status
            deployment["status"] = "completed" if result["success"] else "failed"
            deployment["completed_at"] = datetime.now().isoformat()
            deployment["logs"].extend(result.get("logs", []))
            
            self._save_deployments()
            
            logger.info(f"Deployment {deployment['id']} completed with status: {deployment['status']}")
            return deployment
            
        except Exception as e:
            deployment["status"] = "failed"
            deployment["completed_at"] = datetime.now().isoformat()
            deployment["logs"].append(f"Error: {str(e)}")
            
            self._save_deployments()
            raise
    
    async def _deploy_to_kubernetes(
        self, environment: Dict[str, Any], deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy to a Kubernetes environment."""
        if not self._is_executable_available("kubectl"):
            raise RuntimeError("kubectl not available")
        
        logs = []
        success = True
        
        try:
            # Apply Kubernetes configurations
            cmd = [
                "kubectl",
                "--context", environment["config"].get("context", ""),
                "apply",
                "-f", deployment["artifact_path"]
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                logs.append(f"Output: {stdout.decode()}")
            if stderr:
                logs.append(f"Errors: {stderr.decode()}")
            
            success = process.returncode == 0
            
        except Exception as e:
            logs.append(f"Error: {str(e)}")
            success = False
        
        return {"success": success, "logs": logs}
    
    async def _deploy_to_vm(
        self, environment: Dict[str, Any], deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy to a VM environment."""
        logs = []
        success = True
        
        try:
            # Execute deployment script
            script_path = environment["config"].get("deploy_script")
            if not script_path:
                raise ValueError("No deployment script configured")
            
            cmd = [
                script_path,
                "--artifact", deployment["artifact_path"],
                "--version", deployment["version"]
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                logs.append(f"Output: {stdout.decode()}")
            if stderr:
                logs.append(f"Errors: {stderr.decode()}")
            
            success = process.returncode == 0
            
        except Exception as e:
            logs.append(f"Error: {str(e)}")
            success = False
        
        return {"success": success, "logs": logs}
    
    async def _deploy_serverless(
        self, environment: Dict[str, Any], deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy to a serverless environment."""
        if not self._is_executable_available("serverless"):
            raise RuntimeError("serverless framework not available")
        
        logs = []
        success = True
        
        try:
            # Deploy using serverless framework
            cmd = [
                "serverless",
                "deploy",
                "--stage", environment["name"],
                "--config", deployment["artifact_path"]
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                logs.append(f"Output: {stdout.decode()}")
            if stderr:
                logs.append(f"Errors: {stderr.decode()}")
            
            success = process.returncode == 0
            
        except Exception as e:
            logs.append(f"Error: {str(e)}")
            success = False
        
        return {"success": success, "logs": logs}
    
    def _is_executable_available(self, name: str) -> bool:
        """Check if an executable is available in the system PATH."""
        from shutil import which
        return which(name) is not None
    
    async def list_environments(self) -> List[Dict[str, Any]]:
        """List all deployment environments."""
        return self.environments.get("environments", [])
    
    async def list_deployments(
        self,
        environment_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List deployments with optional filtering.
        
        Args:
            environment_id: Optional environment ID filter
            status: Optional status filter
        """
        deployments = self.deployments.get("deployments", [])
        
        if environment_id:
            deployments = [d for d in deployments if d["environment_id"] == environment_id]
        
        if status:
            deployments = [d for d in deployments if d["status"] == status]
        
        return deployments
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for deployment management."""
        return [
            {
                "name": "create_environment",
                "description": "Create a new deployment environment",
                "parameters": [
                    {
                        "name": "name",
                        "description": "Environment name",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "type",
                        "description": "Environment type",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "config",
                        "description": "Environment configuration",
                        "type": "object",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "Optional environment description",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_create_environment,
            },
            {
                "name": "deploy",
                "description": "Deploy an artifact to an environment",
                "parameters": [
                    {
                        "name": "environment_id",
                        "description": "Target environment ID",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "artifact_path",
                        "description": "Path to deployment artifact",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "version",
                        "description": "Version being deployed",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "config",
                        "description": "Optional deployment configuration",
                        "type": "object",
                        "required": False,
                    }
                ],
                "handler": self.tool_deploy,
            },
            {
                "name": "list_environments",
                "description": "List all deployment environments",
                "parameters": [],
                "handler": self.tool_list_environments,
            },
            {
                "name": "list_deployments",
                "description": "List deployments with optional filtering",
                "parameters": [
                    {
                        "name": "environment_id",
                        "description": "Optional environment ID filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "status",
                        "description": "Optional status filter",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_list_deployments,
            },
        ]
    
    async def tool_create_environment(
        self,
        name: str,
        type: str,
        config: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating an environment."""
        try:
            environment = await self.create_environment(name, type, config, description)
            return {
                "environment": environment,
                "message": f"Created environment '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_deploy(
        self,
        environment_id: str,
        artifact_path: str,
        version: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Tool handler for deploying an artifact."""
        try:
            deployment = await self.deploy(environment_id, artifact_path, version, config)
            return {
                "deployment": deployment,
                "message": f"Deployment completed with status: {deployment['status']}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_list_environments(self) -> Dict[str, Any]:
        """Tool handler for listing environments."""
        environments = await self.list_environments()
        return {"environments": environments}
    
    async def tool_list_deployments(
        self,
        environment_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for listing deployments."""
        deployments = await self.list_deployments(environment_id, status)
        return {"deployments": deployments}
