import os
import json
import asyncio
import socket
from typing import Dict, List, Any, Optional
import httpx
from loguru import logger
from pathlib import Path

class MCPService:
    """Represents a discovered MCP service."""
    
    def __init__(
        self,
        id: str,
        name: str,
        type: str,
        url: Optional[str] = None,
        version: Optional[str] = None,
        capabilities: List[str] = None,
        tools: List[Dict[str, Any]] = None,
        endpoints: Dict[str, str] = None,
        status: str = "unknown"
    ):
        self.id = id
        self.name = name
        self.type = type
        self.url = url
        self.version = version
        self.capabilities = capabilities or []
        self.tools = tools or []
        self.endpoints = endpoints or {}
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MCP service to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "endpoints": self.endpoints,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPService":
        """Create an MCP service from a dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            url=data.get("url"),
            version=data.get("version"),
            capabilities=data.get("capabilities", []),
            tools=data.get("tools", []),
            endpoints=data.get("endpoints", {}),
            status=data.get("status", "unknown"),
        )


class MCPDiscoveryService:
    """
    Service for discovering and integrating with other MCP servers.
    Scans for available MCP servers, catalogs their capabilities,
    and provides interfaces for leveraging their functionality.
    """
    
    def __init__(self):
        self.mcps: Dict[str, MCPService] = {}
        self.mcp_registry_path = Path(os.path.expanduser("~/.mcp/registry.json"))
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def discover(self) -> None:
        """
        Discover available MCP servers.
        This function combines multiple discovery methods to find all available MCPs.
        """
        logger.info("Starting MCP discovery process")
        
        # Create registry directory if it doesn't exist
        self.mcp_registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load previously discovered MCPs from registry
        await self._load_from_registry()
        
        # Run all discovery methods concurrently
        await asyncio.gather(
            self._discover_from_env_vars(),
            self._discover_from_local_directory(),
            self._discover_from_network(),
            self._discover_from_running_processes()
        )
        
        # Save discovered MCPs to registry
        await self._save_to_registry()
        
        logger.info(f"MCP discovery completed. Found {len(self.mcps)} MCP services.")
    
    async def _load_from_registry(self) -> None:
        """Load previously discovered MCPs from the registry file."""
        if not self.mcp_registry_path.exists():
            logger.debug("MCP registry file not found")
            return
        
        try:
            with open(self.mcp_registry_path, "r") as f:
                registry_data = json.load(f)
            
            for mcp_data in registry_data.get("mcps", []):
                mcp = MCPService.from_dict(mcp_data)
                self.mcps[mcp.id] = mcp
            
            logger.debug(f"Loaded {len(self.mcps)} MCPs from registry")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load MCP registry: {e}")
    
    async def _save_to_registry(self) -> None:
        """Save discovered MCPs to the registry file."""
        try:
            registry_data = {
                "version": "1.0",
                "mcps": [mcp.to_dict() for mcp in self.mcps.values()]
            }
            
            with open(self.mcp_registry_path, "w") as f:
                json.dump(registry_data, f, indent=2)
            
            logger.debug(f"Saved {len(self.mcps)} MCPs to registry")
        except IOError as e:
            logger.error(f"Failed to save MCP registry: {e}")
    
    async def _discover_from_env_vars(self) -> None:
        """Discover MCPs from environment variables."""
        mcp_urls = {}
        
        # Look for environment variables with MCP_URL pattern
        for key, value in os.environ.items():
            if key.startswith("MCP_") and key.endswith("_URL") and value:
                name = key[4:-4].lower()
                mcp_urls[name] = value
        
        # Look for MCP_REGISTRY environment variable
        if registry_urls := os.environ.get("MCP_REGISTRY", ""):
            for url in registry_urls.split(","):
                if url.strip():
                    try:
                        async with self.client.get(url.strip()) as response:
                            if response.status_code == 200:
                                registry = response.json()
                                for mcp_data in registry.get("mcps", []):
                                    name = mcp_data.get("name", "").lower()
                                    if name and "url" in mcp_data:
                                        mcp_urls[name] = mcp_data["url"]
                    except (httpx.HTTPError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to fetch MCP registry from {url}: {e}")
        
        # Add discovered MCPs
        for name, url in mcp_urls.items():
            mcp_id = f"env-{name}"
            if mcp_id not in self.mcps:
                self.mcps[mcp_id] = MCPService(
                    id=mcp_id,
                    name=name,
                    type="environment",
                    url=url,
                    status="discovered"
                )
                logger.debug(f"Discovered MCP from environment: {name} at {url}")
    
    async def _discover_from_local_directory(self) -> None:
        """Discover MCPs from local directories."""
        # Check common locations for MCP servers
        mcp_dirs = [
            Path(os.path.expanduser("~/MCP")),
            Path(os.path.expanduser("~/mcp")),
            Path(os.path.expanduser("~/mcps")),
            Path(os.path.expanduser("~/.mcp/servers")),
            Path("/usr/local/share/mcp"),
        ]
        
        for mcp_dir in mcp_dirs:
            if not mcp_dir.exists() or not mcp_dir.is_dir():
                continue
            
            for subdir in mcp_dir.iterdir():
                if not subdir.is_dir():
                    continue
                
                # Check for MCP manifest files
                manifest_paths = [
                    subdir / "mcp.json",
                    subdir / "manifest.json",
                    subdir / "mcp-manifest.json",
                ]
                
                for manifest_path in manifest_paths:
                    if manifest_path.exists():
                        try:
                            with open(manifest_path, "r") as f:
                                manifest = json.load(f)
                            
                            name = manifest.get("name", subdir.name)
                            mcp_id = f"local-{name}"
                            
                            self.mcps[mcp_id] = MCPService(
                                id=mcp_id,
                                name=name,
                                type="local",
                                url=manifest.get("url"),
                                version=manifest.get("version"),
                                capabilities=manifest.get("capabilities", []),
                                tools=manifest.get("tools", []),
                                endpoints=manifest.get("endpoints", {}),
                                status="installed"
                            )
                            
                            logger.debug(f"Discovered local MCP from manifest: {name}")
                            break
                        except (json.JSONDecodeError, IOError) as e:
                            logger.warning(f"Failed to load MCP manifest from {manifest_path}: {e}")
    
    async def _discover_from_network(self) -> None:
        """Discover MCPs from network discovery."""
        # For now, we'll just check some common local ports
        common_ports = [3000, 3001, 5000, 5001, 8000, 8001, 8080, 8081]
        local_ips = ["localhost", "127.0.0.1"]
        
        for ip in local_ips:
            for port in common_ports:
                url = f"http://{ip}:{port}/mcp/info"
                try:
                    async with self.client.get(url) as response:
                        if response.status_code == 200:
                            info = response.json()
                            if "name" in info:
                                name = info["name"]
                                mcp_id = f"network-{name}"
                                
                                self.mcps[mcp_id] = MCPService(
                                    id=mcp_id,
                                    name=name,
                                    type="network",
                                    url=f"http://{ip}:{port}",
                                    version=info.get("version"),
                                    capabilities=info.get("capabilities", []),
                                    tools=info.get("tools", []),
                                    endpoints=info.get("endpoints", {}),
                                    status="active"
                                )
                                
                                logger.debug(f"Discovered network MCP: {name} at {ip}:{port}")
                except httpx.HTTPError:
                    pass  # Ignore connection errors during discovery
    
    async def _discover_from_running_processes(self) -> None:
        """Discover MCPs from running processes."""
        try:
            import psutil
            
            # Look for process names containing "mcp" or "MCP"
            for process in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    process_info = process.info
                    name = process_info["name"].lower()
                    cmdline = process_info.get("cmdline", [])
                    
                    # Check if this looks like an MCP process
                    if "mcp" in name or any("mcp" in cmd.lower() for cmd in cmdline if cmd):
                        # Try to determine the MCP name and type
                        mcp_name = name.replace(".exe", "").replace("-", "_")
                        
                        # See if we can extract a port number from the command line
                        port = None
                        for i, arg in enumerate(cmdline):
                            if arg in ["-p", "--port", "-port", "port"] and i + 1 < len(cmdline):
                                try:
                                    port = int(cmdline[i + 1])
                                    break
                                except ValueError:
                                    pass
                        
                        # Create an MCP service entry
                        mcp_id = f"process-{process_info['pid']}-{mcp_name}"
                        
                        # Only add if not already discovered by another method
                        if mcp_id not in self.mcps:
                            url = f"http://localhost:{port}" if port else None
                            
                            self.mcps[mcp_id] = MCPService(
                                id=mcp_id,
                                name=mcp_name,
                                type="process",
                                url=url,
                                status="running"
                            )
                            
                            logger.debug(f"Discovered MCP from process: {mcp_name} (PID: {process_info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            logger.warning("psutil not available, skipping process discovery")
    
    async def get_mcp_info(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific MCP."""
        if mcp_id not in self.mcps:
            return None
        
        mcp = self.mcps[mcp_id]
        
        # If the MCP has a URL, try to fetch more information
        if mcp.url and mcp.status != "error":
            try:
                info_url = f"{mcp.url}/mcp/info"
                async with self.client.get(info_url) as response:
                    if response.status_code == 200:
                        info = response.json()
                        
                        # Update the MCP with the fetched information
                        mcp.version = info.get("version", mcp.version)
                        mcp.capabilities = info.get("capabilities", mcp.capabilities)
                        mcp.tools = info.get("tools", mcp.tools)
                        mcp.endpoints = info.get("endpoints", mcp.endpoints)
                        mcp.status = "active"
                        
                        logger.debug(f"Updated information for MCP {mcp_id}")
                    else:
                        logger.warning(f"Failed to get information for MCP {mcp_id}: HTTP {response.status_code}")
                        mcp.status = "error"
            except httpx.HTTPError as e:
                logger.warning(f"Failed to get information for MCP {mcp_id}: {e}")
                mcp.status = "error"
        
        return mcp.to_dict()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for MCP discovery and integration."""
        return [
            {
                "name": "list_mcps",
                "description": "List all discovered MCP servers",
                "parameters": [],
                "handler": self.tool_list_mcps,
            },
            {
                "name": "get_mcp_info",
                "description": "Get detailed information about a specific MCP server",
                "parameters": [
                    {
                        "name": "mcp_id",
                        "description": "ID of the MCP server",
                        "type": "string",
                        "required": True,
                    }
                ],
                "handler": self.tool_get_mcp_info,
            },
            {
                "name": "refresh_mcps",
                "description": "Rediscover all MCP servers",
                "parameters": [],
                "handler": self.tool_refresh_mcps,
            },
        ]
    
    async def tool_list_mcps(self) -> Dict[str, Any]:
        """Tool handler for listing all discovered MCPs."""
        return {
            "mcps": [mcp.to_dict() for mcp in self.mcps.values()]
        }
    
    async def tool_get_mcp_info(self, mcp_id: str) -> Dict[str, Any]:
        """Tool handler for getting detailed information about a specific MCP."""
        info = await self.get_mcp_info(mcp_id)
        if info:
            return {"info": info}
        return {"error": f"MCP with ID {mcp_id} not found"}
    
    async def tool_refresh_mcps(self) -> Dict[str, Any]:
        """Tool handler for rediscovering all MCPs."""
        await self.discover()
        return {
            "message": f"Discovered {len(self.mcps)} MCP servers",
            "mcps": [mcp.to_dict() for mcp in self.mcps.values()]
        }
