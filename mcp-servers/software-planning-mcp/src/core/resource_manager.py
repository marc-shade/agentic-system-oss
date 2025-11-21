import os
import json
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from loguru import logger

class ResourceManager:
    """
    Manages resources for the Software Planning MCP.
    Handles file system operations, database management, external services integration,
    and library/package management.
    """
    
    def __init__(self):
        self.workspace_dir = Path(os.path.expanduser("~/.mcp/workspaces"))
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.current_workspace: Optional[str] = None
        self.external_services: Dict[str, Dict[str, Any]] = {}
        self.package_managers = self._discover_package_managers()
    
    def _discover_package_managers(self) -> Dict[str, Dict[str, Any]]:
        """Discover available package managers."""
        package_managers = {}
        
        # Check for common package managers
        managers = [
            {
                "name": "pip",
                "command": "pip",
                "language": "python",
                "install_cmd": ["pip", "install"],
                "uninstall_cmd": ["pip", "uninstall"],
                "list_cmd": ["pip", "list", "--format=json"]
            },
            {
                "name": "npm",
                "command": "npm",
                "language": "javascript",
                "install_cmd": ["npm", "install"],
                "uninstall_cmd": ["npm", "uninstall"],
                "list_cmd": ["npm", "list", "--json"]
            },
            {
                "name": "yarn",
                "command": "yarn",
                "language": "javascript",
                "install_cmd": ["yarn", "add"],
                "uninstall_cmd": ["yarn", "remove"],
                "list_cmd": ["yarn", "list", "--json"]
            },
            {
                "name": "cargo",
                "command": "cargo",
                "language": "rust",
                "install_cmd": ["cargo", "add"],
                "uninstall_cmd": ["cargo", "remove"],
                "list_cmd": ["cargo", "metadata", "--format-version=1"]
            },
            {
                "name": "composer",
                "command": "composer",
                "language": "php",
                "install_cmd": ["composer", "require"],
                "uninstall_cmd": ["composer", "remove"],
                "list_cmd": ["composer", "show", "--format=json"]
            },
        ]
        
        for manager in managers:
            if self._is_executable_available(manager["command"]):
                package_managers[manager["name"]] = {
                    "command": manager["command"],
                    "language": manager["language"],
                    "install_cmd": manager["install_cmd"],
                    "uninstall_cmd": manager["uninstall_cmd"],
                    "list_cmd": manager["list_cmd"],
                    "available": True
                }
                logger.debug(f"Discovered package manager: {manager['name']}")
        
        return package_managers
    
    def _is_executable_available(self, name: str) -> bool:
        """Check if an executable is available in the system PATH."""
        from shutil import which
        return which(name) is not None
    
    async def create_workspace(self, name: str, description: Optional[str] = None) -> str:
        """
        Create a new workspace.
        
        Args:
            name: The name of the workspace
            description: Optional description of the workspace
            
        Returns:
            The path to the created workspace
        """
        workspace_path = self.workspace_dir / name
        if workspace_path.exists():
            raise ValueError(f"Workspace '{name}' already exists")
        
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Create workspace metadata file
        metadata = {
            "name": name,
            "description": description or f"Workspace for {name}",
            "created_at": str(datetime.now().isoformat()),
            "files": [],
            "databases": [],
            "services": [],
            "packages": []
        }
        
        with open(workspace_path / "workspace.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Created workspace: {name} at {workspace_path}")
        return str(workspace_path)
    
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List all available workspaces.
        
        Returns:
            A list of workspace information
        """
        workspaces = []
        
        for workspace_dir in self.workspace_dir.iterdir():
            if workspace_dir.is_dir():
                metadata_file = workspace_dir / "workspace.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                        
                        workspaces.append({
                            "name": metadata.get("name", workspace_dir.name),
                            "description": metadata.get("description", ""),
                            "path": str(workspace_dir),
                            "created_at": metadata.get("created_at", "")
                        })
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Failed to load workspace metadata from {metadata_file}: {e}")
                else:
                    # Basic info for workspaces without metadata
                    workspaces.append({
                        "name": workspace_dir.name,
                        "description": "",
                        "path": str(workspace_dir),
                        "created_at": ""
                    })
        
        return workspaces
    
    async def set_current_workspace(self, name: str) -> Dict[str, Any]:
        """
        Set the current workspace.
        
        Args:
            name: The name of the workspace
            
        Returns:
            Information about the workspace
        """
        workspace_path = self.workspace_dir / name
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{name}' does not exist")
        
        self.current_workspace = name
        
        # Load workspace metadata
        metadata_file = workspace_path / "workspace.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load workspace metadata from {metadata_file}: {e}")
                metadata = {
                    "name": name,
                    "description": f"Workspace for {name}",
                    "files": [],
                    "databases": [],
                    "services": [],
                    "packages": []
                }
        else:
            metadata = {
                "name": name,
                "description": f"Workspace for {name}",
                "files": [],
                "databases": [],
                "services": [],
                "packages": []
            }
        
        logger.info(f"Set current workspace to: {name}")
        return {
            "name": metadata.get("name", name),
            "description": metadata.get("description", ""),
            "path": str(workspace_path),
            "created_at": metadata.get("created_at", ""),
            "files": metadata.get("files", []),
            "databases": metadata.get("databases", []),
            "services": metadata.get("services", []),
            "packages": metadata.get("packages", [])
        }
    
    async def create_file(
        self, 
        path: str, 
        content: str, 
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a file in a workspace.
        
        Args:
            path: The path to the file (relative to the workspace)
            content: The content of the file
            workspace: Optional workspace name (uses current workspace if not specified)
            
        Returns:
            Information about the created file
        """
        workspace_name = workspace or self.current_workspace
        if not workspace_name:
            raise ValueError("No workspace specified and no current workspace set")
        
        workspace_path = self.workspace_dir / workspace_name
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' does not exist")
        
        file_path = workspace_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w") as f:
            f.write(content)
        
        # Update workspace metadata
        metadata_file = workspace_path / "workspace.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                
                # Add file to metadata if not already present
                if path not in [file_info.get("path") for file_info in metadata.get("files", [])]:
                    metadata.setdefault("files", []).append({
                        "path": path,
                        "size": os.path.getsize(file_path),
                        "created_at": str(datetime.now().isoformat())
                    })
                
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update workspace metadata: {e}")
        
        logger.info(f"Created file: {path} in workspace {workspace_name}")
        return {
            "path": path,
            "absolute_path": str(file_path),
            "size": os.path.getsize(file_path),
            "workspace": workspace_name
        }
    
    async def read_file(
        self, 
        path: str, 
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read a file from a workspace.
        
        Args:
            path: The path to the file (relative to the workspace)
            workspace: Optional workspace name (uses current workspace if not specified)
            
        Returns:
            The content of the file
        """
        workspace_name = workspace or self.current_workspace
        if not workspace_name:
            raise ValueError("No workspace specified and no current workspace set")
        
        workspace_path = self.workspace_dir / workspace_name
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' does not exist")
        
        file_path = workspace_path / path
        if not file_path.exists():
            raise ValueError(f"File '{path}' does not exist in workspace '{workspace_name}'")
        
        with open(file_path, "r") as f:
            content = f.read()
        
        return {
            "path": path,
            "absolute_path": str(file_path),
            "size": os.path.getsize(file_path),
            "content": content,
            "workspace": workspace_name
        }
    
    async def list_files(
        self, 
        directory: str = "", 
        workspace: Optional[str] = None,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        List files in a workspace directory.
        
        Args:
            directory: The directory to list (relative to the workspace)
            workspace: Optional workspace name (uses current workspace if not specified)
            recursive: Whether to list files recursively
            
        Returns:
            A list of files in the directory
        """
        workspace_name = workspace or self.current_workspace
        if not workspace_name:
            raise ValueError("No workspace specified and no current workspace set")
        
        workspace_path = self.workspace_dir / workspace_name
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' does not exist")
        
        dir_path = workspace_path / directory
        if not dir_path.exists():
            raise ValueError(f"Directory '{directory}' does not exist in workspace '{workspace_name}'")
        
        files = []
        directories = []
        
        if recursive:
            # Recursive listing
            for root, dirs, filenames in os.walk(dir_path):
                rel_root = os.path.relpath(root, workspace_path)
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    directories.append({
                        "name": dir_name,
                        "path": os.path.join(rel_root, dir_name),
                        "type": "directory"
                    })
                
                for filename in filenames:
                    file_path = Path(root) / filename
                    files.append({
                        "name": filename,
                        "path": os.path.join(rel_root, filename),
                        "size": os.path.getsize(file_path),
                        "type": "file"
                    })
        else:
            # Non-recursive listing
            for item in dir_path.iterdir():
                rel_path = os.path.relpath(item, workspace_path)
                if item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": rel_path,
                        "type": "directory"
                    })
                else:
                    files.append({
                        "name": item.name,
                        "path": rel_path,
                        "size": os.path.getsize(item),
                        "type": "file"
                    })
        
        return {
            "directory": directory,
            "workspace": workspace_name,
            "files": files,
            "directories": directories
        }
    
    async def install_package(
        self,
        package_name: str,
        version: Optional[str] = None,
        package_manager: Optional[str] = None,
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Install a package in a workspace.
        
        Args:
            package_name: The name of the package to install
            version: Optional version of the package
            package_manager: Optional package manager to use
            workspace: Optional workspace name (uses current workspace if not specified)
            
        Returns:
            Information about the installed package
        """
        workspace_name = workspace or self.current_workspace
        if not workspace_name:
            raise ValueError("No workspace specified and no current workspace set")
        
        workspace_path = self.workspace_dir / workspace_name
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' does not exist")
        
        # Determine package manager to use
        if not package_manager:
            # Try to infer from workspace files
            if (workspace_path / "requirements.txt").exists():
                package_manager = "pip"
            elif (workspace_path / "package.json").exists():
                if (workspace_path / "yarn.lock").exists():
                    package_manager = "yarn"
                else:
                    package_manager = "npm"
            elif (workspace_path / "Cargo.toml").exists():
                package_manager = "cargo"
            elif (workspace_path / "composer.json").exists():
                package_manager = "composer"
            else:
                # Default to pip if can't determine
                package_manager = "pip"
        
        if package_manager not in self.package_managers:
            raise ValueError(f"Package manager '{package_manager}' not available")
        
        manager_info = self.package_managers[package_manager]
        
        # Build install command
        install_cmd = list(manager_info["install_cmd"])
        if version and package_manager == "pip":
            install_cmd.append(f"{package_name}=={version}")
        elif version:
            install_cmd.append(f"{package_name}@{version}")
        else:
            install_cmd.append(package_name)
        
        # Run install command
        process = await asyncio.create_subprocess_exec(
            *install_cmd,
            cwd=str(workspace_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Failed to install package '{package_name}': {error_message}")
        
        # Update workspace metadata
        metadata_file = workspace_path / "workspace.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                
                # Add package to metadata if not already present
                package_info = {
                    "name": package_name,
                    "version": version or "latest",
                    "manager": package_manager,
                    "installed_at": str(datetime.now().isoformat())
                }
                
                # Check if package already exists and update it
                packages = metadata.get("packages", [])
                for i, pkg in enumerate(packages):
                    if pkg.get("name") == package_name and pkg.get("manager") == package_manager:
                        packages[i] = package_info
                        break
                else:
                    # Package not found, add it
                    packages.append(package_info)
                
                metadata["packages"] = packages
                
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update workspace metadata: {e}")
        
        logger.info(f"Installed package: {package_name} in workspace {workspace_name}")
        return {
            "package": package_name,
            "version": version or "latest",
            "manager": package_manager,
            "workspace": workspace_name,
            "output": stdout.decode() if stdout else ""
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for resource management."""
        return [
            {
                "name": "create_workspace",
                "description": "Create a new workspace",
                "parameters": [
                    {
                        "name": "name",
                        "description": "The name of the workspace",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "Optional description of the workspace",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_create_workspace,
            },
            {
                "name": "list_workspaces",
                "description": "List all available workspaces",
                "parameters": [],
                "handler": self.tool_list_workspaces,
            },
            {
                "name": "set_current_workspace",
                "description": "Set the current workspace",
                "parameters": [
                    {
                        "name": "name",
                        "description": "The name of the workspace",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_set_current_workspace,
            },
            {
                "name": "create_file",
                "description": "Create a file in a workspace",
                "parameters": [
                    {
                        "name": "path",
                        "description": "The path to the file (relative to the workspace)",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "content",
                        "description": "The content of the file",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "workspace",
                        "description": "Optional workspace name (uses current workspace if not specified)",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_create_file,
            },
            {
                "name": "read_file",
                "description": "Read a file from a workspace",
                "parameters": [
                    {
                        "name": "path",
                        "description": "The path to the file (relative to the workspace)",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "workspace",
                        "description": "Optional workspace name (uses current workspace if not specified)",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_read_file,
            },
            {
                "name": "list_files",
                "description": "List files in a workspace directory",
                "parameters": [
                    {
                        "name": "directory",
                        "description": "The directory to list (relative to the workspace)",
                        "type": "string",
                        "required": False,
                        "default": "",
                    },
                    {
                        "name": "workspace",
                        "description": "Optional workspace name (uses current workspace if not specified)",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "recursive",
                        "description": "Whether to list files recursively",
                        "type": "boolean",
                        "required": False,
                        "default": False,
                    }
                ],
                "handler": self.tool_list_files,
            },
            {
                "name": "install_package",
                "description": "Install a package in a workspace",
                "parameters": [
                    {
                        "name": "package_name",
                        "description": "The name of the package to install",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "version",
                        "description": "Optional version of the package",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "package_manager",
                        "description": "Optional package manager to use",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "workspace",
                        "description": "Optional workspace name (uses current workspace if not specified)",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_install_package,
            },
        ]
    
    async def tool_create_workspace(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Tool handler for creating a workspace."""
        try:
            workspace_path = await self.create_workspace(name, description)
            return {
                "workspace": name,
                "path": workspace_path,
                "message": f"Created workspace '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_list_workspaces(self) -> Dict[str, Any]:
        """Tool handler for listing workspaces."""
        workspaces = await self.list_workspaces()
        return {"workspaces": workspaces}
    
    async def tool_set_current_workspace(self, name: str) -> Dict[str, Any]:
        """Tool handler for setting the current workspace."""
        try:
            workspace_info = await self.set_current_workspace(name)
            return {
                "workspace": name,
                "info": workspace_info,
                "message": f"Set current workspace to '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_create_file(
        self, path: str, content: str, workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for creating a file."""
        try:
            file_info = await self.create_file(path, content, workspace)
            return {
                "file": path,
                "info": file_info,
                "message": f"Created file '{path}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_read_file(
        self, path: str, workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for reading a file."""
        try:
            file_info = await self.read_file(path, workspace)
            return {
                "file": path,
                "content": file_info["content"],
                "info": {k: v for k, v in file_info.items() if k != "content"}
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_list_files(
        self, directory: str = "", workspace: Optional[str] = None, recursive: bool = False
    ) -> Dict[str, Any]:
        """Tool handler for listing files."""
        try:
            file_list = await self.list_files(directory, workspace, recursive)
            return file_list
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_install_package(
        self, package_name: str, version: Optional[str] = None, 
        package_manager: Optional[str] = None, workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for installing a package."""
        try:
            package_info = await self.install_package(package_name, version, package_manager, workspace)
            return {
                "package": package_name,
                "info": package_info,
                "message": f"Installed package '{package_name}'"
            }
        except (ValueError, RuntimeError) as e:
            return {"error": str(e)}
