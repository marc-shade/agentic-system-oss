import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

class IntegrationManager:
    """
    Manages external service integrations and API connections for the Software Planning MCP.
    Handles API configurations, authentication, request management, and service health monitoring.
    """
    
    def __init__(self):
        self.config_dir = Path(os.path.expanduser("~/.mcp/integrations"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.services_file = self.config_dir / "services.json"
        self.auth_file = self.config_dir / "auth.json"
        self.health_file = self.config_dir / "health.json"
        
        # Initialize configuration files
        self._initialize_config_files()
        
        # Load configurations
        self.services = self._load_services()
        self.auth_configs = self._load_auth_configs()
        self.health_checks = self._load_health_checks()
        
        # Initialize HTTP session
        self.session = None
    
    def _initialize_config_files(self):
        """Initialize configuration files with default values."""
        if not self.services_file.exists():
            with open(self.services_file, "w") as f:
                json.dump({"services": []}, f, indent=2)
        
        if not self.auth_file.exists():
            with open(self.auth_file, "w") as f:
                json.dump({"auth_configs": []}, f, indent=2)
        
        if not self.health_file.exists():
            with open(self.health_file, "w") as f:
                json.dump({"health_checks": []}, f, indent=2)
    
    def _load_services(self) -> Dict[str, Any]:
        """Load service configurations."""
        try:
            with open(self.services_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load services: {e}")
            return {"services": []}
    
    def _load_auth_configs(self) -> Dict[str, Any]:
        """Load authentication configurations."""
        try:
            with open(self.auth_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load auth configs: {e}")
            return {"auth_configs": []}
    
    def _load_health_checks(self) -> Dict[str, Any]:
        """Load health check data."""
        try:
            with open(self.health_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load health checks: {e}")
            return {"health_checks": []}
    
    def _save_services(self):
        """Save service configurations."""
        try:
            with open(self.services_file, "w") as f:
                json.dump(self.services, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save services: {e}")
    
    def _save_auth_configs(self):
        """Save authentication configurations."""
        try:
            with open(self.auth_file, "w") as f:
                json.dump(self.auth_configs, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save auth configs: {e}")
    
    def _save_health_checks(self):
        """Save health check data."""
        try:
            with open(self.health_file, "w") as f:
                json.dump(self.health_checks, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save health checks: {e}")
    
    async def _ensure_session(self):
        """Ensure aiohttp session is initialized."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def register_service(
        self,
        name: str,
        base_url: str,
        auth_type: str,
        auth_config: Dict[str, Any],
        endpoints: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new external service.
        
        Args:
            name: Service name
            base_url: Base URL of the service
            auth_type: Authentication type (e.g., 'basic', 'oauth2', 'api_key')
            auth_config: Authentication configuration
            endpoints: List of service endpoints
            description: Optional service description
            
        Returns:
            Service configuration
        """
        # Check if service already exists
        if any(s["name"] == name for s in self.services["services"]):
            raise ValueError(f"Service '{name}' already exists")
        
        # Create service configuration
        service = {
            "id": str(len(self.services["services"]) + 1),
            "name": name,
            "base_url": base_url,
            "auth_type": auth_type,
            "description": description or f"Integration with {name}",
            "endpoints": endpoints,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Store authentication configuration
        auth_entry = {
            "service_id": service["id"],
            "type": auth_type,
            "config": auth_config,
            "created_at": datetime.now().isoformat()
        }
        
        # Add configurations
        self.services["services"].append(service)
        self.auth_configs["auth_configs"].append(auth_entry)
        
        self._save_services()
        self._save_auth_configs()
        
        logger.info(f"Registered service: {name}")
        return service
    
    async def make_request(
        self,
        service_name: str,
        endpoint_name: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to a service endpoint.
        
        Args:
            service_name: Name of the service
            endpoint_name: Name of the endpoint
            method: HTTP method
            params: Optional query parameters
            data: Optional request body
            headers: Optional request headers
            
        Returns:
            Response from the service
        """
        await self._ensure_session()
        
        # Find service configuration
        service = None
        for s in self.services["services"]:
            if s["name"] == service_name:
                service = s
                break
        
        if not service:
            raise ValueError(f"Service '{service_name}' not found")
        
        # Find endpoint configuration
        endpoint = None
        for e in service["endpoints"]:
            if e["name"] == endpoint_name:
                endpoint = e
                break
        
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found in service '{service_name}'")
        
        # Get authentication configuration
        auth_config = None
        for a in self.auth_configs["auth_configs"]:
            if a["service_id"] == service["id"]:
                auth_config = a
                break
        
        if not auth_config:
            raise ValueError(f"Authentication configuration not found for service '{service_name}'")
        
        # Prepare request URL and headers
        url = f"{service['base_url']}{endpoint['path']}"
        request_headers = headers or {}
        
        # Add authentication headers
        if auth_config["type"] == "basic":
            # In a real implementation, credentials would be securely stored
            pass
        elif auth_config["type"] == "oauth2":
            # In a real implementation, this would handle token refresh
            request_headers["Authorization"] = f"Bearer {auth_config['config'].get('access_token')}"
        elif auth_config["type"] == "api_key":
            key_name = auth_config["config"].get("key_name", "X-API-Key")
            request_headers[key_name] = auth_config["config"].get("api_key")
        
        try:
            # Make the request
            async with getattr(self.session, method.lower())(
                url,
                params=params,
                json=data,
                headers=request_headers
            ) as response:
                response_data = await response.json()
                
                result = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": response_data
                }
                
                # Record health check
                await self._record_health_check(service["id"], endpoint["name"], result)
                
                return result
                
        except aiohttp.ClientError as e:
            error = {
                "error": str(e),
                "service": service_name,
                "endpoint": endpoint_name
            }
            
            # Record failed health check
            await self._record_health_check(
                service["id"],
                endpoint["name"],
                {"status_code": 0, "error": str(e)}
            )
            
            raise RuntimeError(f"Request failed: {str(e)}")
    
    async def _record_health_check(
        self,
        service_id: str,
        endpoint_name: str,
        result: Dict[str, Any]
    ):
        """Record a health check result."""
        health_check = {
            "timestamp": datetime.now().isoformat(),
            "service_id": service_id,
            "endpoint": endpoint_name,
            "status_code": result.get("status_code"),
            "error": result.get("error"),
            "response_time": result.get("response_time")
        }
        
        self.health_checks["health_checks"].append(health_check)
        
        # Keep only last 1000 health checks
        if len(self.health_checks["health_checks"]) > 1000:
            self.health_checks["health_checks"] = self.health_checks["health_checks"][-1000:]
        
        self._save_health_checks()
    
    async def get_service_health(
        self,
        service_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get health status for services.
        
        Args:
            service_name: Optional service name filter
            start_time: Optional start time in ISO format
            end_time: Optional end time in ISO format
            
        Returns:
            Health status information
        """
        health_checks = self.health_checks["health_checks"]
        
        # Apply time filters
        if start_time:
            health_checks = [h for h in health_checks if h["timestamp"] >= start_time]
        
        if end_time:
            health_checks = [h for h in health_checks if h["timestamp"] <= end_time]
        
        # Group by service
        service_health = {}
        for check in health_checks:
            service_id = check["service_id"]
            
            # Find service name
            service_name_found = None
            for service in self.services["services"]:
                if service["id"] == service_id:
                    service_name_found = service["name"]
                    break
            
            if service_name and service_name_found != service_name:
                continue
            
            if service_name_found not in service_health:
                service_health[service_name_found] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "endpoints": {}
                }
            
            stats = service_health[service_name_found]
            stats["total_requests"] += 1
            
            if check.get("status_code", 0) >= 200 and check.get("status_code", 0) < 300:
                stats["successful_requests"] += 1
            else:
                stats["failed_requests"] += 1
            
            # Track endpoint stats
            endpoint = check["endpoint"]
            if endpoint not in stats["endpoints"]:
                stats["endpoints"][endpoint] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0
                }
            
            endpoint_stats = stats["endpoints"][endpoint]
            endpoint_stats["total_requests"] += 1
            
            if check.get("status_code", 0) >= 200 and check.get("status_code", 0) < 300:
                endpoint_stats["successful_requests"] += 1
            else:
                endpoint_stats["failed_requests"] += 1
        
        return service_health
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for integration management."""
        return [
            {
                "name": "register_service",
                "description": "Register a new external service",
                "parameters": [
                    {
                        "name": "name",
                        "description": "Service name",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "base_url",
                        "description": "Base URL of the service",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "auth_type",
                        "description": "Authentication type",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "auth_config",
                        "description": "Authentication configuration",
                        "type": "object",
                        "required": True,
                    },
                    {
                        "name": "endpoints",
                        "description": "List of service endpoints",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "path": {"type": "string"},
                                "method": {"type": "string"}
                            }
                        },
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "Optional service description",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_register_service,
            },
            {
                "name": "make_request",
                "description": "Make a request to a service endpoint",
                "parameters": [
                    {
                        "name": "service_name",
                        "description": "Name of the service",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "endpoint_name",
                        "description": "Name of the endpoint",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "method",
                        "description": "HTTP method",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "params",
                        "description": "Optional query parameters",
                        "type": "object",
                        "required": False,
                    },
                    {
                        "name": "data",
                        "description": "Optional request body",
                        "type": "object",
                        "required": False,
                    },
                    {
                        "name": "headers",
                        "description": "Optional request headers",
                        "type": "object",
                        "required": False,
                    }
                ],
                "handler": self.tool_make_request,
            },
            {
                "name": "get_service_health",
                "description": "Get health status for services",
                "parameters": [
                    {
                        "name": "service_name",
                        "description": "Optional service name filter",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "start_time",
                        "description": "Optional start time in ISO format",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "end_time",
                        "description": "Optional end time in ISO format",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_get_service_health,
            },
        ]
    
    async def tool_register_service(
        self,
        name: str,
        base_url: str,
        auth_type: str,
        auth_config: Dict[str, Any],
        endpoints: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for registering a service."""
        try:
            service = await self.register_service(
                name, base_url, auth_type, auth_config, endpoints, description
            )
            return {
                "service": service,
                "message": f"Registered service '{name}'"
            }
        except ValueError as e:
            return {"error": str(e)}
    
    async def tool_make_request(
        self,
        service_name: str,
        endpoint_name: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for making a request."""
        try:
            result = await self.make_request(
                service_name, endpoint_name, method, params, data, headers
            )
            return {
                "result": result,
                "message": f"Request to {service_name}/{endpoint_name} completed"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_service_health(
        self,
        service_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for getting service health."""
        try:
            health = await self.get_service_health(service_name, start_time, end_time)
            return {"health": health}
        except Exception as e:
            return {"error": str(e)}
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None
