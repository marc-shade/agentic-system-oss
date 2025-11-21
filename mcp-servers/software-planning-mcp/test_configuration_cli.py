#!/usr/bin/env python
import asyncio
from src.core.configuration_manager import ConfigurationManager

async def test():
    manager = ConfigurationManager()
    try:
        # Set some configuration values
        await manager.set("system.log_level", "DEBUG")
        await manager.set("app.name", "Software Planning MCP")
        
        # Set a default value
        await manager.set_default("security.token_expiry", "3600")
        
        # Set an override value
        await manager.set_override("system.environment", "development")
        
        # Get configuration values
        logging_level = manager.get("system.log_level")
        app_name = manager.get("app.name")
        token_expiry = manager.get("security.token_expiry")
        environment = manager.get("system.environment")
        
        # Print the configuration values
        print(f"system.log_level: {logging_level}")
        print(f"app.name: {app_name}")
        print(f"security.token_expiry: {token_expiry}")
        print(f"system.environment: {environment}")
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
