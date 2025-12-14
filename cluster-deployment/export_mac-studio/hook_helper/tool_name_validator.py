#!/usr/bin/env python3
"""
Tool Name Length Validator Hook
Prevents API errors from tool names exceeding 200 characters
"""
import sys
import json

def validate_tool_name(tool_name):
    """Check if tool name length is within API limits"""
    
    MAX_LENGTH = 200
    
    if len(tool_name) > MAX_LENGTH:
        # Try to create abbreviated version
        parts = tool_name.split("__")
        if len(parts) >= 3:
            # Format: mcp__server__function
            server = parts[1]
            function = parts[2]
            
            # Abbreviate server name if needed
            if len(server) > 30:
                server = server[:27] + "..."
            
            # Abbreviate function name if needed
            if len(function) > 50:
                function = function[:47] + "..."
            
            abbreviated = f"mcp__{server}__{function}"
            
            return False, abbreviated
        else:
            return False, None
    
    return True, None

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"allow": True}))
        return
    
    tool_name = sys.argv[1]
    
    is_valid, abbreviated = validate_tool_name(tool_name)
    
    if not is_valid:
        if abbreviated:
            response = {
                "allow": False,
                "message": f"⚠️ Tool name too long ({len(tool_name)} chars, max 200)\n" +
                          f"Suggested abbreviation: {abbreviated}",
                "suggested_tool": abbreviated
            }
        else:
            response = {
                "allow": False,
                "message": f"❌ Tool name too long ({len(tool_name)} chars, max 200)\n" +
                          "Please use a shorter tool name or abbreviation."
            }
    else:
        response = {"allow": True}
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()