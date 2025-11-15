#!/usr/bin/env python3
"""
Compressed Context Integration for Enhanced Memory MCP
Integrates the context compression filter into the memory system
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from context_compression_filter import ContextCompressionFilter

logger = logging.getLogger("compressed-context")

class CompressedContextManager:
    """Manages compressed context loading for enhanced memory system"""
    
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.filter = ContextCompressionFilter()
        self.compression_enabled = True
        
    def enable_compression(self, enabled: bool = True):
        """Enable or disable context compression"""
        self.compression_enabled = enabled
        logger.info(f"Context compression {'enabled' if enabled else 'disabled'}")
    
    def load_compressed_session_context(self, session_id: Optional[str] = None, 
                                      max_entries: int = 15) -> Dict[str, Any]:
        """Load session context with compression applied"""
        if not self.compression_enabled:
            return self._load_raw_context(session_id)
        
        try:
            # Look for Claude session logs
            claude_dir = Path.home() / ".claude" / "projects"
            if not claude_dir.exists():
                return {"status": "no_session_data", "entries": []}
            
            # Find most recent session or specific session
            session_files = list(claude_dir.glob("*.jsonl"))
            if not session_files:
                return {"status": "no_session_files", "entries": []}
            
            # Use most recent if no specific session requested
            if session_id:
                target_file = claude_dir / f"{session_id}.jsonl"
                if not target_file.exists():
                    return {"status": "session_not_found", "entries": []}
            else:
                target_file = max(session_files, key=lambda f: f.stat().st_mtime)
            
            # Load and filter session data
            session_entries = []
            with open(target_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        session_entries.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            # Apply compression filter
            filtered_entries = self.filter.filter_session_logs(session_entries, max_entries)
            
            return {
                "status": "compressed",
                "session_file": str(target_file.name),
                "original_entries": len(session_entries),
                "compressed_entries": len(filtered_entries),
                "compression_ratio": f"{len(filtered_entries)/len(session_entries)*100:.1f}%",
                "entries": filtered_entries
            }
            
        except Exception as e:
            logger.error(f"Error loading compressed context: {e}")
            return {"status": "error", "error": str(e), "entries": []}
    
    def _load_raw_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Load raw context without compression (fallback)"""
        return {
            "status": "raw_mode", 
            "note": "Compression disabled - raw logs would be loaded",
            "entries": []
        }
    
    def get_selective_raw_logs(self, session_id: str, entry_types: List[str] = None,
                             tool_names: List[str] = None) -> Dict[str, Any]:
        """Retrieve specific raw log entries for detailed analysis"""
        try:
            claude_dir = Path.home() / ".claude" / "projects"
            target_file = claude_dir / f"{session_id}.jsonl"
            
            if not target_file.exists():
                return {"status": "not_found", "entries": []}
            
            filtered_entries = []
            with open(target_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Filter by entry type
                        if entry_types and entry.get("type") not in entry_types:
                            continue
                        
                        # Filter by tool name
                        if tool_names:
                            if entry.get("type") == "tool_use":
                                if entry.get("name") not in tool_names:
                                    continue
                            elif entry.get("type") == "assistant":
                                content = entry.get("content", [])
                                has_matching_tool = False
                                for item in content:
                                    if (item.get("type") == "tool_use" and 
                                        item.get("name") in tool_names):
                                        has_matching_tool = True
                                        break
                                if not has_matching_tool:
                                    continue
                        
                        filtered_entries.append(entry)
                        
                    except json.JSONDecodeError:
                        continue
            
            return {
                "status": "success",
                "session_id": session_id,
                "filters": {
                    "entry_types": entry_types,
                    "tool_names": tool_names
                },
                "entries": filtered_entries
            }
            
        except Exception as e:
            logger.error(f"Error retrieving selective logs: {e}")
            return {"status": "error", "error": str(e)}
    
    def create_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Create a high-level summary of session context"""
        try:
            claude_dir = Path.home() / ".claude" / "projects" 
            target_file = claude_dir / f"{session_id}.jsonl"
            
            if not target_file.exists():
                return {"status": "not_found"}
            
            # Analyze session
            stats = {
                "total_entries": 0,
                "user_messages": 0,
                "assistant_responses": 0,
                "tool_calls": {},
                "session_duration": None,
                "key_topics": [],
                "errors": 0
            }
            
            first_timestamp = None
            last_timestamp = None
            
            with open(target_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        stats["total_entries"] += 1
                        
                        # Track timestamps
                        if "timestamp" in entry:
                            timestamp = entry["timestamp"]
                            if not first_timestamp:
                                first_timestamp = timestamp
                            last_timestamp = timestamp
                        
                        # Count entry types
                        entry_type = entry.get("type", "unknown")
                        if entry_type == "user":
                            stats["user_messages"] += 1
                        elif entry_type == "assistant":
                            stats["assistant_responses"] += 1
                            
                            # Count tool calls
                            content = entry.get("content", [])
                            for item in content:
                                if item.get("type") == "tool_use":
                                    tool_name = item.get("name", "unknown")
                                    stats["tool_calls"][tool_name] = stats["tool_calls"].get(tool_name, 0) + 1
                        
                        # Look for errors
                        if "error" in str(entry).lower():
                            stats["errors"] += 1
                    
                    except json.JSONDecodeError:
                        continue
            
            # Calculate duration
            if first_timestamp and last_timestamp:
                from datetime import datetime
                try:
                    start = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                    duration = end - start
                    stats["session_duration"] = str(duration)
                except:
                    pass
            
            return {
                "status": "success",
                "session_id": session_id,
                "summary": stats
            }
            
        except Exception as e:
            logger.error(f"Error creating context summary: {e}")
            return {"status": "error", "error": str(e)}

def test_compressed_context():
    """Test the compressed context manager"""
    manager = CompressedContextManager(Path.home() / ".claude" / "enhanced_memories")
    
    print("Testing Compressed Context Manager:")
    
    # Test loading compressed context
    result = manager.load_compressed_session_context(max_entries=10)
    print(f"Compressed context result: {result['status']}")
    if result.get('compression_ratio'):
        print(f"Compression ratio: {result['compression_ratio']}")
    
    # Test creating summary
    if result.get('session_file'):
        session_id = result['session_file'].replace('.jsonl', '')
        summary = manager.create_context_summary(session_id)
        print(f"Summary status: {summary['status']}")

if __name__ == "__main__":
    test_compressed_context()