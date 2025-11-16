#!/usr/bin/env python3
"""
Context Compression Filter for MCP Memory System
Filters out TTS commands and verbose system logs from session context loading
"""

import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

class ContextCompressionFilter:
    """Filters and compresses context for session loading"""
    
    def __init__(self):
        self.tts_patterns = [
            r'say\s+-v\s+\w+\s+-r\s+\d+',  # say -v Moira -r 180
            r'speak_to_marc\(',  # Function calls
            r'subprocess\.run.*say.*',  # Subprocess TTS calls
            r'"?Orchestrator.*initialized"?',  # Auto-init messages
            r'"?communication protocol.*active"?',  # Protocol messages
            r'"?communication protocol.*operational"?',  # Protocol operational messages
        ]
        
        self.verbose_patterns = [
            r'update_visual_context\(',  # Visual updates
            r'osascript.*iTerm',  # iTerm background changes
            r'generate.*image.*prompt',  # Image generation logs
            r'MCP.*server.*operational',  # Server status messages
            r'AGI.*embodiment.*ready',  # AGI status messages
        ]
        
        self.system_noise_patterns = [
            r'Tool ran without output or errors',
            r'subprocess\.Popen',
            r'json\.dumps',
            r'Path\.home\(\)',
            r'with open.*as.*:',
        ]
    
    def should_filter_content(self, content: str) -> bool:
        """Check if content should be filtered out"""
        # Check for TTS commands
        for pattern in self.tts_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # Check for verbose system logs
        for pattern in self.verbose_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # Check for system noise
        for pattern in self.system_noise_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def compress_tool_call(self, tool_call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compress a tool call to essential information only"""
        if not isinstance(tool_call, dict):
            return tool_call
        
        # Filter out TTS and visual update tool calls completely
        if tool_call.get("name") == "Bash":
            command = tool_call.get("input", {}).get("command", "")
            if self.should_filter_content(command):
                return None  # Remove completely
        
        # Compress large outputs
        if "result" in tool_call and isinstance(tool_call["result"], str):
            result = tool_call["result"]
            if len(result) > 500:  # Large output
                # Extract key information only
                lines = result.split('\n')
                important_lines = []
                for line in lines:
                    if any(keyword in line.lower() for keyword in 
                          ['error', 'success', 'complete', 'found', 'created', 'failed']):
                        important_lines.append(line)
                
                if important_lines:
                    tool_call["result"] = f"[COMPRESSED] {' | '.join(important_lines[:3])}"
                else:
                    tool_call["result"] = "[COMPRESSED] Output available on request"
        
        return tool_call
    
    def compress_session_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compress a single session log entry"""
        if not isinstance(entry, dict):
            return entry
        
        # Keep summaries as-is
        if entry.get("type") == "summary":
            return entry
        
        # Filter user messages that are system noise
        if entry.get("type") == "user":
            content = entry.get("message", {}).get("content", "")
            if self.should_filter_content(content):
                return None
        
        # Compress assistant tool calls
        if entry.get("type") == "assistant":
            content = entry.get("content", [])
            if isinstance(content, list):
                filtered_content = []
                for item in content:
                    if item.get("type") == "tool_use":
                        compressed = self.compress_tool_call(item)
                        if compressed:  # Only add if not filtered out
                            filtered_content.append(compressed)
                    else:
                        filtered_content.append(item)
                
                if filtered_content:
                    entry["content"] = filtered_content
                    return entry
                else:
                    return None  # All content was filtered
        
        return entry
    
    def create_session_summary(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a compressed summary of session entries"""
        tool_counts = {}
        user_requests = []
        outcomes = []
        
        for entry in entries:
            if entry.get("type") == "user":
                content = entry.get("message", {}).get("content", "")
                if len(content) < 200 and not self.should_filter_content(content):
                    user_requests.append(content[:100])
            
            elif entry.get("type") == "assistant":
                content = entry.get("content", [])
                for item in content:
                    if item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        return {
            "type": "compressed_summary",
            "user_requests": user_requests[-3:],  # Last 3 requests
            "tool_usage": tool_counts,
            "total_entries": len(entries),
            "compression_note": "Full logs available via selective retrieval"
        }
    
    def filter_session_logs(self, session_data: List[Dict[str, Any]], 
                          max_entries: int = 20) -> List[Dict[str, Any]]:
        """Filter and compress session logs for context loading"""
        filtered_entries = []
        
        for entry in session_data:
            compressed = self.compress_session_entry(entry)
            if compressed:
                filtered_entries.append(compressed)
        
        # If still too many entries, create summary
        if len(filtered_entries) > max_entries:
            summary = self.create_session_summary(filtered_entries)
            return [summary] + filtered_entries[-5:]  # Summary + last 5 entries
        
        return filtered_entries

def test_compression_filter():
    """Test the compression filter with sample data"""
    filter_system = ContextCompressionFilter()
    
    # Test data that should be filtered
    test_entries = [
        {
            "type": "tool_use",
            "name": "Bash",
            "input": {"command": "say -v Moira -r 180 'System ready'"}
        },
        {
            "type": "tool_use", 
            "name": "Task",
            "result": "Found 50 files. Analysis complete. System operational."
        },
        {
            "type": "user",
            "message": {"content": "Analyze the codebase"}
        }
    ]
    
    print("Testing Context Compression Filter:")
    for i, entry in enumerate(test_entries):
        result = filter_system.compress_session_entry(entry)
        print(f"Entry {i}: {'FILTERED' if result is None else 'KEPT'}")
    
    print("\nFilter patterns loaded:", len(filter_system.tts_patterns))

if __name__ == "__main__":
    test_compression_filter()