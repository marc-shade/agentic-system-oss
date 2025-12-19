#!/usr/bin/env python3
"""
Context Bundle Tracker Hook
Implements the video's context bundle pattern for 70% context recovery
"""

import os
import json
import datetime
from pathlib import Path

class ContextBundleTracker:
    def __init__(self):
        self.bundle_dir = Path("/home/marc/.claude/context-bundles")
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.bundle_path = self.bundle_dir / f"bundle_{self.session_id}.md"
        self.initialize_bundle()
    
    def initialize_bundle(self):
        """Initialize a new context bundle"""
        with open(self.bundle_path, 'w') as f:
            f.write(f"# Context Bundle - Session {self.session_id}\n")
            f.write(f"Started: {datetime.datetime.now().isoformat()}\n\n")
            f.write("## Operations Log\n\n")
    
    def track_operation(self, tool_name, tool_input, result=None):
        """Track important operations for context recovery"""
        # Only track operations that matter for context
        important_tools = ['Read', 'Write', 'Edit', 'Task', 'Grep', 'Glob']
        
        if tool_name not in important_tools:
            return
        
        with open(self.bundle_path, 'a') as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            if tool_name == 'Read':
                file_path = tool_input.get('file_path', '')
                f.write(f"[{timestamp}] READ: {file_path}\n")
            
            elif tool_name in ['Write', 'Edit']:
                file_path = tool_input.get('file_path', '')
                f.write(f"[{timestamp}] MODIFIED: {file_path}\n")
            
            elif tool_name == 'Task':
                subagent = tool_input.get('subagent_type', '')
                prompt_preview = tool_input.get('prompt', '')[:100]
                f.write(f"[{timestamp}] SPAWNED: {subagent}\n")
                f.write(f"  Purpose: {prompt_preview}...\n")
            
            elif tool_name in ['Grep', 'Glob']:
                pattern = tool_input.get('pattern', '') or tool_input.get('query', '')
                f.write(f"[{timestamp}] SEARCHED: {pattern}\n")
    
    def add_summary(self, summary):
        """Add a summary section to the bundle"""
        with open(self.bundle_path, 'a') as f:
            f.write(f"\n## Summary\n{summary}\n")
    
    def get_bundle_path(self):
        """Return the current bundle path"""
        return str(self.bundle_path)

# Global tracker instance
tracker = ContextBundleTracker()

def post_tool_use(tool_name, tool_input, result):
    """Hook called after each tool use"""
    tracker.track_operation(tool_name, tool_input, result)

def on_session_end():
    """Hook called when session ends"""
    tracker.add_summary("Session completed. Context bundle saved for recovery.")

# Export for hook system
__all__ = ['post_tool_use', 'on_session_end']