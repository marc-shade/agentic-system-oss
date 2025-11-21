#!/usr/bin/env python
import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, List

async def test_notification_manager():
    """Test the notification manager server."""
    print("\n=== Testing Notification Manager ===")
    
    # Start the notification manager server process
    process = subprocess.Popen(
        ["python", "src/core/notification_manager_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd="/Users/marc/Documents/Cline/MCP/software-planning-mcp"
    )
    
    # Send a test notification
    request = {
        "id": "test1",
        "method": "tool_send_notification",
        "params": {
            "message": "Test notification",
            "notification_type": "info",
            "priority": "medium",
            "topic": "test"
        }
    }
    
    # Write the request to stdin
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # Read the response from stdout
    response = process.stdout.readline()
    print(f"Notification Response: {response}")
    
    # Get notifications
    request = {
        "id": "test2",
        "method": "tool_get_notifications",
        "params": {
            "limit": 10
        }
    }
    
    # Write the request to stdin
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # Read the response from stdout
    response = process.stdout.readline()
    print(f"Get Notifications Response: {response}")
    
    # Clean up
    process.terminate()
    process.wait()
    print("Notification Manager test completed")

async def test_configuration_manager():
    """Test the configuration manager server."""
    print("\n=== Testing Configuration Manager ===")
    
    # Start the configuration manager server process
    process = subprocess.Popen(
        ["python", "src/core/configuration_manager_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd="/Users/marc/Documents/Cline/MCP/software-planning-mcp"
    )
    
    # Set a test configuration
    request = {
        "id": "test1",
        "method": "tool_set_config",
        "params": {
            "key": "test.setting",
            "value": "test_value"
        }
    }
    
    # Write the request to stdin
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # Read the response from stdout
    response = process.stdout.readline()
    print(f"Set Config Response: {response}")
    
    # Get the configuration
    request = {
        "id": "test2",
        "method": "tool_get_config",
        "params": {
            "key": "test.setting"
        }
    }
    
    # Write the request to stdin
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # Read the response from stdout
    response = process.stdout.readline()
    print(f"Get Config Response: {response}")
    
    # Clean up
    process.terminate()
    process.wait()
    print("Configuration Manager test completed")

async def main():
    """Run all tests."""
    print("Starting MCP server tests...")
    
    # Test notification manager
    await test_notification_manager()
    
    # Test configuration manager
    await test_configuration_manager()
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
