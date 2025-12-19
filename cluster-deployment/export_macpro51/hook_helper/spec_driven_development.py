#!/usr/bin/env python3
"""
Spec-Driven Development Hook
Captures specifications and integrates with learning/memory systems
"""

import json
import sqlite3
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class SpecDrivenHook:
    def __init__(self):
        self.claude_home = Path.home() / ".claude"
        self.spec_home = self.claude_home / "agency-spec-system"
        self.memory_db = self.claude_home / "enhanced_memory.db"
        self.learning_db = self.claude_home / "learning.db"
        self.spec_log = self.claude_home / "specifications.log"
        
    def capture_specification(self, spec_text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Capture and store a specification"""
        spec_hash = hashlib.md5(spec_text.encode()).hexdigest()[:8]
        
        # Store in memory system
        self.store_in_memory(spec_text, spec_hash, metadata)
        
        # Learn from specification pattern
        self.learn_spec_pattern(spec_text, metadata)
        
        # Log specification
        self.log_specification(spec_hash, metadata)
        
        return {
            "spec_id": spec_hash,
            "stored": True,
            "learned": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def store_in_memory(self, spec_text: str, spec_hash: str, metadata: Dict):
        """Store specification in enhanced memory"""
        conn = sqlite3.connect(self.memory_db)
        c = conn.cursor()
        
        entity_data = {
            "type": "specification",
            "name": f"spec_{spec_hash}",
            "content": spec_text,
            "metadata": json.dumps({
                **metadata,
                "spec_hash": spec_hash,
                "created_at": datetime.now().isoformat()
            })
        }
        
        c.execute("""
            INSERT INTO entities (type, name, content, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entity_data["type"],
            entity_data["name"],
            entity_data["content"],
            entity_data["metadata"],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def learn_spec_pattern(self, spec_text: str, metadata: Dict):
        """Learn from specification patterns"""
        conn = sqlite3.connect(self.learning_db)
        c = conn.cursor()
        
        # Extract patterns from spec
        patterns = self.extract_patterns(spec_text)
        
        # Store as learned pattern
        for pattern_type, pattern_data in patterns.items():
            c.execute("""
                INSERT OR REPLACE INTO patterns 
                (pattern_type, pattern_data, frequency, success_rate, last_seen)
                VALUES (?, ?, 
                    COALESCE((SELECT frequency + 1 FROM patterns 
                              WHERE pattern_type = ? AND pattern_data = ?), 1),
                    1.0, ?)
            """, (
                f"spec_{pattern_type}",
                json.dumps(pattern_data),
                f"spec_{pattern_type}",
                json.dumps(pattern_data),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def extract_patterns(self, spec_text: str) -> Dict[str, Any]:
        """Extract learnable patterns from specification"""
        patterns = {}
        
        # Intent patterns (what the user wants)
        if "build" in spec_text.lower():
            patterns["intent"] = {"action": "build", "frequency": 1}
        elif "fix" in spec_text.lower():
            patterns["intent"] = {"action": "fix", "frequency": 1}
        elif "enhance" in spec_text.lower():
            patterns["intent"] = {"action": "enhance", "frequency": 1}
        
        # Technical patterns (how to implement)
        tech_keywords = ["api", "database", "frontend", "backend", "cli", "mcp"]
        for keyword in tech_keywords:
            if keyword in spec_text.lower():
                patterns[f"tech_{keyword}"] = {"detected": True}
        
        return patterns
    
    def log_specification(self, spec_hash: str, metadata: Dict):
        """Log specification for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "spec_id": spec_hash,
            "metadata": metadata
        }
        
        with open(self.spec_log, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def generate_implementation_plan(self, spec_text: str) -> Dict[str, Any]:
        """Generate implementation plan from specification"""
        # Use learned patterns to suggest implementation
        conn = sqlite3.connect(self.learning_db)
        c = conn.cursor()
        
        # Find similar successful patterns
        c.execute("""
            SELECT pattern_data, success_rate 
            FROM patterns 
            WHERE pattern_type LIKE 'spec_%' 
            AND success_rate > 0.7
            ORDER BY frequency DESC
            LIMIT 5
        """)
        
        similar_patterns = c.fetchall()
        conn.close()
        
        # Generate plan based on patterns
        plan = {
            "specification": spec_text,
            "suggested_tools": self.suggest_tools(spec_text),
            "learned_patterns": [json.loads(p[0]) for p in similar_patterns],
            "confidence": sum(p[1] for p in similar_patterns) / len(similar_patterns) if similar_patterns else 0.5
        }
        
        return plan
    
    def suggest_tools(self, spec_text: str) -> List[str]:
        """Suggest tools based on specification"""
        tools = []
        
        spec_lower = spec_text.lower()
        
        # Tool mapping based on intent
        if "read" in spec_lower or "analyze" in spec_lower:
            tools.extend(["Read", "Grep", "Glob"])
        if "write" in spec_lower or "create" in spec_lower:
            tools.extend(["Write", "Edit"])
        if "test" in spec_lower or "run" in spec_lower:
            tools.extend(["Bash"])
        if "search" in spec_lower or "find" in spec_lower:
            tools.extend(["Grep", "Glob", "WebSearch"])
        if "memory" in spec_lower or "remember" in spec_lower:
            tools.append("mcp__enhanced-memory-mcp__create_entities")
        
        return list(set(tools))  # Remove duplicates

def hook(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main hook entry point"""
    
    # Only process specification-related events
    if event_type not in ["pre-tool-use", "specification", "plan"]:
        return {"continue": True}
    
    hook = SpecDrivenHook()
    
    # Check if this is a specification command
    if event_type == "pre-tool-use" and event_data.get("tool") == "Task":
        task_prompt = event_data.get("prompt", "")
        
        # Check for specification keywords
        if any(keyword in task_prompt.lower() for keyword in ["specify", "specification", "plan", "design"]):
            # Capture as specification
            result = hook.capture_specification(task_prompt, {
                "source": "task_tool",
                "event_type": event_type
            })
            
            # Generate implementation plan
            plan = hook.generate_implementation_plan(task_prompt)
            
            # Add to event data for downstream processing
            event_data["specification"] = result
            event_data["implementation_plan"] = plan
    
    return {"continue": True, "modified_data": event_data}

if __name__ == "__main__":
    # Test the hook
    hook = SpecDrivenHook()
    
    test_spec = "Build an API endpoint for user authentication with JWT tokens"
    result = hook.capture_specification(test_spec, {"test": True})
    plan = hook.generate_implementation_plan(test_spec)
    
    print(f"Specification captured: {result}")
    print(f"Implementation plan: {json.dumps(plan, indent=2)}")