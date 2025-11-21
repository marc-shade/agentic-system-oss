#!/usr/bin/env python3
"""
Test script to verify YouTube transcript MCP server functionality
"""

import json
import subprocess
import sys
from pathlib import Path

def test_mcp_server():
    """Test the MCP server with actual MCP protocol messages."""
    
    # Path to the server
    server_path = Path(__file__).parent / "server.py"
    python_path = "/Users/marc/Documents/Cline/MCP/.unified_environments/base_mcp/venv/bin/python"
    
    print("🔧 Testing YouTube Transcript MCP Server")
    print("=" * 50)
    
    # Test messages
    messages = [
        # Initialize
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        },
        # List tools
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        },
        # Call get_transcript tool
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_transcript",
                "arguments": {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                }
            }
        }
    ]
    
    try:
        # Start the server process
        proc = subprocess.Popen(
            [python_path, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(server_path.parent)
        )
        
        # Send messages and collect responses
        responses = []
        
        for i, message in enumerate(messages):
            print(f"\n📤 Sending message {i+1}: {message['method']}")
            
            # Send message
            message_str = json.dumps(message) + "\n"
            proc.stdin.write(message_str)
            proc.stdin.flush()
            
            # Read response
            try:
                response_line = proc.stdout.readline()
                if response_line.strip():
                    response = json.loads(response_line.strip())
                    responses.append(response)
                    
                    print(f"📥 Response {i+1}: Success")
                    if "result" in response:
                        if "tools" in response["result"]:
                            print(f"   Tools available: {len(response['result']['tools'])}")
                        elif "content" in response["result"]:
                            content = response["result"]["content"][0]["text"]
                            if len(content) > 200:
                                print(f"   Content: {content[:200]}...")
                            else:
                                print(f"   Content: {content}")
                        else:
                            print(f"   Result keys: {list(response['result'].keys())}")
                    elif "error" in response:
                        print(f"   Error: {response['error']}")
                        
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
            except Exception as e:
                print(f"   ❌ Error reading response: {e}")
        
        # Close the process
        proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        print(f"\n✅ Test completed - {len(responses)} successful responses")
        
        # Validate responses
        if len(responses) >= 2:
            tools_response = responses[1]
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                if any(tool["name"] == "get_transcript" for tool in tools):
                    print("✅ get_transcript tool is properly exposed")
                else:
                    print("❌ get_transcript tool not found in tools list")
            else:
                print("❌ Invalid tools/list response")
                
        if len(responses) >= 3:
            transcript_response = responses[2]
            if "result" in transcript_response:
                print("✅ get_transcript tool call succeeded")
            else:
                print("❌ get_transcript tool call failed")
                
        return len(responses) >= 2
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_claude_config():
    """Test Claude Desktop configuration"""
    print("\n🔧 Testing Claude Code settings configuration...")
    
    config_path = Path.home() / ".claude/settings.json"
    
    if not config_path.exists():
        print("❌ Claude Code settings file not found")
        return False
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        servers = config.get("mcpServers", {})
        if "youtube-transcript" in servers:
            server_config = servers["youtube-transcript"]
            expected_command = "/Users/marc/Documents/Cline/MCP/.unified_environments/base_mcp/venv/bin/python"
            expected_cwd = "/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp"
            
            if server_config.get("command") == expected_command:
                if server_config.get("cwd") == expected_cwd:
                    if "server.py" in server_config.get("args", []):
                        print("✅ YouTube Transcript MCP properly configured in Claude Code")
                        return True
                    else:
                        print("❌ YouTube Transcript MCP args incorrect in config")
                        return False
                else:
                    print("❌ YouTube Transcript MCP cwd incorrect in config")
                    return False
            else:
                print("❌ YouTube Transcript MCP command incorrect in config")  
                return False
        else:
            print("❌ YouTube Transcript MCP not found in Claude Code config")
            return False
    except Exception as e:
        print(f"❌ Error reading Claude Code config: {e}")
        return False

def main():
    """Main test function"""
    print("🐜 Ant-Worker-Execute: Testing YouTube Transcript MCP Integration")
    print("=" * 60)
    
    # Test MCP server functionality
    server_ok = test_mcp_server()
    
    # Test Claude Desktop configuration  
    config_ok = test_claude_config()
    
    print("\n" + "=" * 60)
    if server_ok and config_ok:
        print("🎉 SUCCESS: YouTube Transcript MCP is properly configured and working!")
        print("\nYou can now use: mcp__youtube-transcript-mcp__get_transcript")
        print("Example: mcp__youtube-transcript-mcp__get_transcript({ url: 'https://youtube.com/watch?v=VIDEO_ID' })")
        return True
    else:
        print("❌ FAILURE: YouTube Transcript MCP has issues that need to be resolved")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)