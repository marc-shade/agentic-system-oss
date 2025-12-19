#!/usr/bin/env python3
"""
Post-Tool-Use Hook with VoiceMode Integration
Provides voice feedback after important operations complete
"""

import json
import sys
import os

# Add hooks directory to path
sys.path.append('/home/marc/.claude/hooks')

def main():
    """Main hook handler"""
    try:
        # Read hook input
        hook_input = json.loads(sys.stdin.read())
        
        tool_name = hook_input.get("tool", "")
        result = hook_input.get("result", {})
        success = not (isinstance(result, dict) and "error" in result)
        
        # Import voice integration
        from voicemode_integration import post_tool_notification, voice
        
        # Handle specific tool completions
        if tool_name == "Task":
            # Agent task completion
            if success:
                voice.announce_milestone('task_complete', "Agent finished")
            else:
                voice.announce_milestone('error', "Agent failed")
                
        elif tool_name == "Write":
            # File creation completion
            post_tool_notification("Write", success)
            
        elif tool_name == "MultiEdit":
            # Multiple edits completion
            post_tool_notification("MultiEdit", success)
            
        elif tool_name == "Bash":
            # Command execution completion
            # Only announce if it was significant or failed
            if not success:
                voice.announce_milestone('error', "Command failed")
            elif "install" in str(hook_input.get("arguments", {})).lower():
                voice.announce_milestone('success', "Installation complete")
            elif "test" in str(hook_input.get("arguments", {})).lower():
                if success:
                    voice.announce_milestone('success', "Tests passed")
                    
        elif tool_name == "TodoWrite":
            # Task list update - check for completed tasks
            todos = hook_input.get("arguments", {}).get("todos", [])
            completed = sum(1 for t in todos if t.get("status") == "completed")
            total = len(todos)
            
            # Announce when all tasks are done
            if completed == total and total > 0:
                voice.announce_milestone('success', "All tasks complete!")
            elif completed > 0:
                # Announce individual task completions
                remaining = total - completed
                if remaining == 1:
                    voice.speak("One task left", wait_for_response=False)
                elif remaining > 1 and remaining <= 3:
                    voice.speak(f"{remaining} tasks remaining", wait_for_response=False)
                    
        elif tool_name == "WebSearch":
            # Search completion
            if success:
                voice.announce_milestone('found', "search results")
                
        elif tool_name == "WebFetch":
            # Fetch completion
            post_tool_notification("WebFetch", success)
            
        elif tool_name.startswith("mcp__") and not success:
            # MCP tool failure - always announce
            service = tool_name.split("__")[1].split("_")[0]
            voice.announce_milestone('error', f"{service} failed")
            
        # Special milestone announcements based on patterns
        if success:
            result_str = str(result).lower()
            
            # File operations
            if "created" in result_str or "saved" in result_str:
                voice.announce_milestone('success', "File saved")
            elif "deleted" in result_str or "removed" in result_str:
                voice.announce_milestone('success', "Removed")
            elif "found" in result_str and tool_name in ["Grep", "Glob"]:
                voice.announce_milestone('found')
            elif "complete" in result_str or "finished" in result_str:
                voice.announce_milestone('task_complete')
                
    except Exception as e:
        # Silently fail - don't block execution
        pass
    
    # Always return success
    return json.dumps({"success": True})

if __name__ == "__main__":
    result = main()
    print(result)