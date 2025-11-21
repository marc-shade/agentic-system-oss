import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from loguru import logger

class CollaborationManager:
    """
    Manages collaboration features for the Software Planning MCP.
    Handles team management, version control integration, communication channels,
    and task tracking.
    """
    
    def __init__(self):
        self.config_dir = Path(os.path.expanduser("~/.mcp/collaboration"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.teams_file = self.config_dir / "teams.json"
        self.vcs_config_file = self.config_dir / "vcs_config.json"
        self.communication_config_file = self.config_dir / "communication_config.json"
        self.task_tracking_file = self.config_dir / "task_tracking.json"
        
        # Initialize configuration files if they don't exist
        self._initialize_config_files()
        
        # Load configurations
        self.teams = self._load_teams()
        self.vcs_configs = self._load_vcs_configs()
        self.communication_configs = self._load_communication_configs()
        self.task_tracking = self._load_task_tracking()
        
        # Detect available VCS tools
        self.vcs_tools = self._detect_vcs_tools()
    
    def _initialize_config_files(self):
        """Initialize configuration files with default values if they don't exist."""
        if not self.teams_file.exists():
            with open(self.teams_file, "w") as f:
                json.dump({"teams": []}, f, indent=2)
        
        if not self.vcs_config_file.exists():
            with open(self.vcs_config_file, "w") as f:
                json.dump({"configurations": []}, f, indent=2)
        
        if not self.communication_config_file.exists():
            with open(self.communication_config_file, "w") as f:
                json.dump({"configurations": []}, f, indent=2)
        
        if not self.task_tracking_file.exists():
            with open(self.task_tracking_file, "w") as f:
                json.dump({"tasks": [], "projects": []}, f, indent=2)
    
    def _load_teams(self) -> Dict[str, Any]:
        """Load team configurations."""
        try:
            with open(self.teams_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load teams configuration: {e}")
            return {"teams": []}
    
    def _load_vcs_configs(self) -> Dict[str, Any]:
        """Load version control system configurations."""
        try:
            with open(self.vcs_config_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load VCS configuration: {e}")
            return {"configurations": []}
    
    def _load_communication_configs(self) -> Dict[str, Any]:
        """Load communication channel configurations."""
        try:
            with open(self.communication_config_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load communication configuration: {e}")
            return {"configurations": []}
    
    def _load_task_tracking(self) -> Dict[str, Any]:
        """Load task tracking data."""
        try:
            with open(self.task_tracking_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load task tracking data: {e}")
            return {"tasks": [], "projects": []}
    
    def _save_teams(self):
        """Save team configurations."""
        try:
            with open(self.teams_file, "w") as f:
                json.dump(self.teams, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save teams configuration: {e}")
    
    def _save_vcs_configs(self):
        """Save version control system configurations."""
        try:
            with open(self.vcs_config_file, "w") as f:
                json.dump(self.vcs_configs, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save VCS configuration: {e}")
    
    def _save_communication_configs(self):
        """Save communication channel configurations."""
        try:
            with open(self.communication_config_file, "w") as f:
                json.dump(self.communication_configs, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save communication configuration: {e}")
    
    def _save_task_tracking(self):
        """Save task tracking data."""
        try:
            with open(self.task_tracking_file, "w") as f:
                json.dump(self.task_tracking, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save task tracking data: {e}")
    
    def _detect_vcs_tools(self) -> Dict[str, Dict[str, Any]]:
        """Detect available version control tools."""
        vcs_tools = {}
        
        # Check for Git
        if self._is_executable_available("git"):
            vcs_tools["git"] = {
                "name": "Git",
                "command": "git",
                "available": True,
                "version": self._get_git_version()
            }
        
        # Check for SVN
        if self._is_executable_available("svn"):
            vcs_tools["svn"] = {
                "name": "Subversion",
                "command": "svn",
                "available": True,
                "version": self._get_svn_version()
            }
        
        # Check for Mercurial
        if self._is_executable_available("hg"):
            vcs_tools["hg"] = {
                "name": "Mercurial",
                "command": "hg",
                "available": True,
                "version": self._get_hg_version()
            }
        
        return vcs_tools
    
    def _is_executable_available(self, name: str) -> bool:
        """Check if an executable is available in the system PATH."""
        from shutil import which
        return which(name) is not None
    
    def _get_git_version(self) -> str:
        """Get Git version."""
        try:
            result = subprocess.run(
                ["git", "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return "Unknown"
    
    def _get_svn_version(self) -> str:
        """Get Subversion version."""
        try:
            result = subprocess.run(
                ["svn", "--version", "--quiet"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return "Unknown"
    
    def _get_hg_version(self) -> str:
        """Get Mercurial version."""
        try:
            result = subprocess.run(
                ["hg", "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.split("\n")[0].strip()
        except subprocess.SubprocessError:
            return "Unknown"
    
    async def create_team(
        self, 
        name: str, 
        description: Optional[str] = None,
        members: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new team.
        
        Args:
            name: The name of the team
            description: Optional description of the team
            members: Optional list of team members with roles
            
        Returns:
            Information about the created team
        """
        # Check if team already exists
        if any(team["name"] == name for team in self.teams.get("teams", [])):
            raise ValueError(f"Team '{name}' already exists")
        
        # Create new team
        team = {
            "id": str(len(self.teams.get("teams", [])) + 1),
            "name": name,
            "description": description or f"Team {name}",
            "created_at": datetime.now().isoformat(),
            "members": members or [],
            "projects": []
        }
        
        # Add team to configuration
        self.teams.setdefault("teams", []).append(team)
        self._save_teams()
        
        logger.info(f"Created team: {name}")
        return team
    
    async def list_teams(self) -> List[Dict[str, Any]]:
        """
        List all teams.
        
        Returns:
            A list of teams
        """
        return self.teams.get("teams", [])
    
    async def add_team_member(
        self, 
        team_id: str, 
        name: str, 
        email: str, 
        role: str
    ) -> Dict[str, Any]:
        """
        Add a member to a team.
        
        Args:
            team_id: The ID of the team
            name: The name of the member
            email: The email of the member
            role: The role of the member
            
        Returns:
            Updated team information
        """
        # Find the team
        team = None
        for t in self.teams.get("teams", []):
            if t["id"] == team_id:
                team = t
                break
        
        if not team:
            raise ValueError(f"Team with ID '{team_id}' not found")
        
        # Check if member already exists
        if any(member["email"] == email for member in team.get("members", [])):
            raise ValueError(f"Member with email '{email}' already exists in team '{team['name']}'")
        
        # Add member to team
        member = {
            "name": name,
            "email": email,
            "role": role,
            "added_at": datetime.now().isoformat()
        }
        
        team.setdefault("members", []).append(member)
        self._save_teams()
        
        logger.info(f"Added member {name} to team {team['name']}")
        return team
    
    async def configure_git_repository(
        self,
        repo_url: str,
        name: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        workspace_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Configure a Git repository for collaboration.
        
        Args:
            repo_url: The URL of the Git repository
            name: Optional name for the configuration
            username: Optional username for authentication
            token: Optional token for authentication
            workspace_path: Optional local workspace path
            
        Returns:
            Information about the configured repository
        """
        if "git" not in self.vcs_tools:
            raise ValueError("Git is not available on this system")
        
        # Create configuration
        config = {
            "id": str(len(self.vcs_configs.get("configurations", [])) + 1),
            "type": "git",
            "name": name or f"Git Repository {len(self.vcs_configs.get('configurations', [])) + 1}",
            "repo_url": repo_url,
            "username": username,
            "token_configured": bool(token),
            "workspace_path": workspace_path,
            "created_at": datetime.now().isoformat()
        }
        
        # Store token securely if provided
        if token:
            # In a real implementation, this would use a secure storage method
            # For now, we'll just indicate that a token is configured
            config["token_configured"] = True
        
        # Add configuration
        self.vcs_configs.setdefault("configurations", []).append(config)
        self._save_vcs_configs()
        
        logger.info(f"Configured Git repository: {repo_url}")
        return {k: v for k, v in config.items() if k != "token_configured"}
    
    async def list_vcs_configurations(self) -> List[Dict[str, Any]]:
        """
        List all version control system configurations.
        
        Returns:
            A list of VCS configurations
        """
        # Return configurations without sensitive information
        return [
            {k: v for k, v in config.items() if k != "token_configured"}
            for config in self.vcs_configs.get("configurations", [])
        ]
    
    async def clone_repository(
        self,
        config_id: str,
        target_path: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a repository using a configured VCS.
        
        Args:
            config_id: The ID of the VCS configuration
            target_path: Optional target path for the clone
            branch: Optional branch to clone
            
        Returns:
            Information about the cloned repository
        """
        # Find the configuration
        config = None
        for c in self.vcs_configs.get("configurations", []):
            if c["id"] == config_id:
                config = c
                break
        
        if not config:
            raise ValueError(f"VCS configuration with ID '{config_id}' not found")
        
        if config["type"] != "git":
            raise ValueError(f"Only Git repositories are supported for cloning at this time")
        
        # Determine target path
        clone_path = target_path or config.get("workspace_path")
        if not clone_path:
            raise ValueError("No target path specified for cloning")
        
        # Build clone command
        cmd = ["git", "clone"]
        
        if branch:
            cmd.extend(["--branch", branch])
        
        # Add repository URL
        repo_url = config["repo_url"]
        if config.get("username") and config.get("token_configured"):
            # In a real implementation, this would retrieve the token from secure storage
            # For now, we'll just use a placeholder
            repo_url = repo_url.replace("https://", f"https://{config['username']}:TOKEN@")
        
        cmd.append(repo_url)
        cmd.append(clone_path)
        
        # Execute clone command
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Failed to clone repository: {error_message}")
            
            logger.info(f"Cloned repository to {clone_path}")
            return {
                "config_id": config_id,
                "repo_url": config["repo_url"],
                "clone_path": clone_path,
                "branch": branch,
                "success": True,
                "output": stdout.decode() if stdout else ""
            }
        except (asyncio.SubprocessError, RuntimeError) as e:
            logger.error(f"Failed to clone repository: {e}")
            return {
                "config_id": config_id,
                "repo_url": config["repo_url"],
                "clone_path": clone_path,
                "branch": branch,
                "success": False,
                "error": str(e)
            }
    
    async def create_task(
        self,
        title: str,
        description: str,
        assignee: Optional[str] = None,
        project: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: str = "medium",
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new task.
        
        Args:
            title: The title of the task
            description: The description of the task
            assignee: Optional assignee for the task
            project: Optional project for the task
            due_date: Optional due date for the task (ISO format)
            priority: Optional priority for the task
            labels: Optional labels for the task
            
        Returns:
            Information about the created task
        """
        # Create new task
        task = {
            "id": str(len(self.task_tracking.get("tasks", [])) + 1),
            "title": title,
            "description": description,
            "status": "open",
            "assignee": assignee,
            "project": project,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "due_date": due_date,
            "priority": priority,
            "labels": labels or [],
            "comments": []
        }
        
        # Add task to tracking
        self.task_tracking.setdefault("tasks", []).append(task)
        self._save_task_tracking()
        
        logger.info(f"Created task: {title}")
        return task
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Optional status filter
            assignee: Optional assignee filter
            project: Optional project filter
            
        Returns:
            A list of tasks matching the filters
        """
        tasks = self.task_tracking.get("tasks", [])
        
        # Apply filters
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        if assignee:
            tasks = [task for task in tasks if task.get("assignee") == assignee]
        
        if project:
            tasks = [task for task in tasks if task.get("project") == project]
        
        return tasks
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a task.
        
        Args:
            task_id: The ID of the task
            status: The new status of the task
            comment: Optional comment about the status change
            
        Returns:
            Updated task information
        """
        # Find the task
        task = None
        for t in self.task_tracking.get("tasks", []):
            if t["id"] == task_id:
                task = t
                break
        
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")
        
        # Update task status
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        
        # Add comment if provided
        if comment:
            task.setdefault("comments", []).append({
                "text": comment,
                "created_at": datetime.now().isoformat(),
                "type": "status_change",
                "old_status": task.get("status"),
                "new_status": status
            })
        
        self._save_task_tracking()
        
        logger.info(f"Updated task {task_id} status to {status}")
        return task
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for collaboration management."""
        return [
            {
                "name": "create_team",
                "description": "Create a new team",
                "parameters": [
                    {
                        "name": "name",
                        "description": "The name of the team",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "Optional description of the team",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "members",
                        "description": "Optional list of team members with roles",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "role": {"type": "string"}
                            }
                        },
                        "required": False,
                    }
                ],
                "handler": self.tool_create_team,
            },
            {
                "name": "list_teams",
                "description": "List all teams",
                "parameters": [],
                "handler": self.tool_list_teams,
            },
            {
                "name": "add_team_member",
                "description": "Add a member to a team",
                "parameters": [
                    {
                        "name": "team_id",
                        "description": "The ID of the team",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "name",
                        "description": "The name of the member",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "email",
                        "description": "The email of the member",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "role",
                        "description": "The role of the member",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_add_team_member,
            },
            {
                "name": "configure_git_repository",
                "description": "Configure a Git repository for collaboration",
                "parameters": [
                    {
                        "name": "repo_url",
                        "description": "The URL of the Git repository",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "name",
                        "description": "Optional name for the configuration",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "username",
                        "description": "Optional username for authentication",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "token",
                        "description": "Optional token for authentication",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "workspace_path",
                        "description": "Optional local workspace path",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_configure_git_repository,
            },
            {
                "name": "list_vcs_configurations",
                "description": "List all version control system configurations",
                "parameters": [],
                "handler": self.tool_list_vcs_configurations,
            },
            {
                "name": "clone_repository",
                "description": "Clone a repository using a configured VCS",
                "parameters": [
                    {
                        "name": "config_id",
                        "description": "The ID of the VCS configuration",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "target_path",
                        "description": "Optional target path for the clone",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "branch",
                        "description": "Optional branch to clone",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_clone_repository,
            },
            {
                "name": "create_task",
                "description": "Create a new task",
                "parameters": [
                    {
                        "name": "title",
                        "description": "The title of the task",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "The description of the task",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "assignee",
                        "description": "Optional assignee for the task",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "project",
                        "description": "Optional project for the task",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "due_date",
                        "description": "Optional due date for the task (ISO format)",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "priority",
                        "description": "Optional priority for the task",
                        "type": "string",
                        "required": False,
                        "default": "medium",
                    },
                    {
                        "name": "labels",
                        "description": "Optional labels for the task",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": False,
                    }
                ],
                "handler": self.tool_create_task,
            },
            {
                "name": "list_tasks",
                "description": "List tasks with optional filtering",
                "parameters": [
                    {
                        "name": "status",
                        "description": "Optional status filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "assignee",
                        "description": "Optional assignee filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "project",
                        "description": "Optional project filter",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_list_tasks,
            },
            {
                "name": "update_task_status",
                "description": "Update the status of a task",
                "parameters": [
                    {
                        "name": "task_id",
                        "description": "The ID of the task",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "status",
                        "description": "The new status of the task",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "comment",
                        "description": "Optional comment about the status change",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_update_task_status,
            },
        ]
    
    async def tool_create_team(
        self, 
        name: str, 
        description: Optional[str] = None,
        members: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating a team."""
        try:
            team = await self.create_team(name, description, members)
            return {
                "team": team,
                "message": f"Created team '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_list_teams(self) -> Dict[str, Any]:
        """Tool handler for listing teams."""
        teams = await self.list_teams()
        return {"teams": teams}
    
    async def tool_add_team_member(
        self, 
        team_id: str, 
        name: str, 
        email: str, 
        role: str
    ) -> Dict[str, Any]:
        """Tool handler for adding a team member."""
        try:
            team = await self.add_team_member(team_id, name, email, role)
            return {
                "team": team,
                "message": f"Added member '{name}' to team"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_configure_git_repository(
        self,
        repo_url: str,
        name: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        workspace_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for configuring a Git repository."""
        try:
            config = await self.configure_git_repository(repo_url, name, username, token, workspace_path)
            return {
                "config": config,
                "message": f"Configured Git repository '{repo_url}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_list_vcs_configurations(self) -> Dict[str, Any]:
        """Tool handler for listing VCS configurations."""
        configs = await self.list_vcs_configurations()
        return {"configurations": configs}
    
    async def tool_clone_repository(
        self,
        config_id: str,
        target_path: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for cloning a repository."""
        result = await self.clone_repository(config_id, target_path, branch)
        if result.get("success"):
            return {
                "result": result,
                "message": f"Cloned repository to {result.get('clone_path')}"
            }
        else:
            return {
                "error": result.get("error", "Unknown error"),
                "result": result
            }
    
    async def tool_create_task(
        self,
        title: str,
        description: str,
        assignee: Optional[str] = None,
        project: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: str = "medium",
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating a task."""
        try:
            task = await self.create_task(title, description, assignee, project, due_date, priority, labels)
            return {
                "task": task,
                "message": f"Created task '{title}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_list_tasks(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        project: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for listing tasks."""
        tasks = await self.list_tasks(status, assignee, project)
        return {"tasks": tasks}
    
    async def tool_update_task_status(
        self,
        task_id: str,
        status: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for updating task status."""
        try:
            task = await self.update_task_status(task_id, status, comment)
            return {
                "task": task,
                "message": f"Updated task status to '{status}'"
            }
        except ValueError as e:
            return {"error": str(e)}
