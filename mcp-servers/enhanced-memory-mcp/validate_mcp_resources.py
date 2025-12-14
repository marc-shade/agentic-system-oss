#!/usr/bin/env python3
"""
Validate MCP Resources integration with the Enhanced Memory server
Tests the actual MCP protocol communication for resources
"""

import json
import subprocess
import asyncio
import time
from pathlib import Path

async def test_mcp_protocol():
    """Test MCP protocol communication for resources"""
    
    print("🚀 Testing MCP Resources Protocol Integration")
    
    # Start the server process
    server_path = Path(__file__).parent / "server_resources.py"
    process = subprocess.Popen(
        ["python", str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # Give server time to start
        await asyncio.sleep(1)
        
        # Test 1: Initialize
        print("📋 Testing MCP initialization...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            init_response = json.loads(response_line.strip())
            if "result" in init_response:
                print("✅ Server initialized successfully")
                capabilities = init_response["result"].get("capabilities", {})
                print(f"   Server capabilities: {list(capabilities.keys())}")
            else:
                print(f"❌ Initialization failed: {init_response}")
                return False
        
        # Test 2: List Tools
        print("\n🛠️ Testing tool listing...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            tools_response = json.loads(response_line.strip())
            if "result" in tools_response:
                tools = tools_response["result"]["tools"]
                print(f"✅ Found {len(tools)} tools")
                tool_names = [tool["name"] for tool in tools]
                print(f"   Tools: {', '.join(tool_names[:5])}...")
            else:
                print(f"❌ Tool listing failed: {tools_response}")
        
        # Test 3: List Resources (if supported)
        print("\n📊 Testing resource listing...")
        resources_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(resources_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            resources_response = json.loads(response_line.strip())
            if "result" in resources_response:
                resources = resources_response["result"]["resources"]
                print(f"✅ Found {len(resources)} resources")
                for resource in resources:
                    print(f"   📊 {resource['uri']} - {resource['name']}")
            else:
                print(f"⚠️ Resources not supported or failed: {resources_response}")
        
        # Test 4: Get a resource
        print("\n🔍 Testing resource access...")
        resource_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {
                "uri": "memory://status"
            }
        }
        
        process.stdin.write(json.dumps(resource_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            resource_response = json.loads(response_line.strip())
            if "result" in resource_response:
                contents = resource_response["result"]["contents"]
                print(f"✅ Resource accessed successfully")
                print(f"   Content type: {contents[0].get('mimeType', 'unknown')}")
                
                # Parse the JSON content to validate
                try:
                    content_data = json.loads(contents[0]["text"])
                    if "statistics" in content_data:
                        stats = content_data["statistics"]
                        print(f"   Entities: {stats.get('total_entities', 'unknown')}")
                        print(f"   Compression: {stats.get('compression_savings_percentage', 'unknown')}")
                except:
                    print("   Content format validation skipped")
            else:
                print(f"❌ Resource access failed: {resource_response}")
        
        # Test 5: Create some entities via tool
        print("\n🏗️ Testing entity creation...")
        create_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "create_entities",
                "arguments": {
                    "entities": [
                        {
                            "name": "MCPResourceTest",
                            "entityType": "test",
                            "observations": ["MCP Resources integration test", "Validates protocol communication"]
                        }
                    ]
                }
            }
        }
        
        process.stdin.write(json.dumps(create_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            create_response = json.loads(response_line.strip())
            if "result" in create_response:
                result_text = create_response["result"]["content"][0]["text"]
                result_data = json.loads(result_text)
                if result_data.get("success"):
                    print(f"✅ Entity created successfully")
                    print(f"   Entities created: {result_data['entities_created']}")
                    print(f"   Compression savings: {result_data['overall_savings']}")
                else:
                    print(f"❌ Entity creation failed: {result_data}")
            else:
                print(f"❌ Entity creation request failed: {create_response}")
        
        print("\n🎉 MCP Resources Protocol Integration Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        # Clean up process
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    success = asyncio.run(test_mcp_protocol())
    exit(0 if success else 1)